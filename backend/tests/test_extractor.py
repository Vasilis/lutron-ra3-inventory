"""Extractor correctness checks that are awkward to exercise via fixtures."""

from __future__ import annotations

import asyncio

import pytest

from ra3_inventory.leap.extract import InventoryExtractor
from ra3_inventory.models import RadioRa3Processor


class _IdleProto:
    async def run(self) -> None:
        await asyncio.Event().wait()


class _ChangingProjectExtractor(InventoryExtractor):
    async def _fetch_toplevel(self):
        return {
            "/project": {
                "Project": {
                    "href": "/project",
                    "ProjectModifiedTimestamp": "before",
                }
            }
        }

    async def _fetch_devices(self):
        return (
            RadioRa3Processor(
                href="/device/1",
                DeviceType="RadioRa3Processor",
            ),
            [],
        )

    async def _fetch_expanded_buttongroups(self, devices):
        return {}

    async def _fetch_programming_models(self, bg_expansions):
        return {}

    async def _fetch_presets(self, programming_models):
        return {}

    async def _read(self, url: str):
        if url == "/project":
            return {
                "Project": {
                    "href": "/project",
                    "ProjectModifiedTimestamp": "after",
                }
            }
        return None


@pytest.mark.asyncio
async def test_extractor_marks_snapshot_partial_when_project_changes_mid_walk() -> None:
    extractor = _ChangingProjectExtractor(_IdleProto(), host="192.0.2.1")

    inventory = await extractor.run()

    assert inventory.partial is True
