"""REST API Endpoints für Szenario-Management."""

import logging
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.database import get_db, ScenarioRepository, ScenarioModel
from ..models.schemas import (
    ScenarioCreate,
    ScenarioUpdate,
    ScenarioResponse,
    ScenarioListResponse,
)

logger = logging.getLogger("konflikt.scenarios")
router = APIRouter(prefix="/api/scenarios", tags=["scenarios"])


def model_to_response(scenario: ScenarioModel) -> ScenarioResponse:
    """Konvertiert ein ScenarioModel zu ScenarioResponse."""
    return ScenarioResponse(
        id=scenario.id,
        name=scenario.name,
        scenario_text=scenario.scenario_text,
        agent_a_name=scenario.agent_a_name,
        agent_a_prompt=scenario.agent_a_prompt,
        agent_b_name=scenario.agent_b_name,
        agent_b_prompt=scenario.agent_b_prompt,
        is_preset=scenario.is_preset == 1,
        created_at=scenario.created_at,
        updated_at=scenario.updated_at,
    )


@router.get("", response_model=ScenarioListResponse)
async def list_scenarios(db: AsyncSession = Depends(get_db)):
    """Alle Szenarien auflisten (Presets zuerst, dann custom)."""
    repo = ScenarioRepository(db)
    scenarios = await repo.list_all()
    return ScenarioListResponse(
        scenarios=[model_to_response(s) for s in scenarios],
        total=len(scenarios),
    )


@router.get("/{scenario_id}", response_model=ScenarioResponse)
async def get_scenario(scenario_id: str, db: AsyncSession = Depends(get_db)):
    """Ein einzelnes Szenario laden."""
    repo = ScenarioRepository(db)
    scenario = await repo.get(scenario_id)
    if not scenario:
        raise HTTPException(status_code=404, detail="Szenario nicht gefunden")
    return model_to_response(scenario)


@router.post("", response_model=ScenarioResponse, status_code=201)
async def create_scenario(data: ScenarioCreate, db: AsyncSession = Depends(get_db)):
    """Neues benutzerdefiniertes Szenario erstellen."""
    repo = ScenarioRepository(db)
    scenario = await repo.create(
        name=data.name,
        scenario_text=data.scenario_text,
        agent_a_name=data.agent_a_name,
        agent_a_prompt=data.agent_a_prompt,
        agent_b_name=data.agent_b_name,
        agent_b_prompt=data.agent_b_prompt,
        is_preset=False,
    )
    logger.info(f"Neues Szenario erstellt: {scenario.id} - {scenario.name}")
    return model_to_response(scenario)


@router.put("/{scenario_id}", response_model=ScenarioResponse)
async def update_scenario(
    scenario_id: str,
    data: ScenarioUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Benutzerdefiniertes Szenario aktualisieren (Presets können nicht geändert werden)."""
    repo = ScenarioRepository(db)

    # Prüfen ob Szenario existiert
    existing = await repo.get(scenario_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Szenario nicht gefunden")

    # Prüfen ob es ein Preset ist
    if existing.is_preset == 1:
        raise HTTPException(status_code=403, detail="Preset-Szenarien können nicht geändert werden")

    scenario = await repo.update(
        scenario_id=scenario_id,
        name=data.name,
        scenario_text=data.scenario_text,
        agent_a_name=data.agent_a_name,
        agent_a_prompt=data.agent_a_prompt,
        agent_b_name=data.agent_b_name,
        agent_b_prompt=data.agent_b_prompt,
    )
    logger.info(f"Szenario aktualisiert: {scenario_id}")
    return model_to_response(scenario)


@router.delete("/{scenario_id}", status_code=204)
async def delete_scenario(scenario_id: str, db: AsyncSession = Depends(get_db)):
    """Benutzerdefiniertes Szenario löschen (Presets können nicht gelöscht werden)."""
    repo = ScenarioRepository(db)

    # Prüfen ob Szenario existiert
    existing = await repo.get(scenario_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Szenario nicht gefunden")

    # Prüfen ob es ein Preset ist
    if existing.is_preset == 1:
        raise HTTPException(status_code=403, detail="Preset-Szenarien können nicht gelöscht werden")

    success = await repo.delete(scenario_id)
    if not success:
        raise HTTPException(status_code=500, detail="Löschen fehlgeschlagen")

    logger.info(f"Szenario gelöscht: {scenario_id}")
    return None
