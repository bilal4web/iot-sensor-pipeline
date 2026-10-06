"""
End-to-end metrics computed from SYNTHETIC simulation runs.

All numbers produced here describe the simulator's behavior under the
configured channel parameters — they are NOT measurements of any real
deployment.
"""

import numpy as np


def delivery_rate(generated_total, accepted_unique):
    """Fraction of generated readings that reached the cloud exactly once."""
    if generated_total == 0:
        return 0.0
    return accepted_unique / generated_total


def latency_cdf(latencies_s, points=200):
    """Return (x, y) for the empirical CDF of end-to-end latency."""
    lat = np.sort(np.asarray(latencies_s, dtype=float))
    if lat.size == 0:
        return np.array([]), np.array([])
    x = np.linspace(lat[0], lat[-1], points)
    y = np.searchsorted(lat, x, side="right") / lat.size
    return x, y


def latency_percentiles(latencies_s, pct=(50, 90, 99)):
    lat = np.asarray(latencies_s, dtype=float)
    if lat.size == 0:
        return {p: float("nan") for p in pct}
    return {p: float(np.percentile(lat, p)) for p in pct}


def summarize_run(generated_total, gateway):
    """One dict of headline metrics for a finished run."""
    gs = gateway.stats()
    lat = latency_percentiles(gateway.latencies_s)
    return {
        "generated": generated_total,
        "accepted_unique": gs["accepted_unique"],
        "delivery_rate": delivery_rate(generated_total, gs["accepted_unique"]),
        "crc_failure_rate": gs["crc_failure_rate"],
        "duplicate_rate": gs["duplicate_rate"],
        "latency_p50_s": lat[50],
        "latency_p90_s": lat[90],
        "latency_p99_s": lat[99],
        "batches_sent": gs["batches_sent"],
    }
