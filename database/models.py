from datetime import datetime
from sqlalchemy import BigInteger, String, DateTime, ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, create_async_engine

from data.config import DB_URL

engine = create_async_engine(url=DB_URL)
async_session = async_sessionmaker(engine)

class Base(AsyncAttrs, DeclarativeBase):
    pass

class User(Base):
    __tablename__ = 'users'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    tg_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=True)
    username: Mapped[str] = mapped_column(String(255), nullable=True)
    joined_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Anime(Base):
    __tablename__ = 'animes'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text, nullable=True)
    image_id: Mapped[str] = mapped_column(String(255), nullable=True)
    code: Mapped[str] = mapped_column(String(50), unique=True) # Search code

class Episode(Base):
    __tablename__ = 'episodes'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    anime_id: Mapped[int] = mapped_column(ForeignKey('animes.id', ondelete='CASCADE'))
    part: Mapped[int] = mapped_column(Integer)
    file_id: Mapped[str] = mapped_column(String(255))

    __table_args__ = (
        UniqueConstraint('anime_id', 'part', name='_anime_part_uc'),
    )

class Channel(Base):
    __tablename__ = 'channels'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    channel_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    title: Mapped[str] = mapped_column(String(255))
    invite_link: Mapped[str] = mapped_column(String(255))

class Setting(Base):
    __tablename__ = 'settings'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(50), unique=True)
    value: Mapped[str] = mapped_column(Text, nullable=True)

async def async_main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
