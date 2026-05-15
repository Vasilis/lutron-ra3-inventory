"""JSON export — Pydantic ``model_dump_json``."""

from __future__ import annotations

from ..models import ProcessorInventory


def to_json(inventory: ProcessorInventory, *, indent: int = 2) -> str:
    """Serialize a ProcessorInventory to JSON, indented for readability."""
    return inventory.model_dump_json(indent=indent)


def to_json_bytes(inventory: ProcessorInventory, *, indent: int = 2) -> bytes:
    return to_json(inventory, indent=indent).encode("utf-8")
