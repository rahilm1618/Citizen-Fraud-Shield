import asyncio
import sys

from sqlalchemy.ext.asyncio import create_async_engine
from app.database import async_session_factory, engine
from app.models import User
from app.auth import get_password_hash

async def seed_users():
    async with async_session_factory() as session:
        # Create admin user
        admin = User(
            email="admin@admin.com",
            password_hash=get_password_hash("password"),
            role="admin"
        )
        session.add(admin)

        # Create officer user
        officer = User(
            email="officer@cybercell.gov.in",
            password_hash=get_password_hash("password"),
            role="law_enforcement"
        )
        session.add(officer)

        try:
            await session.commit()
            print("✅ Successfully seeded admin and officer users.")
        except Exception as e:
            print(f"Users might already exist or an error occurred: {e}")

    await engine.dispose()

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(seed_users())
