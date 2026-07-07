import json
import logging
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert

from app.config import settings
from app.models import FraudEntity, FraudLink

logger = logging.getLogger(__name__)

def _get_openai_client():
    from openai import AsyncOpenAI
    return AsyncOpenAI(api_key=settings.openai_api_key)

def _get_groq_client():
    from openai import AsyncOpenAI
    return AsyncOpenAI(base_url="https://api.groq.com/openai/v1", api_key=settings.groq_api_key)

def _get_gemini_client():
    from google import genai
    return genai.Client(api_key=settings.gemini_api_key)


async def extract_entities(transcript: str) -> list[dict]:
    system_prompt = """You are a forensic entity extractor.
Extract any phone numbers, bank account numbers, UPI IDs, or names of individuals mentioned in the transcript.
Valid entity types are: "phone", "bank_account", "upi_id", "name".
Return ONLY valid JSON matching this exact schema:
{
  "entities": [
    {"type": "phone", "value": "..."}
  ]
}
If none found, return {"entities": []}.
"""
    if settings.llm_provider.lower() == "gemini":
        return await _extract_entities_gemini(system_prompt, transcript)
    elif settings.llm_provider.lower() == "groq":
        return await _extract_entities_groq(system_prompt, transcript)
    else:
        return await _extract_entities_openai_wrapped(system_prompt, transcript)

async def _extract_entities_openai_wrapped(system_prompt: str, transcript: str) -> list[dict]:
    from app.utils.json_parser import extract_json_from_text
    client = _get_openai_client()
    try:
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": transcript}
            ],
            response_format={"type": "json_object"},
            temperature=0.1
        )
        content = response.choices[0].message.content
        if not content:
            return []
        data = extract_json_from_text(content)
        return data.get("entities", [])
    except Exception as e:
        logger.error(f"OpenAI entity extraction failed: {e}")
        return []

async def _extract_entities_groq(system_prompt: str, transcript: str, retries=1) -> list[dict]:
    from app.utils.json_parser import extract_json_from_text
    client = _get_groq_client()
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": transcript}
    ]
    for attempt in range(retries + 1):
        try:
            response = await client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0.1
            )
            content = response.choices[0].message.content
            if not content:
                return []
            data = extract_json_from_text(content)
            return data.get("entities", [])
        except Exception as e:
            logger.error(f"Groq entity extraction failed on attempt {attempt+1}: {e}")
            messages.append({"role": "assistant", "content": content if 'content' in locals() and content else ""})
            messages.append({"role": "user", "content": "You did not return valid JSON. Please return ONLY valid JSON matching the exact schema requested, with no markdown formatting."})
            
    return []

async def _extract_entities_gemini(system_prompt: str, transcript: str) -> list[dict]:
    from app.utils.json_parser import extract_json_from_text
    client = _get_gemini_client()
    try:
        response = await client.aio.models.generate_content(
            model=settings.gemini_model,
            contents=[system_prompt, transcript],
            config={
                "response_mime_type": "application/json"
            }
        )
        content = response.text
        if not content:
            return []
        data = extract_json_from_text(content)
        return data.get("entities", [])
    except Exception as e:
        logger.error(f"Gemini entity extraction failed: {e}")
        return []

async def upsert_entities(session_id: uuid.UUID, entities: list[dict], db: AsyncSession):
    """
    Upserts entities into fraud_entities and creates links in fraud_links.
    Idempotent per session_id to avoid incrementing report_count multiple times for live updates.
    """
    for entity in entities:
        etype = entity.get("type")
        evalue = entity.get("value")
        if not etype or not evalue:
            continue
            
        # Ensure type is valid
        if etype not in ["phone", "bank_account", "upi_id", "name"]:
            continue
            
        # 1. First, insert or get the entity WITHOUT incrementing report_count yet
        stmt = insert(FraudEntity).values(
            entity_type=etype,
            entity_value=evalue,
            report_count=0  # Start at 0, we will increment if it's a new link
        ).on_conflict_do_update(
            index_elements=['entity_type', 'entity_value'],
            set_={'entity_value': evalue} # Dummy update to return the ID
        ).returning(FraudEntity.id)
        
        result = await db.execute(stmt)
        entity_id = result.scalar_one()
        
        # 2. Check if link already exists
        link_stmt = select(FraudLink).where(
            FraudLink.session_id == session_id,
            FraudLink.entity_id == entity_id
        )
        link_result = await db.execute(link_stmt)
        existing_link = link_result.scalar_one_or_none()
        
        # 3. If no link exists, this is a new entity for this session
        if not existing_link:
            # Increment report_count
            update_stmt = update(FraudEntity).where(FraudEntity.id == entity_id).values(
                report_count=FraudEntity.report_count + 1
            )
            await db.execute(update_stmt)
            
            # Create link
            link = FraudLink(
                session_id=session_id,
                entity_id=entity_id
            )
            db.add(link)
        
    await db.flush()
