"""Build the firm-year Organizational Authenticity Index.

The index is missing unless both the About page and the proxy exist and
the About page has at least one codebook theme. A firm that does not
publish values language is reported as undefined, not as inauthentic.
Berkshire is the case this rule is written for.

Two sensitivities are stored beside the main score. Bonus 0 uses the
proxy's word mix only. Bonus 5 lets a concrete practice dominate the
lived vector. The main score uses the pre-registered bonus of 2.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.constants import FACE_VALIDITY_TICKERS, LIVED_FLAG_BONUS, YEARS
from src.measure import authenticity_score, cosine_excluding, lived_composition
from src.plotting import SECTOR_COLORS, finish, new_figure
from src.taxonomy import THEME_FLAGS, THEME_ORDER

PART1 = ROOT / "part1" / "data" / "company_year.csv"
PART2 = ROOT / "part2" / "data" / "proxy_company_year.csv"
DATA_DIR = ROOT / "part3" / "data"
OUT_DIR = ROOT / "part3" / "output"

FLAG_COLUMNS = sorted({flag for flags in THEME_FLAGS.values() for flag in flags})


def _shares(row: pd.Series, prefix: str) -> dict[str, float] | None:
    values = {}
    for theme in THEME_ORDER:
        value = row.get(f"{prefix}{theme}")
        if pd.isna(value):
            return None
        values[theme] = float(value)
    if sum(values.values()) <= 0:
        return None
    return values


def _flags(row: pd.Series) -> dict[str, int]:
    return {name: int(row[name]) if name in row and not pd.isna(row[name]) else 0 for name in FLAG_COLUMNS}


def _score_frame(frame: pd.DataFrame, bonus: float) -> pd.DataFrame:
    """Recompute with a different practice bonus without touching the texts.

    lived_composition reads LIVED_FLAG_BONUS from constants, so the
    sensitivity rebuilds the lived mix here with the same rule.
    """
    rows = []
    for _, row in frame.iterrows():
        stated = _shares(row, "stated_share_")
        flags = _flags(row)
        if stated is None or row["proxy_missing"] == 1:
            scored = {
                "cosine_alignment": None,
                "follow_through": None,
                "n_emphasized_themes": 0,
                "n_operationalized_themes": 0,
                "oai": None,
                "cosine_ex_shareholder": None,
            }
        else:
            raw = {}
            for theme in THEME_ORDER:
                verbal = float(row[f"lived_per_1k_{theme}"])
                practice = bonus if any(flags.get(flag, 0) > 0 for flag in THEME_FLAGS.get(theme, [])) else 0.0
                raw[theme] = verbal + practice
            total = sum(raw.values())
            lived = None if total <= 0 else {theme: value / total for theme, value in raw.items()}
            if bonus == LIVED_FLAG_BONUS:
                # Use the shared function so the main score cannot drift.
                lived = lived_composition(
                    {theme: float(row[f"lived_per_1k_{theme}"]) for theme in THEME_ORDER},
                    flags,
                )
            scored = authenticity_score(stated, lived, flags)
            scored["cosine_ex_shareholder"] = cosine_excluding(stated, lived)
        rows.append(scored)
    return pd.DataFrame(rows)


def pearson(left: pd.Series, right: pd.Series) -> float | None:
    pair = pd.concat([left, right], axis=1).dropna()
    if len(pair) < 5:
        return None
    if pair.iloc[:, 0].std() == 0 or pair.iloc[:, 1].std() == 0:
        return None
    return float(np.corrcoef(pair.iloc[:, 0], pair.iloc[:, 1])[0, 1])


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    about = pd.read_csv(PART1)
    proxy = pd.read_csv(PART2)
    about_keep = ["ticker", "company_name", "sector", "year", "word_count", "gap_reason"] + [
        f"theme_share_{theme}" for theme in THEME_ORDER
    ]
    about = about[about_keep].rename(columns={
        "word_count": "about_words",
        "gap_reason": "about_gap",
        **{f"theme_share_{theme}": f"stated_share_{theme}" for theme in THEME_ORDER},
    })
    proxy_keep = ["ticker", "year", "word_count", "gap_reason", "operational_dei", "operational_climate"] + [
        f"theme_per_1k_{theme}" for theme in THEME_ORDER
    ] + FLAG_COLUMNS
    proxy = proxy[proxy_keep].rename(columns={
        "word_count": "proxy_words",
        "gap_reason": "proxy_gap",
        **{f"theme_per_1k_{theme}": f"lived_per_1k_{theme}" for theme in THEME_ORDER},
    })
    panel = about.merge(proxy, on=["ticker", "year"], how="outer")
    panel["about_missing"] = panel["about_gap"].fillna("missing").ne("").astype(int)
    # A blank gap reason means the document exists. NaN from the merge means the row was absent.
    panel["about_missing"] = np.where(panel["about_words"].fillna(0).gt(0), 0, 1)
    panel["proxy_missing"] = np.where(panel["proxy_words"].fillna(0).gt(0), 0, 1)

    main_scores = _score_frame(panel, LIVED_FLAG_BONUS)
    low_bonus = _score_frame(panel, 0.0)
    high_bonus = _score_frame(panel, 5.0)
    panel["cosine_alignment"] = main_scores["cosine_alignment"]
    panel["follow_through"] = main_scores["follow_through"]
    panel["n_emphasized_themes"] = main_scores["n_emphasized_themes"]
    panel["n_operationalized_themes"] = main_scores["n_operationalized_themes"]
    panel["oai"] = main_scores["oai"]
    panel["cosine_ex_shareholder"] = main_scores["cosine_ex_shareholder"]
    panel["oai_bonus0"] = low_bonus["oai"]
    panel["oai_bonus5"] = high_bonus["oai"]
    panel["practice_bonus"] = LIVED_FLAG_BONUS
    panel.to_csv(DATA_DIR / "authenticity_panel.csv", index=False)

    scored = panel.dropna(subset=["oai"])
    dist = {
        "n_scored": int(len(scored)),
        "n_panel": int(len(panel)),
        "mean": round(float(scored["oai"].mean()), 2) if len(scored) else None,
        "std": round(float(scored["oai"].std()), 2) if len(scored) else None,
        "min": round(float(scored["oai"].min()), 2) if len(scored) else None,
        "p25": round(float(scored["oai"].quantile(0.25)), 2) if len(scored) else None,
        "median": round(float(scored["oai"].median()), 2) if len(scored) else None,
        "p75": round(float(scored["oai"].quantile(0.75)), 2) if len(scored) else None,
        "max": round(float(scored["oai"].max()), 2) if len(scored) else None,
        "mean_cosine": round(float(scored["cosine_alignment"].mean()), 3) if len(scored) else None,
        "mean_follow_through": (
            None if scored["follow_through"].dropna().empty
            else round(float(scored["follow_through"].mean()), 3)
        ),
        "corr_about_words": None if pearson(scored["oai"], scored["about_words"]) is None else round(pearson(scored["oai"], scored["about_words"]), 3),
        "corr_proxy_words": None if pearson(scored["oai"], scored["proxy_words"]) is None else round(pearson(scored["oai"], scored["proxy_words"]), 3),
        "corr_bonus0": None if pearson(scored["oai"], scored["oai_bonus0"]) is None else round(pearson(scored["oai"], scored["oai_bonus0"]), 3),
        "corr_bonus5": None if pearson(scored["oai"], scored["oai_bonus5"]) is None else round(pearson(scored["oai"], scored["oai_bonus5"]), 3),
        "by_sector": scored.groupby("sector")["oai"].mean().round(2).to_dict() if len(scored) else {},
        "by_year": {str(year): round(float(value), 2) for year, value in scored.groupby("year")["oai"].mean().items()} if len(scored) else {},
    }
    (OUT_DIR / "distribution.json").write_text(json.dumps(dist, indent=2))

    by_sector_year = scored.groupby(["sector", "year"], as_index=False)["oai"].mean() if len(scored) else pd.DataFrame()
    if len(by_sector_year):
        by_sector_year.to_csv(OUT_DIR / "oai_by_sector_year.csv", index=False)

    # Face-validity cases were named in src/constants.py before scoring.
    cases = scored[scored["ticker"].isin(FACE_VALIDITY_TICKERS)].copy()
    case_summary = cases.groupby(["ticker", "company_name", "sector"], as_index=False).agg(
        n=("oai", "size"),
        oai=("oai", "mean"),
        cosine=("cosine_alignment", "mean"),
        follow_through=("follow_through", "mean"),
    )
    case_summary = case_summary.sort_values("oai")
    case_summary.to_csv(OUT_DIR / "face_validity_cases.csv", index=False)

    firm_mean = scored.groupby(["ticker", "company_name", "sector"], as_index=False)["oai"].mean()
    firm_mean = firm_mean.sort_values("oai")
    pd.concat([firm_mean.head(8), firm_mean.tail(8)]).to_csv(OUT_DIR / "oai_extremes.csv", index=False)

    if len(scored):
        fig, ax = new_figure(8, 5)
        ax.hist(scored["oai"], bins=15, color="#0072B2", edgecolor="white")
        ax.legend().remove() if ax.get_legend() else None
        ax.set_title("Distribution of the Organizational Authenticity Index")
        ax.set_xlabel("Index (0-100)")
        ax.set_ylabel("Firm-years")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        fig.tight_layout()
        fig.savefig(OUT_DIR / "oai_histogram.png", dpi=140)
        import matplotlib.pyplot as plt
        plt.close(fig)

        fig, ax = new_figure()
        for sector, color in SECTOR_COLORS.items():
            part = by_sector_year[by_sector_year["sector"] == sector]
            ax.plot(part["year"], part["oai"], marker="o", label=sector, color=color)
        ax.set_xticks(YEARS)
        finish(ax, "Mean authenticity by sector and year", "Year", "Organizational Authenticity Index", OUT_DIR / "oai_by_sector_year.png")

    print(json.dumps(dist, indent=2))
    if len(case_summary):
        print(case_summary.to_string(index=False))
    if len(firm_mean):
        print("LOWEST")
        print(firm_mean.head(8).to_string(index=False))
        print("HIGHEST")
        print(firm_mean.tail(8).to_string(index=False))


if __name__ == "__main__":
    main()
