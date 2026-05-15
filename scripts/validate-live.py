#!/usr/bin/env python3
"""One-shot live-validation script.

Imports the legacy pairing certs at ``--certs-dir``, derives the processor
serial, runs the full extractor against ``--host``, writes a snapshot,
and (optionally) saves a sanitized copy as the repo's example fixture.

Usage::

    python scripts/validate-live.py \\
        --host 192.168.1.184 \\
        --certs-dir "/path/to/lutron_certs" \\
        --save-example examples/sanitized-snapshot.json

The script is intentionally not wrapped as a pytest test — it requires a
live processor and physical access to the LAN, so it doesn't belong in CI.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import shutil
import sys
import tempfile
from pathlib import Path

from ra3_inventory.leap import connect_leap, extract_inventory
from ra3_inventory.models import parse_device, RadioRa3Processor
from ra3_inventory.storage import keychain, materialize_pairing, write_snapshot
from ra3_inventory.storage.certs import store_pairing_to_disk
from ra3_inventory.storage.paths import ensure_profile_tree, profile_json_path

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)-5s %(name)s: %(message)s"
)
_LOG = logging.getLogger("validate-live")


def _on_progress(event) -> None:
    pct = (
        f"{int((event.progress or 0) * 100):3d}%"
        if event.progress is not None
        else "  -"
    )
    print(f"  [{pct}] {event.phase:<22s} {event.detail}", flush=True)


async def _derive_serial(host: str, certs_tmp: Path) -> tuple[str, RadioRa3Processor]:
    """Open one LEAP connection to recover the processor's SerialNumber."""
    key, cert, ca = (
        certs_tmp / "caseta.key",
        certs_tmp / "caseta.crt",
        certs_tmp / "caseta-bridge.crt",
    )
    proto = await connect_leap(host, keyfile=key, certfile=cert, ca_certs=ca)
    proto_task = asyncio.create_task(proto.run())
    try:
        resp = await proto.request("ReadRequest", "/device?where=IsThisDevice:true")
        devs = next((v for v in (resp.Body or {}).values() if isinstance(v, list)), [])
        if not devs:
            raise RuntimeError("processor self-query returned no devices")
        processor = parse_device(devs[0])
        if not isinstance(processor, RadioRa3Processor):
            processor = RadioRa3Processor.model_validate(devs[0])
        serial = str(processor.SerialNumber or "")
        if not serial:
            # Fall back to MAC address
            if processor.NetworkInterfaces:
                mac = processor.NetworkInterfaces[0].MACAddress or ""
                if mac:
                    serial = mac.replace(":", "").lower()
        if not serial:
            raise RuntimeError("could not derive stable serial for profile")
        return serial, processor
    finally:
        proto.close()
        await proto.wait_closed()
        proto_task.cancel()
        try:
            await proto_task
        except (asyncio.CancelledError, Exception):  # noqa: BLE001
            pass


async def _run(args: argparse.Namespace) -> int:
    src = Path(args.certs_dir).expanduser().resolve()
    if not (src / "caseta.key").exists():
        print(f"ERROR: no caseta.key in {src}", file=sys.stderr)
        return 2

    # Stage certs into a temp dir for the serial-discovery probe (we don't
    # yet know which profile they belong to).
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        for n in ("caseta.key", "caseta.crt", "caseta-bridge.crt"):
            shutil.copy2(src / n, tmp / n)
        _LOG.info("Probing %s for processor serial...", args.host)
        serial, processor = await _derive_serial(args.host, tmp)
        _LOG.info(
            "Processor serial: %s (%s)", serial, processor.Name or processor.ModelNumber
        )

        # Install certs into the profile tree or Keychain.
        ensure_profile_tree(serial)
        key_pem = (tmp / "caseta.key").read_text()
        cert_pem = (tmp / "caseta.crt").read_text()
        ca_pem = (tmp / "caseta-bridge.crt").read_text()
        if keychain.is_available():
            keychain.store_pairing(
                serial,
                key_pem=key_pem,
                cert_pem=cert_pem,
                ca_pem=ca_pem,
            )
            _LOG.info("Mirrored creds to macOS Keychain")
        elif args.disk_passphrase:
            store_pairing_to_disk(
                serial,
                key_pem=key_pem,
                cert_pem=cert_pem,
                ca_pem=ca_pem,
                passphrase=args.disk_passphrase,
            )
            _LOG.info("Stored creds in encrypted on-disk fallback")
        else:
            print(
                "ERROR: Keychain unavailable; pass --disk-passphrase "
                "to use encrypted on-disk credential storage",
                file=sys.stderr,
            )
            return 2

        fw = ""
        if processor.FirmwareImage and processor.FirmwareImage.Firmware:
            fw = processor.FirmwareImage.Firmware.DisplayName or ""
        profile_json_path(serial).write_text(
            json.dumps(
                {
                    "name": args.name,
                    "host": args.host,
                    "firmware": fw,
                },
                indent=2,
            )
        )

    # Now run the real extraction.
    certs = materialize_pairing(serial, passphrase=args.disk_passphrase)
    if certs is None:
        print(f"ERROR: failed to materialize certs for {serial}", file=sys.stderr)
        return 2

    print("\nRunning full extraction:")
    try:
        inv = await extract_inventory(
            host=args.host,
            keyfile=certs.key,
            certfile=certs.cert,
            ca_certs=certs.ca,
            on_progress=_on_progress,
            capture_raw=args.capture_raw,
        )
    finally:
        certs.cleanup()
    snapshot_path = write_snapshot(serial, inv)
    print("\nSummary:")
    print(f"  Processor : {inv.processor.Name or '?'}  ({inv.processor.ModelNumber})")
    print(f"  Firmware  : {fw or '?'}")
    print(f"  Areas     : {len(inv.areas)}")
    print(f"  Devices   : {len(inv.devices)}")
    print(f"  Zones     : {len(inv.zones)}")
    print(
        f"  Buttons   : {sum(len(bg.Buttons or []) for bgs in inv.button_group_expansions.values() for bg in bgs)}"
    )
    print(f"  PMs       : {len(inv.programming_models)}")
    print(f"  Presets   : {len(inv.presets)}")
    print(f"  Duration  : {inv.duration_seconds:.1f}s")
    print(f"  Snapshot  : {snapshot_path}")

    if args.save_example:
        from sanitize_snapshot import sanitize_snapshot

        sanitized = sanitize_snapshot(inv.model_dump(mode="json"))
        dst = Path(args.save_example).expanduser().resolve()
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(json.dumps(sanitized, indent=2))
        print(f"  Example   : {dst}")
    return 0


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Live-validate the backend against a real RA3"
    )
    p.add_argument("--host", required=True, help="processor IP")
    p.add_argument(
        "--certs-dir",
        required=True,
        help="dir holding caseta.key/crt + caseta-bridge.crt",
    )
    p.add_argument("--name", default="Default", help="profile display name")
    p.add_argument(
        "--disk-passphrase",
        default=None,
        help="passphrase for encrypted on-disk credential storage when Keychain is unavailable",
    )
    p.add_argument(
        "--capture-raw",
        action="store_true",
        help="include the raw LEAP responses in the snapshot (large)",
    )
    p.add_argument(
        "--save-example",
        default=None,
        help="if set, write a sanitized copy of the snapshot here",
    )
    return p.parse_args()


if __name__ == "__main__":  # pragma: no cover
    sys.exit(asyncio.run(_run(parse_args())))
