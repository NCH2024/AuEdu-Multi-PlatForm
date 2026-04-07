# Server_Core/app/db/session.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# Tạo engine bất đồng bộ
engine = create_async_engine(DATABASE_URL, echo=True)

# Tạo session factory
AsyncSessionLocal = sessionmaker(
    bind=engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)

Base = declarative_base()

# Dependency để lấy database session cho các API sau này
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session