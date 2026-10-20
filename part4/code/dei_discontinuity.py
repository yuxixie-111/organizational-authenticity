"""Did the 2020 values surge decouple from operational DEI?

This is the additional analysis. It is exploratory. The windows were set
from public history, not from inspecting the series and then choosing
the cut that worked.

Windows
-------
pre        2018-2019   before the 2020 shock
shock      2020-2021   George Floyd protests, COVID, first human-capital proxy season
transition 2022        energy shock and the start of the anti-ESG campaign
backlash   2023-2024   after SFFA v. Harvard and state anti-ESG laws

Hypotheses, stated so they can fail
------------------------------------
H1. From pre to shock, the within-firm rise in emphasized inclusion
    language on the About page is larger than the within-firm rise in
    an operational DEI signal in the proxy.
H2. From shock to backlash, stated inclusion falls more in Technology
    and Consumer Discretionary than in Energy.
H3. Firms whose stated inclusion rose more than their operational DEI
    signal from pre to shock also show a larger decline in the
    authenticity index over that same step.

All three use within-firm changes. A firm enters a contrast only when
it has at least one non-missing observation in each window. Levels are
reported too, because a within-firm design can hide a shift that is
common to every firm but visible in the cross-section.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.constants import STATED_EMPHASIS_SHARE, WINDOWS
from src.plotting import SECTOR_COLORS, finish, new_figure

ABOUT = ROOT / "part1" / "data" / "company_year.csv"
PROXY = ROOT / "part2" / "data" / "proxy_company_year.csv"
OAI = ROOT / "part3" / "data" / "authenticity_panel.csv"
DATA_DIR = ROOT / "part4" / "data"
OUT_DIR = ROOT / "part4" / "output"

CONSUMER_FACING = {"Technology", "Consumer Discretionary"}


def window_mean(frame: pd.DataFrame, ticker: str, years: tuple[int, int], column: str) -> float | None:
    part = frame[(frame["ticker"] == ticker) & frame["year"].between(years[0], years[1])]
    values = pd.to_numeric(part[column], errors="coerce").dropna()
    if values.empty:
        return None
    return float(values.mean())


def paired(firm: pd.DataFrame, column: str, start: str, end: str) -> pd.DataFrame:
    left = firm[["ticker", "sector", f"{column}_{start}"]].rename(columns={f"{column}_{start}": "start"})
    right = firm[["ticker", f"{column}_{end}"]].rename(columns={f"{column}_{end}": "end"})
    both = left.merge(right, on="ticker").dropna()
    both["delta"] = both["end"] - both["start"]
    both["outcome"] = column
    both["contrast"] = f"{start}_to_{end}"
    return both


def summarize(deltas: pd.DataFrame) -> dict:
    if deltas.empty:
        return {"n": 0}
    return {
        "n": int(len(deltas)),
        "mean_delta": round(float(deltas["delta"].mean()), 4),
        "median_delta": round(float(deltas["delta"].median()), 4),
        "share_positive": round(float((deltas["delta"] > 0).mean()), 4),
        "share_negative": round(float((deltas["delta"] < 0).mean()), 4),
    }


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    about = pd.read_csv(ABOUT)
    proxy = pd.read_csv(PROXY)
    oai = pd.read_csv(OAI)

    about["stated_inclusion_share"] = pd.to_numeric(about["theme_share_inclusion"], errors="coerce")
    about.loc[about["page_text_clean"].fillna("").str.len().eq(0), "stated_inclusion_share"] = np.nan
    about["stated_inclusion_emphasized"] = np.where(
        about["stated_inclusion_share"].isna(),
        np.nan,
        (about["stated_inclusion_share"] >= STATED_EMPHASIS_SHARE).astype(float),
    )
    proxy["operational_dei"] = pd.to_numeric(proxy["operational_dei"], errors="coerce")
    proxy.loc[proxy["gap_reason"].fillna("").ne(""), "operational_dei"] = np.nan
    proxy["lived_inclusion_per_1k"] = pd.to_numeric(proxy["theme_per_1k_inclusion"], errors="coerce")
    proxy.loc[proxy["gap_reason"].fillna("").ne(""), "lived_inclusion_per_1k"] = np.nan

    base = about[["ticker", "company_name", "sector", "year", "stated_inclusion_share", "stated_inclusion_emphasized"]].merge(
        proxy[["ticker", "year", "operational_dei", "lived_inclusion_per_1k"]],
        on=["ticker", "year"],
        how="outer",
    ).merge(
        oai[["ticker", "year", "oai"]],
        on=["ticker", "year"],
        how="left",
    )
    outcomes = [
        "stated_inclusion_share",
        "stated_inclusion_emphasized",
        "operational_dei",
        "lived_inclusion_per_1k",
        "oai",
    ]
    firm_rows = []
    for ticker, part in base.groupby("ticker"):
        row = {
            "ticker": ticker,
            "company_name": part["company_name"].dropna().iloc[0],
            "sector": part["sector"].dropna().iloc[0],
        }
        for name, bounds in WINDOWS.items():
            for outcome in outcomes:
                row[f"{outcome}_{name}"] = window_mean(part, ticker, bounds, outcome)
        firm_rows.append(row)
    firm = pd.DataFrame(firm_rows)
    firm["decoupling_gap_pre_to_shock"] = (
        firm["stated_inclusion_emphasized_shock"] - firm["stated_inclusion_emphasized_pre"]
    ) - (
        firm["operational_dei_shock"] - firm["operational_dei_pre"]
    )
    firm["oai_change_pre_to_shock"] = firm["oai_shock"] - firm["oai_pre"]
    firm.to_csv(DATA_DIR / "firm_windows.csv", index=False)

    contrasts = [("pre", "shock"), ("shock", "backlash")]
    contrast_frames = []
    hypothesis = {}
    for start, end in contrasts:
        for outcome in outcomes:
            deltas = paired(firm, outcome, start, end)
            contrast_frames.append(deltas)
            hypothesis[f"{outcome}_{start}_to_{end}"] = summarize(deltas)
            for sector, part in deltas.groupby("sector"):
                hypothesis[f"{outcome}_{start}_to_{end}__{sector}"] = summarize(part)

    # H1 compares two changes that are both on a 0/1 scale.
    h1_stated = paired(firm, "stated_inclusion_emphasized", "pre", "shock")
    h1_lived = paired(firm, "operational_dei", "pre", "shock")
    h1 = h1_stated[["ticker", "sector", "delta"]].merge(
        h1_lived[["ticker", "delta"]],
        on="ticker",
        suffixes=("_stated", "_operational"),
    )
    h1["stated_minus_operational"] = h1["delta_stated"] - h1["delta_operational"]
    hypothesis["H1"] = {
        **summarize(h1.rename(columns={"stated_minus_operational": "delta"})),
        "mean_stated_delta": round(float(h1["delta_stated"].mean()), 4) if len(h1) else None,
        "mean_operational_delta": round(float(h1["delta_operational"].mean()), 4) if len(h1) else None,
        "interpretation": (
            "Supported if mean_stated_delta exceeds mean_operational_delta. "
            "The difference itself is in the mean_delta field."
        ),
    }

    # H2. Consumer-facing sectors versus energy, shock to backlash, continuous share.
    h2 = paired(firm, "stated_inclusion_share", "shock", "backlash")
    facing = h2[h2["sector"].isin(CONSUMER_FACING)]
    energy = h2[h2["sector"] == "Energy"]
    hypothesis["H2"] = {
        "consumer_facing_tech_and_discretionary": summarize(facing),
        "energy": summarize(energy),
        "healthcare": summarize(h2[h2["sector"] == "Healthcare"]),
        "financials": summarize(h2[h2["sector"] == "Financials"]),
        "interpretation": (
            "Supported if the consumer-facing mean delta is more negative than the energy mean delta."
        ),
    }

    # H3. Correlation of the decoupling gap with the OAI change.
    h3 = firm[["decoupling_gap_pre_to_shock", "oai_change_pre_to_shock"]].dropna()
    if len(h3) >= 5 and h3.iloc[:, 0].std() > 0 and h3.iloc[:, 1].std() > 0:
        corr = float(np.corrcoef(h3.iloc[:, 0], h3.iloc[:, 1])[0, 1])
    else:
        corr = None
    hypothesis["H3"] = {
        "n": int(len(h3)),
        "correlation_gap_with_oai_change": None if corr is None else round(corr, 4),
        "interpretation": (
            "Supported if the correlation is negative: a larger rhetoric-minus-practice "
            "jump coincides with a fall in the authenticity index."
        ),
    }
    (OUT_DIR / "hypothesis_summary.json").write_text(json.dumps(hypothesis, indent=2))
    if contrast_frames:
        pd.concat(contrast_frames, ignore_index=True).to_csv(DATA_DIR / "firm_deltas.csv", index=False)

    # Levels over time, for the figure that a reader can check by eye.
    yearly = base.groupby("year", as_index=False).agg(
        stated_inclusion_share=("stated_inclusion_share", "mean"),
        stated_inclusion_emphasized=("stated_inclusion_emphasized", "mean"),
        operational_dei=("operational_dei", "mean"),
        lived_inclusion_per_1k=("lived_inclusion_per_1k", "mean"),
        oai=("oai", "mean"),
        n_stated=("stated_inclusion_share", "count"),
        n_operational=("operational_dei", "count"),
    )
    yearly.to_csv(OUT_DIR / "yearly_levels.csv", index=False)

    fig, ax = new_figure()
    ax.plot(yearly["year"], yearly["stated_inclusion_emphasized"], marker="o", label="About page emphasizes inclusion", color="#CC79A7")
    ax.plot(yearly["year"], yearly["operational_dei"], marker="o", label="Proxy has an operational DEI signal", color="#0072B2")
    ax.set_ylim(-0.05, 1.05)
    ax.axvspan(2019.5, 2021.5, color="#CC79A7", alpha=0.08)
    ax.axvspan(2022.5, 2024.5, color="#E69F00", alpha=0.10)
    finish(
        ax,
        "Stated inclusion versus operational DEI",
        "Year",
        "Share of firms",
        OUT_DIR / "stated_vs_operational_dei.png",
    )

    h2_means = []
    for sector in SECTOR_COLORS:
        part = h2[h2["sector"] == sector]
        if part.empty:
            continue
        h2_means.append((sector, float(part["delta"].mean()), int(len(part))))
    if h2_means:
        fig, ax = new_figure(9, 5)
        labels = [item[0] for item in h2_means]
        values = [item[1] for item in h2_means]
        colors = [SECTOR_COLORS[label] for label in labels]
        ax.bar(labels, values, color=colors)
        ax.axhline(0, color="black", linewidth=0.8)
        ax.legend().remove() if ax.get_legend() else None
        ax.set_title("Change in About-page inclusion share, 2020-21 to 2023-24")
        ax.set_xlabel("")
        ax.set_ylabel("Within-firm change in theme share")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        fig.tight_layout()
        fig.savefig(OUT_DIR / "backlash_by_sector.png", dpi=140)
        import matplotlib.pyplot as plt
        plt.close(fig)

    print(json.dumps({"H1": hypothesis["H1"], "H2": hypothesis["H2"], "H3": hypothesis["H3"]}, indent=2))


if __name__ == "__main__":
    main()
