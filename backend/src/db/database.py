"""SQLite Database Setup und Session-Management."""

import os
from datetime import datetime
from typing import Optional
from sqlalchemy import create_engine, Column, String, Integer, DateTime, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker as async_sessionmaker

# Database Path
DB_PATH = os.getenv("DATABASE_PATH", "konflikt_simulator.db")
DATABASE_URL = f"sqlite+aiosqlite:///{DB_PATH}"

# Async Engine
engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

Base = declarative_base()


class SessionModel(Base):
    """SQLAlchemy Model für eine Simulations-Session."""

    __tablename__ = "sessions"

    id = Column(String, primary_key=True)
    mode = Column(String, nullable=False)  # "mediator" oder "participant"
    agent_a_name = Column(String, nullable=False)
    agent_a_prompt = Column(Text, nullable=False)
    agent_b_name = Column(String, nullable=False)
    agent_b_prompt = Column(Text, nullable=False)
    scenario = Column(Text, nullable=True)
    user_role = Column(String, nullable=True)
    turns = Column(Integer, default=0)
    messages = Column(JSON, default=list)  # Liste von Message-Dicts
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Integer, default=1)  # SQLite hat kein Boolean


class AgentConfigModel(Base):
    """SQLAlchemy Model für gespeicherte Agenten-Konfigurationen."""

    __tablename__ = "agent_configs"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    prompt = Column(Text, nullable=False)
    is_preset = Column(Integer, default=0)  # 1 = vordefiniertes Preset
    created_at = Column(DateTime, default=datetime.utcnow)


async def init_db():
    """Initialisiert die Datenbank und erstellt Tabellen."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncSession:
    """Dependency für FastAPI - gibt eine DB Session zurück."""
    async with AsyncSessionLocal() as session:
        yield session


class SessionRepository:
    """Repository für Session-Operationen."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        session_id: str,
        mode: str,
        agent_a_name: str,
        agent_a_prompt: str,
        agent_b_name: str,
        agent_b_prompt: str,
        scenario: Optional[str] = None,
        user_role: Optional[str] = None,
    ) -> SessionModel:
        """Erstellt eine neue Session."""
        session = SessionModel(
            id=session_id,
            mode=mode,
            agent_a_name=agent_a_name,
            agent_a_prompt=agent_a_prompt,
            agent_b_name=agent_b_name,
            agent_b_prompt=agent_b_prompt,
            scenario=scenario,
            user_role=user_role,
            messages=[],
        )
        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)
        return session

    async def get(self, session_id: str) -> Optional[SessionModel]:
        """Holt eine Session nach ID."""
        from sqlalchemy import select
        result = await self.db.execute(
            select(SessionModel).where(SessionModel.id == session_id)
        )
        return result.scalar_one_or_none()

    async def update_messages(
        self,
        session_id: str,
        messages: list,
        turns: int,
    ) -> Optional[SessionModel]:
        """Aktualisiert die Nachrichten einer Session."""
        session = await self.get(session_id)
        if session:
            session.messages = messages
            session.turns = turns
            session.updated_at = datetime.utcnow()
            await self.db.commit()
            await self.db.refresh(session)
        return session

    async def deactivate(self, session_id: str) -> bool:
        """Deaktiviert eine Session."""
        session = await self.get(session_id)
        if session:
            session.is_active = 0
            session.updated_at = datetime.utcnow()
            await self.db.commit()
            return True
        return False

    async def list_active(self, limit: int = 50) -> list[SessionModel]:
        """Listet aktive Sessions."""
        from sqlalchemy import select
        result = await self.db.execute(
            select(SessionModel)
            .where(SessionModel.is_active == 1)
            .order_by(SessionModel.updated_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def list_all(self, limit: int = 100) -> list[SessionModel]:
        """Listet alle Sessions."""
        from sqlalchemy import select
        result = await self.db.execute(
            select(SessionModel)
            .order_by(SessionModel.updated_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())


class AgentConfigRepository:
    """Repository für Agenten-Konfigurationen."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        config_id: str,
        name: str,
        prompt: str,
        is_preset: bool = False,
    ) -> AgentConfigModel:
        """Erstellt eine neue Agenten-Konfiguration."""
        config = AgentConfigModel(
            id=config_id,
            name=name,
            prompt=prompt,
            is_preset=1 if is_preset else 0,
        )
        self.db.add(config)
        await self.db.commit()
        await self.db.refresh(config)
        return config

    async def get(self, config_id: str) -> Optional[AgentConfigModel]:
        """Holt eine Konfiguration nach ID."""
        from sqlalchemy import select
        result = await self.db.execute(
            select(AgentConfigModel).where(AgentConfigModel.id == config_id)
        )
        return result.scalar_one_or_none()

    async def list_presets(self) -> list[AgentConfigModel]:
        """Listet vordefinierte Presets."""
        from sqlalchemy import select
        result = await self.db.execute(
            select(AgentConfigModel).where(AgentConfigModel.is_preset == 1)
        )
        return list(result.scalars().all())

    async def list_custom(self) -> list[AgentConfigModel]:
        """Listet benutzerdefinierte Konfigurationen."""
        from sqlalchemy import select
        result = await self.db.execute(
            select(AgentConfigModel).where(AgentConfigModel.is_preset == 0)
        )
        return list(result.scalars().all())

    async def delete(self, config_id: str) -> bool:
        """Löscht eine Konfiguration."""
        config = await self.get(config_id)
        if config and config.is_preset == 0:  # Presets nicht löschen
            await self.db.delete(config)
            await self.db.commit()
            return True
        return False
