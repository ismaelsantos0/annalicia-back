import asyncio
from app.database import AsyncSessionLocal
from app.models import Appointment
from sqlalchemy import delete

async def clear():
    async with AsyncSessionLocal() as db:
        await db.execute(delete(Appointment))
        await db.commit()
        print('All appointments deleted')

asyncio.run(clear())
