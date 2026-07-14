import json
import logging

from app.config import settings

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

async def score_transcript(transcript: str, matched_patterns: list[dict]) -> dict:
    """
    Analyzes a transcript against matched reference scams.
    Returns a dict with: risk_score (0-100), explanation (str), red_flags (list of str)
    """
    
    if not matched_patterns:
        context_str = "No close reference pattern was found. Rely on general fraud-detection reasoning rather than a fabricated pattern match."
    else:
        context_str = "Reference these known scam patterns if relevant:\n" + "\n".join([f"Pattern: {p['title']}\nScript: {p['script_text']}" for p in matched_patterns])
    
    system_prompt = f"""You are an expert fraud detection AI for Indian citizens.
Analyze the following transcript of a suspicious call/message.
{context_str}

Evaluate the transcript and output strict JSON with the following schema:
{{
    "risk_score": <int between 0 and 100>,
    "explanation": "<string explaining the verdict in plain, reassuring language to the citizen>",
    "red_flags": ["list", "of", "suspicious", "indicators"]
}}
"""
    
    
    if settings.llm_provider.lower() == "gemini":
        return await _score_transcript_gemini(system_prompt, transcript)
    elif settings.llm_provider.lower() == "groq":
        return await _score_transcript_groq(system_prompt, transcript)
    else:
        return await _score_transcript_openai(system_prompt, transcript)

async def _score_transcript_openai(system_prompt: str, user_prompt: str) -> dict:
    from app.utils.json_parser import extract_json_from_text
    client = _get_openai_client()
    try:
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.2
        )
        content = response.choices[0].message.content
        if not content:
            raise ValueError("No content returned from OpenAI")
        return extract_json_from_text(content)
    except Exception as e:
        logger.error(f"OpenAI scoring failed: {e}")
        return {"risk_score": 50, "explanation": "Analysis failed.", "red_flags": []}

async def _score_transcript_groq(system_prompt: str, user_prompt: str, retries=1) -> dict:
    from app.utils.json_parser import extract_json_from_text
    client = _get_groq_client()
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    for attempt in range(retries + 1):
        try:
            response = await client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0.2
            )
            content = response.choices[0].message.content
            if not content:
                raise ValueError("No content returned from Groq")
            return extract_json_from_text(content)
        except Exception as e:
            logger.error(f"Groq scoring failed on attempt {attempt+1}: {e}")
            messages.append({"role": "assistant", "content": content if 'content' in locals() and content else ""})
            messages.append({"role": "user", "content": "You did not return valid JSON. Please return ONLY valid JSON matching the exact schema requested, with no markdown formatting."})
            
    return {"risk_score": 50, "explanation": "Analysis failed.", "red_flags": []}

async def _score_transcript_gemini(system_prompt: str, user_prompt: str) -> dict:
    client = _get_gemini_client()
    try:
        # Note: google-genai sync methods are used commonly or we can use async client
        # For simplicity in this implementation, if the async method varies, we'll just run it.
        # However, genai.Client has an asynchronous sub-module: client.aio.models.generate_content
        response = await client.aio.models.generate_content(
            model=settings.gemini_model,
            contents=[system_prompt, user_prompt],
            config={
                "response_mime_type": "application/json"
            }
        )
        content = response.text
        if not content:
            raise ValueError("No content returned from Gemini")
        from app.utils.json_parser import extract_json_from_text
        return extract_json_from_text(content)
    except Exception as e:
        logger.error(f"Gemini scoring failed: {e}")
        return {"risk_score": 50, "explanation": "Analysis failed.", "red_flags": []}

async def answer_followup(transcript: str, risk_score: int, explanation: str, chat_history: list[dict], new_message: str) -> str:
    """
    Answers a follow-up question from the citizen about their case.
    chat_history should be a list of {"role": "user"|"assistant", "content": "..."}
    """
    system_prompt = f"""You are a reassuring fraud prevention assistant.
The citizen provided this transcript:
"{transcript}"

We evaluated it with a risk score of {risk_score}/100 and this explanation:
"{explanation}"

Answer their follow-up questions concisely and calmly. Do not use markdown if possible, keep it conversational.
"""
    if settings.llm_provider.lower() == "gemini":
        return await _answer_followup_gemini(system_prompt, chat_history, new_message)
    elif settings.llm_provider.lower() == "groq":
        return await _answer_followup_groq(system_prompt, chat_history, new_message)
    else:
        return await _answer_followup_openai(system_prompt, chat_history, new_message)

async def _answer_followup_openai(system_prompt: str, chat_history: list[dict], new_message: str) -> str:
    client = _get_openai_client()
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(chat_history)
    messages.append({"role": "user", "content": new_message})
    
    try:
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0.7
        )
        content = response.choices[0].message.content
        if content is None:
            return "I'm sorry, I couldn't generate a response."
        return content
    except Exception as e:
        logger.error(f"OpenAI followup failed: {e}")
        return "I'm sorry, I encountered an error processing your request."

async def _answer_followup_groq(system_prompt: str, chat_history: list[dict], new_message: str) -> str:
    client = _get_groq_client()
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(chat_history)
    messages.append({"role": "user", "content": new_message})
    
    try:
        response = await client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=0.7
        )
        content = response.choices[0].message.content
        if content is None:
            return "I'm sorry, I couldn't generate a response."
        return content
    except Exception as e:
        logger.error(f"Groq followup failed: {e}")
        return "I'm sorry, I encountered an error processing your request."

async def _answer_followup_gemini(system_prompt: str, chat_history: list[dict], new_message: str) -> str:
    client = _get_gemini_client()
    # Constructing gemini contents
    contents = [system_prompt]
    for msg in chat_history:
        contents.append(f"{msg['role'].capitalize()}: {msg['content']}")
    contents.append(f"User: {new_message}")
    
    try:
        response = await client.aio.models.generate_content(
            model=settings.gemini_model,
            contents=contents
        )
        content = response.text
        if content is None:
            return "I'm sorry, I couldn't generate a response."
        return content
    except Exception as e:
        logger.error(f"Gemini followup failed: {e}")
        return "I'm sorry, I encountered an error processing your request."
