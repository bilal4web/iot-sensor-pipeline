"""
Matplotlib charts for SYNTHETIC simulation results.

Every figure is generated from simulated data and labeled as such.
Uses the Agg backend so plots render headlessly.
"""

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from .metrics import latency_cdf

SYNTH_LABEL = "SYNTHETIC SIMULATION DATA"
plt.rcParams.update({"figure.dpi": 130, "axes.grid": True, "grid.alpha": 0.3})


def _stamp(ax, text=SYNTH_LABEL):
    ax.text(
        0.99,
        0.01,
        text,
        transform=ax.transAxes,
        ha="right",
        va="bottom",
        fontsize=7,
        color="0.45",
    )


def plot_delivery_vs_loss(loss_rates, delivery_rates, path):
    fig, ax = plt.subplots(figsize=(7, 4.2))
    ax.plot(loss_rates, delivery_rates, "o-", color="#0F766E", lw=2)
    ax.set_xlabel("Configured link loss rate")
    ax.set_ylabel("End-to-end delivery rate")
    ax.set_title("Delivery rate vs. wireless link loss (simulated)")
    ax.set_ylim(0, 1.02)
    _stamp(ax)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def plot_latency_cdf(latencies_s, path):
    x, y = latency_cdf(latencies_s)
    fig, ax = plt.subplots(figsize=(7, 4.2))
    ax.plot(x, y, color="#0F766E", lw=2)
    ax.set_xlabel("End-to-end latency (s, virtual time)")
    ax.set_ylabel("CDF")
    ax.set_title("Latency CDF — node to gateway (simulated)")
    for q, style in ((0.5, "--"), (0.9, ":"), (0.99, "-.")):
        idx = int(np.searchsorted(y, q))
        if idx < len(x):
            ax.axvline(x[idx], color="0.5", ls=style, lw=1)
            ax.text(x[idx], q + 0.02, f"p{int(q*100)}={x[idx]:.2f}s", fontsize=8)
    _stamp(ax)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def plot_gateway_outcomes(stats, path):
    labels = ["Accepted\n(unique)", "Duplicates\n(dropped)", "CRC failures\n(dropped)"]
    values = [stats["accepted_unique"], stats["duplicates"], stats["crc_failed"]]
    fig, ax = plt.subplots(figsize=(7, 4.2))
    bars = ax.bar(labels, values, color=["#0F766E", "#D97706", "#DC2626"])
    ax.set_title("Gateway packet outcomes (simulated)")
    ax.set_ylabel("Packets")
    for b, v in zip(bars, values):
        ax.text(b.get_x() + b.get_width() / 2, b.get_height(), f"{v}",
                ha="center", va="bottom", fontsize=9)
    _stamp(ax)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def plot_sample_timeseries(readings, path, node_id="node-0", max_points=300):
    """Raw synthetic readings from one node (before the radio)."""
    sel = [r for r in readings if r.node_id == node_id][:max_points]
    t = np.array([r.ts for r in sel]) / 60.0  # minutes
    fig, axes = plt.subplots(3, 1, figsize=(7, 5.2), sharex=True)
    series = [
        ("temperature_c", "Temperature (°C)", "#DC2626"),
        ("ph", "pH", "#0F766E"),
        ("turbidity_ntu", "Turbidity (NTU)", "#2563EB"),
    ]
    for ax, (attr, label, color) in zip(axes, series):
        ax.plot(t, [getattr(r, attr) for r in sel], color=color, lw=1)
        ax.set_ylabel(label)
    axes[-1].set_xlabel("Time (minutes, virtual)")
    axes[0].set_title(f"Synthetic sensor stream — {node_id} (pre-radio)")
    _stamp(axes[-1])
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
