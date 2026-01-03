"""SQLite Database Setup und Session-Management."""

import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional
from sqlalchemy import create_engine, Column, String, Integer, DateTime, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker as async_sessionmaker

# Database Path - stabil im backend/ Verzeichnis
BACKEND_DIR = Path(__file__).parent.parent.parent  # backend/
DB_PATH = os.getenv("DATABASE_PATH", str(BACKEND_DIR / "konflikt_simulator.db"))
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


class ScenarioModel(Base):
    """SQLAlchemy Model für Szenarien (Presets und benutzerdefinierte)."""

    __tablename__ = "scenarios"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    scenario_text = Column(Text, nullable=False)
    agent_a_name = Column(String, nullable=False)
    agent_a_prompt = Column(Text, nullable=False)
    agent_b_name = Column(String, nullable=False)
    agent_b_prompt = Column(Text, nullable=False)
    is_preset = Column(Integer, default=0)  # 0=custom, 1=preset
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


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


class ScenarioRepository:
    """Repository für Szenario-Operationen."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        name: str,
        scenario_text: str,
        agent_a_name: str,
        agent_a_prompt: str,
        agent_b_name: str,
        agent_b_prompt: str,
        is_preset: bool = False,
        scenario_id: Optional[str] = None,
    ) -> ScenarioModel:
        """Erstellt ein neues Szenario."""
        scenario = ScenarioModel(
            id=scenario_id or str(uuid.uuid4()),
            name=name,
            scenario_text=scenario_text,
            agent_a_name=agent_a_name,
            agent_a_prompt=agent_a_prompt,
            agent_b_name=agent_b_name,
            agent_b_prompt=agent_b_prompt,
            is_preset=1 if is_preset else 0,
        )
        self.db.add(scenario)
        await self.db.commit()
        await self.db.refresh(scenario)
        return scenario

    async def get(self, scenario_id: str) -> Optional[ScenarioModel]:
        """Holt ein Szenario nach ID."""
        from sqlalchemy import select
        result = await self.db.execute(
            select(ScenarioModel).where(ScenarioModel.id == scenario_id)
        )
        return result.scalar_one_or_none()

    async def list_all(self) -> list[ScenarioModel]:
        """Listet alle Szenarien (Presets zuerst, dann custom nach Erstellungsdatum)."""
        from sqlalchemy import select
        result = await self.db.execute(
            select(ScenarioModel)
            .order_by(ScenarioModel.is_preset.desc(), ScenarioModel.created_at.asc())
        )
        return list(result.scalars().all())

    async def list_presets(self) -> list[ScenarioModel]:
        """Listet nur Preset-Szenarien."""
        from sqlalchemy import select
        result = await self.db.execute(
            select(ScenarioModel).where(ScenarioModel.is_preset == 1)
        )
        return list(result.scalars().all())

    async def list_custom(self) -> list[ScenarioModel]:
        """Listet nur benutzerdefinierte Szenarien."""
        from sqlalchemy import select
        result = await self.db.execute(
            select(ScenarioModel)
            .where(ScenarioModel.is_preset == 0)
            .order_by(ScenarioModel.created_at.desc())
        )
        return list(result.scalars().all())

    async def update(
        self,
        scenario_id: str,
        name: Optional[str] = None,
        scenario_text: Optional[str] = None,
        agent_a_name: Optional[str] = None,
        agent_a_prompt: Optional[str] = None,
        agent_b_name: Optional[str] = None,
        agent_b_prompt: Optional[str] = None,
    ) -> Optional[ScenarioModel]:
        """Aktualisiert ein Szenario (nur custom, keine Presets)."""
        scenario = await self.get(scenario_id)
        if scenario and scenario.is_preset == 0:
            if name is not None:
                scenario.name = name
            if scenario_text is not None:
                scenario.scenario_text = scenario_text
            if agent_a_name is not None:
                scenario.agent_a_name = agent_a_name
            if agent_a_prompt is not None:
                scenario.agent_a_prompt = agent_a_prompt
            if agent_b_name is not None:
                scenario.agent_b_name = agent_b_name
            if agent_b_prompt is not None:
                scenario.agent_b_prompt = agent_b_prompt
            scenario.updated_at = datetime.utcnow()
            await self.db.commit()
            await self.db.refresh(scenario)
            return scenario
        return None

    async def delete(self, scenario_id: str) -> bool:
        """Löscht ein Szenario (nur custom, keine Presets)."""
        scenario = await self.get(scenario_id)
        if scenario and scenario.is_preset == 0:
            await self.db.delete(scenario)
            await self.db.commit()
            return True
        return False

    async def exists(self, scenario_id: str) -> bool:
        """Prüft ob ein Szenario existiert."""
        scenario = await self.get(scenario_id)
        return scenario is not None


# Preset-Szenarien für Seeding
PRESET_SCENARIOS = [
    {
        "id": "preset-arbeitsplatz",
        "name": "Arbeitsplatz",
        "scenario_text": """Maria (42, Senior Projektmanagerin) und Stefan (35, ambitionierter Projektmitarbeiter) arbeiten seit 2 Jahren im selben Team. Letzte Woche hat Stefan dem Abteilungsleiter eine innovative Lösung für das aktuelle Kundenprojekt präsentiert - ohne Maria vorher einzuweihen. Die Idee wurde gut aufgenommen, und der Chef lobte Stefan öffentlich. Maria fühlt sich übergangen und hinterfragt Stefans Loyalität. Stefan versteht nicht, warum Maria so reagiert - er wollte doch nur Initiative zeigen. Beide treffen sich jetzt zum Klärungsgespräch.""",
        "agent_a_name": "Maria",
        "agent_a_prompt": "Du bist Maria, 42 Jahre, Senior Projektmanagerin mit 15 Jahren Berufserfahrung. Du bist direkt, professionell und erwartest Respekt für deine Position. Du fühlst dich von Stefan hintergangen und bist enttäuscht über seinen Vertrauensbruch.",
        "agent_b_name": "Stefan",
        "agent_b_prompt": "Du bist Stefan, 35 Jahre, ambitionierter Projektmitarbeiter der Karriere machen will. Du bist ehrgeizig, manchmal ungeduldig und verstehst nicht, warum Maria so reagiert. Du wolltest Initiative zeigen und siehst dich zu Unrecht kritisiert.",
    },
    {
        "id": "preset-paar-konflikt",
        "name": "Paar-Konflikt",
        "scenario_text": """Lisa (34, Vollzeit-Marketingmanagerin) und Thomas (36, Softwareentwickler mit flexiblen Arbeitszeiten) sind seit 5 Jahren zusammen und wohnen seit 3 Jahren in einer gemeinsamen Wohnung. Lisa kommt jeden Abend erschöpft nach Hause und findet regelmäßig unerledigte Hausarbeit vor, während Thomas am PC sitzt. Sie hat das Gefühl, dass sie neben ihrem anspruchsvollen Job auch noch den gesamten Haushalt managt. Thomas findet, dass er seinen fairen Anteil beiträgt und Lisa übertreibt. Heute Abend eskaliert der Streit nach einem besonders stressigen Tag.""",
        "agent_a_name": "Lisa",
        "agent_a_prompt": "Du bist Lisa, 34 Jahre alt, Vollzeit-Marketingmanagerin. Du bist emotional, fühlst dich oft ungerecht behandelt und überlastet. Du kommst erschöpft nach Hause und hast das Gefühl, alles alleine machen zu müssen. Du reagierst schnell defensiv und verwendest oft Vorwürfe.",
        "agent_b_name": "Thomas",
        "agent_b_prompt": "Du bist Thomas, 36 Jahre alt, Softwareentwickler mit flexiblen Arbeitszeiten. Du bist rational, analytisch und verstehst nicht, warum Lisa so emotional reagiert. Du findest, du trägst deinen fairen Anteil bei und sie übertreibt. Du wirst sarkastisch wenn du frustriert bist.",
    },
    {
        "id": "preset-familie",
        "name": "Familie",
        "scenario_text": """Markus (28) hat gerade seiner Mutter Renate (58) eröffnet, dass er seinen gut bezahlten IT-Job bei einem DAX-Konzern gekündigt hat, um Vollzeit als freischaffender Künstler zu arbeiten. Renate, die selbst hart gearbeitet hat, um Markus das Studium zu ermöglichen, ist schockiert. Sie macht sich Sorgen um seine finanzielle Zukunft und Altersvorsorge. Markus fühlt sich seit Jahren in seinem Job gefangen und hat endlich den Mut gefunden, seinen Traum zu verfolgen. Er hat 6 Monate Ersparnisse und erste Aufträge. Das Gespräch findet bei Kaffee und Kuchen in Renates Wohnzimmer statt.""",
        "agent_a_name": "Renate",
        "agent_a_prompt": "Du bist Renate, 58 Jahre, Mutter von Markus. Du hast hart gearbeitet um deinem Sohn das Studium zu ermöglichen. Du machst dir große Sorgen um seine finanzielle Zukunft und Altersvorsorge. Du verstehst nicht, warum er einen sicheren Job aufgibt. Du bist enttäuscht und besorgt zugleich.",
        "agent_b_name": "Markus",
        "agent_b_prompt": "Du bist Markus, 28 Jahre, hast deinen IT-Job gekündigt um Künstler zu werden. Du fühlst dich seit Jahren im Job gefangen und hast endlich den Mut gefunden, deinen Traum zu verfolgen. Du hast 6 Monate Ersparnisse und erste Aufträge. Du wünschst dir Unterstützung von deiner Mutter.",
    },
    {
        "id": "preset-wg",
        "name": "WG",
        "scenario_text": """Alex (24, Masterstudent im letzten Semester) und Kim (23, Remote-Mitarbeiter bei einem Startup) teilen sich seit 8 Monaten eine 2-Zimmer-Wohnung. Alex schreibt gerade unter Hochdruck seine Masterarbeit und arbeitet oft bis 4 Uhr morgens, um tagsüber Ruhe zum Schlafen zu finden. Kim arbeitet flexible Stunden und macht gerne laute Musik beim Arbeiten, hat häufig spontan Freunde zu Besuch. Es ist Sonntagmittag, Alex wurde zum dritten Mal diese Woche von Kims Musik geweckt. Die Abgabe ist in 2 Wochen.""",
        "agent_a_name": "Alex",
        "agent_a_prompt": "Du bist Alex, 24 Jahre, Masterstudent im letzten Semester. Du schreibst unter Hochdruck deine Masterarbeit, die Abgabe ist in 2 Wochen. Du arbeitest nachts und brauchst tagsüber Ruhe zum Schlafen. Du bist gestresst, übermüdet und am Limit. Du wurdest gerade wieder von Kims Musik geweckt.",
        "agent_b_name": "Kim",
        "agent_b_prompt": "Du bist Kim, 23 Jahre, Remote-Mitarbeiter bei einem Startup. Du arbeitest flexible Stunden und brauchst Musik zum Arbeiten. Du hast ein aktives Sozialleben und lädst gerne Freunde ein. Du findest Alex übertreibt und sollte sich besser organisieren.",
    },
]


async def seed_preset_scenarios():
    """Fügt die Standard-Szenarien ein, falls nicht vorhanden (idempotent)."""
    async with AsyncSessionLocal() as db:
        repo = ScenarioRepository(db)
        for preset in PRESET_SCENARIOS:
            if not await repo.exists(preset["id"]):
                await repo.create(
                    scenario_id=preset["id"],
                    name=preset["name"],
                    scenario_text=preset["scenario_text"],
                    agent_a_name=preset["agent_a_name"],
                    agent_a_prompt=preset["agent_a_prompt"],
                    agent_b_name=preset["agent_b_name"],
                    agent_b_prompt=preset["agent_b_prompt"],
                    is_preset=True,
                )
