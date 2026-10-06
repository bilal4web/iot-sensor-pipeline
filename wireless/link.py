"""
Configurable wireless link model + stop-and-wait ARQ sender.

The link drops, corrupts, and delays packets according to configurable
distributions. The ReliableSender implements retries with exponential
backoff; a lost ACK causes a retransmission that the gateway will see
as a duplicate (deduplicated downstream).

All channel behavior is SYNTHETIC — a teaching model, not a measurement
of any real radio link.
"""

from dataclasses import dataclass, field

import numpy as np


@dataclass
class TransmitOutcome:
    delivered: bool          # did the frame reach the receiver?
    corrupted: bool          # was it bit-flipped in flight?
    latency_s: float         # one-way airtime (virtual seconds)
    payload: bytes = b""     # bytes as received (possibly corrupted)


@dataclass
class SendResult:
    delivered_ok: bool       # at least one copy arrived AND was ACKed
    attempts: int            # total transmission attempts used
    copies_delivered: int    # how many copies reached the gateway
    final_latency_s: float   # latency of the first delivered copy


class WirelessLink:
    """A lossy, delayed, occasionally-corrupting radio channel model."""

    def __init__(
        self,
        loss_rate=0.10,
        corrupt_rate=0.02,
        latency_mean_ms=120.0,
        latency_std_ms=45.0,
        ack_loss_rate=None,
        seed=None,
    ):
        if not 0.0 <= loss_rate < 1.0:
            raise ValueError("loss_rate must be in [0, 1)")
        self.loss_rate = loss_rate
        self.corrupt_rate = corrupt_rate
        self.latency_mean_ms = latency_mean_ms
        self.latency_std_ms = latency_std_ms
        # ACKs travel the same lossy medium unless overridden.
        self.ack_loss_rate = loss_rate if ack_loss_rate is None else ack_loss_rate
        self.rng = np.random.default_rng(seed)

    def _sample_latency_s(self):
        ms = self.rng.normal(self.latency_mean_ms, self.latency_std_ms)
        return max(1.0, ms) / 1000.0

    def _maybe_corrupt(self, raw: bytes) -> bytes:
        """Flip one random byte to emulate in-flight bit errors."""
        if len(raw) == 0 or self.rng.random() >= self.corrupt_rate:
            return raw
        buf = bytearray(raw)
        idx = int(self.rng.integers(0, len(buf)))
        buf[idx] ^= 1 << int(self.rng.integers(0, 8))
        return bytes(buf)

    def transmit(self, raw: bytes) -> TransmitOutcome:
        """Simulate a single frame transmission."""
        if self.rng.random() < self.loss_rate:
            return TransmitOutcome(delivered=False, corrupted=False, latency_s=0.0)
        corrupted = self.rng.random() < self.corrupt_rate
        payload = self._maybe_corrupt(raw) if corrupted else raw
        return TransmitOutcome(
            delivered=True,
            corrupted=corrupted,
            latency_s=self._sample_latency_s(),
            payload=payload,
        )

    def ack_ok(self) -> bool:
        """Was the link-layer ACK received?"""
        return self.rng.random() >= self.ack_loss_rate


class ReliableSender:
    """Stop-and-wait ARQ: retries with exponential backoff on loss/timeout."""

    def __init__(self, link: WirelessLink, max_retries=3, base_backoff_s=0.4):
        self.link = link
        self.max_retries = max_retries
        self.base_backoff_s = base_backoff_s

    def send(self, raw: bytes, send_time: float, on_delivered) -> SendResult:
        """
        Send one packet, invoking on_delivered(payload, arrival_time) for
        EVERY copy that reaches the receiver (duplicates included).
        Returns aggregate statistics for this packet.
        """
        attempts = 0
        copies = 0
        first_latency = 0.0
        now = send_time

        for attempt in range(self.max_retries + 1):
            attempts += 1
            outcome = self.link.transmit(raw)
            if outcome.delivered:
                copies += 1
                arrival = now + outcome.latency_s
                if copies == 1:
                    first_latency = outcome.latency_s
                on_delivered(outcome.payload, arrival)
                if self.link.ack_ok():
                    return SendResult(True, attempts, copies, first_latency)
                # ACK lost: receiver got it, but we don't know -> retry,
                # which the gateway will observe as a duplicate.
            # Backoff before the next attempt (virtual time only).
            now += self.base_backoff_s * (2 ** attempt)

        return SendResult(False, attempts, copies, first_latency)
