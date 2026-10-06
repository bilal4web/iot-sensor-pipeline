"""
Synthetic sensor node emulator.

Generates plausible-but-fake environmental readings (temperature, pH,
turbidity) with timestamps, sequence numbers and CRC32 checksums.

ALL DATA PRODUCED BY THIS MODULE IS SYNTHETIC. It is a demonstration
emulator only and does not reproduce any real CISNR hardware, firmware,
or field data.
"""

import json
import zlib
from dataclasses import dataclass

import numpy as np


@dataclass
class Reading:
    node_id: str
    seq: int
    ts: float  # virtual timestamp, seconds
    temperature_c: float
    ph: float
    turbidity_ntu: float


class SensorNode:
    """Emulates one battery-powered environmental sensor node."""

    def __init__(self, node_id, seed=None, interval_s=5.0):
        self.node_id = node_id
        self.rng = np.random.default_rng(seed)
        self.interval_s = interval_s
        # Slowly-varying baselines so the series looks like a real deployment.
        self._temp_base = 24.0 + self.rng.uniform(-2.0, 2.0)
        self._ph_base = 7.0 + self.rng.uniform(-0.4, 0.4)
        self._turb_base = 4.0 + self.rng.uniform(0.0, 6.0)
        self._drift_phase = self.rng.uniform(0, 2 * np.pi)

    def generate_reading(self, seq, t):
        """Produce one synthetic reading at virtual time t."""
        # Diurnal-ish drift + measurement noise (all synthetic).
        drift = np.sin(2 * np.pi * t / 86400.0 + self._drift_phase)
        temp = self._temp_base + 1.5 * drift + self.rng.normal(0, 0.25)
        ph = self._ph_base + 0.1 * drift + self.rng.normal(0, 0.05)
        turb = max(
            0.1,
            self._turb_base * (1 + 0.2 * drift) + self.rng.normal(0, 0.8),
        )
        return Reading(
            node_id=self.node_id,
            seq=seq,
            ts=t,
            temperature_c=round(float(temp), 2),
            ph=round(float(ph), 2),
            turbidity_ntu=round(float(turb), 2),
        )


def _canonical_body(packet):
    """Canonical JSON of everything except the CRC field."""
    body = {k: v for k, v in packet.items() if k != "crc"}
    return json.dumps(body, sort_keys=True, separators=(",", ":")).encode()


def compute_crc(packet):
    """CRC32 checksum over the packet body (hex string)."""
    return format(zlib.crc32(_canonical_body(packet)) & 0xFFFFFFFF, "08x")


def make_packet(reading):
    """Wrap a Reading into a transmittable packet dict with CRC."""
    packet = {
        "node_id": reading.node_id,
        "seq": reading.seq,
        "ts": reading.ts,
        "readings": {
            "temperature_c": reading.temperature_c,
            "ph": reading.ph,
            "turbidity_ntu": reading.turbidity_ntu,
        },
    }
    packet["crc"] = compute_crc(packet)
    return packet


def serialize(packet):
    """Packet dict -> bytes for the (simulated) radio."""
    return json.dumps(packet, separators=(",", ":")).encode()


def deserialize(raw):
    """Bytes -> packet dict. Raises ValueError on malformed input."""
    return json.loads(raw.decode())


def verify_crc(packet):
    """True if the packet's CRC matches its body."""
    return packet.get("crc") == compute_crc(packet)
