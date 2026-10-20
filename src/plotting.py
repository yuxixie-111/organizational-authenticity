"""Small shared figure settings so the four parts look like one project."""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

# Okabe-Ito, readable in grayscale and for common forms of color blindness.
SECTOR_COLORS = {
    "Technology": "#0072B2",
    "Financials": "#E69F00",
    "Healthcare": "#009E73",
    "Consumer Discretionary": "#CC79A7",
    "Energy": "#D55E00",
}


def new_figure(width: float = 10, height: float = 5.5):
    fig, ax = plt.subplots(figsize=(width, height))
    return fig, ax


def finish(ax, title: str, xlabel: str, ylabel: str, path) -> None:
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.legend(frameon=False, fontsize=8)
    ax.figure.tight_layout()
    ax.figure.savefig(path, dpi=140)
    plt.close(ax.figure)
