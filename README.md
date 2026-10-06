# IoT Sensor-to-Cloud Pipeline Simulator

> **HONESTY DISCLAIMER — read first.** This is an **educational demonstration**
> inspired by the *architecture* of the CISNR (Center for Intelligence Systems
> and Network Research, UET Peshawar) E. coli rapid-detection project. It is
> **not** the actual CISNR system, it contains **none** of its data, and every
> number it produces is **synthetic simulation output** — no real sensor counts,
> accuracy claims, uptime statistics, or field results are implied anywhere.

## What it is

A small, readable Python simulator of the classic IoT pipeline:

```
 +----------------+      lossy radio + ARQ retries      +---------------+
 |  Sensor nodes  |  ===============================>  |    Gateway    |
 | temp / pH /    |   loss, latency, bit-errors, ACKs   | CRC + dedup   |
 | turbidity (all |                                     | batching      |
 | synthetic)     |                                     +-------+-------+
 +----------------+                                             | batched HTTPS
                                                                v
                                                        +---------------+
                                                        | Cloud ingest  |
                                                        | mock HTTP API |
                                                        +-------+-------+
                                                                |
                                                                v
                                                        +---------------+
                                                        | Analysis +    |
                                                        | dashboard     |
                                                        +---------------+
```

Each stage:

| Stage | File | What it does |
|---|---|---|
| Sensor node | `sensors/node.py` | Emulates nodes emitting temperature, pH, turbidity readings with timestamps, sequence numbers, and CRC32 checksums. All values synthetic. |
| Wireless link | `wireless/link.py` | Configurable packet-loss rate, latency distribution, bit-error corruption, plus a stop-and-wait ARQ sender with exponential backoff. Lost ACKs surface as duplicates downstream. |
| Gateway | `gateway/aggregator.py` | Validates CRC (drops corrupted frames), deduplicates `(node_id, seq)` retransmissions, batches readings, POSTs batches to the cloud. |
| Cloud ingest | `cloud/ingest.py` | Mock cloud: local HTTP server (`POST /readings`, `GET /api/readings`, `GET /api/stats`), stores to memory + JSONL. |
| Analysis | `analysis/` | End-to-end metrics and matplotlib charts from the simulated run. |
| Dashboard | `dashboard.html` | Static page: pipeline diagram, run metrics, charts. Regenerated each run. |

## How to run

```bash
pip install -r requirements.txt
python3 run_pipeline.py
```

Options:

```bash
python3 run_pipeline.py --loss 0.20 --nodes 4 --readings 300 --seed 42
```

Runtime is well under a minute for defaults (3 nodes × 240 readings, plus a
small loss sweep). The script prints progress, writes `results/*.png`,
`results/summary.json`, `results/cloud_readings.jsonl`, and `dashboard.html`.

## Sample results (simulation outputs — not real measurements)

Typical default run (`--loss 0.10`, seed 7):

- Readings generated: 720 (3 nodes × 240)
- Delivery rate: ~99.9% (ARQ retries recover almost all losses)
- CRC failure rate: ~0.1% of received frames
- Duplicate rate: ~10% of received frames (lost ACKs → retransmits, dropped by dedup)
- End-to-end latency p50 ≈ 0.12 s, p99 ≈ 0.6 s (virtual time)

Loss sweep (delivery rate vs. configured link loss, 3 nodes × 80 readings each):

| Link loss | Delivery rate (simulated) |
|---|---|
| 0% | 100% |
| 5% | 100% |
| 10% | 100% |
| 20% | 100% |
| 30% | ~99.6% |

(Exact figures vary with `--seed`; see `results/summary.json` after your run.
With 3 ARQ retries, delivery stays near-perfect — the *cost* of loss shows up
instead as duplicate traffic (~10% at 10% loss) and a longer latency tail.
Try `--loss 0.5` to watch delivery finally degrade.)

## Project structure

```
iot-sensor-pipeline/
├── sensors/node.py          # synthetic sensor emulator + CRC packets
├── wireless/link.py         # lossy link model + ARQ sender
├── gateway/aggregator.py    # CRC check, dedup, batching, cloud POST
├── cloud/ingest.py          # mock cloud HTTP API (stdlib only)
├── analysis/metrics.py      # delivery/latency/CRC/duplicate metrics
├── analysis/plots.py        # matplotlib charts
├── run_pipeline.py          # one-command end-to-end demo
├── dashboard.html           # regenerated static dashboard
├── results/                 # charts, summary.json, cloud_readings.jsonl
├── requirements.txt
└── README.md
```

## Notes & limits

- Time is *virtual*: latencies/backoffs advance a simulated clock, so runs are
  fast. Only the cloud HTTP hop is real (localhost).
- The corruption model flips a single random byte per corrupted frame — a
  teaching simplification, not a real bit-error model.
- No security, no TLS, no auth on the mock cloud — it is a local demo stand-in.
