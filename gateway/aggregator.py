"""
Gateway aggregator: the edge between the (simulated) radio and the cloud.

Responsibilities:
  * validate CRC on every received frame (drop corrupted ones),
  * deduplicate retransmissions by (node_id, seq),
  * batch accepted readings and forward them to the cloud ingest API.

All traffic processed here is SYNTHETIC simulation output.
"""

import json
import urllib.request

from sensors.node import deserialize, verify_crc


class Gateway:
    def __init__(self, cloud_url=None, batch_size=20):
        self.cloud_url = cloud_url.rstrip("/") if cloud_url else None
        self.batch_size = batch_size
        self._buffer = []
        self._seen = set()  # (node_id, seq) already accepted
        # Counters for analysis.
        self.received_total = 0
        self.crc_failed = 0
        self.duplicates = 0
        self.accepted = 0
        self.batches_sent = 0
        self.latencies_s = []  # arrival_time - node send ts, per unique reading

    def receive(self, raw: bytes, arrival_time: float):
        """Handle one delivered frame (duplicates included)."""
        self.received_total += 1
        try:
            packet = deserialize(raw)
        except (ValueError, UnicodeDecodeError):
            self.crc_failed += 1
            return
        if not verify_crc(packet):
            self.crc_failed += 1
            return
        key = (packet["node_id"], packet["seq"])
        if key in self._seen:
            self.duplicates += 1
            return
        self._seen.add(key)
        self.accepted += 1
        self.latencies_s.append(max(0.0, arrival_time - packet["ts"]))
        self._buffer.append(packet)
        if len(self._buffer) >= self.batch_size:
            self.flush()

    def flush(self):
        """POST the current batch to the cloud ingest API."""
        if not self._buffer:
            return
        batch = self._buffer
        self._buffer = []
        if self.cloud_url is None:
            return  # analysis-only mode: no cloud attached
        data = json.dumps({"readings": batch}).encode()
        req = urllib.request.Request(
            self.cloud_url + "/readings",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            resp.read()
        self.batches_sent += 1

    def stats(self):
        total = self.received_total or 1
        return {
            "received_total": self.received_total,
            "crc_failed": self.crc_failed,
            "crc_failure_rate": self.crc_failed / total,
            "duplicates": self.duplicates,
            "duplicate_rate": self.duplicates / total,
            "accepted_unique": self.accepted,
            "batches_sent": self.batches_sent,
        }
