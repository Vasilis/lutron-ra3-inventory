"""API route modules. Importing this package wires up every router on the FastAPI app."""

from . import export, extraction, health, inventory, pairing, profiles, snapshots

__all__ = ["export", "extraction", "health", "inventory", "pairing", "profiles", "snapshots"]
