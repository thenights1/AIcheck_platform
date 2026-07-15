"""Checkers API — list available compliance skills."""

from fastapi import APIRouter

from backend.registry import get_registry

router = APIRouter(prefix="/api/checkers", tags=["checkers"])


@router.get("")
def list_checkers():
    registry = get_registry(refresh=True)
    return [entry.to_info_dict() for entry in registry.values()]
