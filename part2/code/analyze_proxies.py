"""Text-mine proxy statements: theme mix, tone, and operational practices.

Word densities are per 1,000 words so a long proxy is not scored as
having stronger values. Behavioral flags record a concrete practice
(a representation statistic, a pay link, an emissions target). Those
flags are what Part 3 treats as lived priority. Theme words alone,
inside a legal document, are too easy to produce.

The same change rule as Part 1 is stored for symmetry. Proxies rewrite
numbers every year, so similarity will run lower than on About pages.
The theme-mix shift and the flag changes are the quantities the summary
interprets.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.companies import COMPANIES
from src.constants import CHANGE_THRESHOLD, EVENT_CONTEXT, RUBRIC_VERSION, YEARS
from src.plotting import SECTOR_COLORS, finish, new_figure
from src.taxonomy import THEME_LABELS, THEME_ORDER, behavioral_flags, theme_counts
from src.textutil import (
    cosine_similarity,
    linguistic_features,
    notable_shift,
    per_thousand,
    sha1_text,
    shares_from_counts,
    tone_net,
    word_count,
)

PART2 = ROOT / "part2"
META_DIR = PART2 / "data" / "meta"
TEXT_DIR = PART2 / "data" / "text"
OUT_DIR = PART2 / "output"
DATA_DIR = PART2 / "data"

INCLUSION_FLAGS = ["flag_dei_metrics", "flag_pay_equity", "flag_inclusion_in_pay"]


def load_text(ticker: str, year: int) -> str:
    path = TEXT_DIR / f"{ticker}_{year}.txt"
    if not path.exists():
        return ""
    return path.read_text()


def narrate(row: dict, prior: dict | None) -> str:
    if row["gap_reason"]:
        return (
            f"No DEF 14A for {row['year']}. Reason: {row['gap_reason']}. "
            "The next or previous proxy was not substituted."
        )
    bits = [f"Proxy filed {row['filing_date']} ({row['word_count']} words)."]
    top = [
        theme for theme in THEME_ORDER
        if (row.get(f"theme_share_{theme}") or 0) >= 0.12
    ]
    if top:
        bits.append(
            "Largest theme shares: " + ", ".join(THEME_LABELS[theme] for theme in top) + "."
        )
    practices = []
    if row["operational_dei"] == 1:
        practices.append("a numeric or pay-linked DEI practice")
    if row["flag_emissions_target"] == 1:
        practices.append("an emissions or climate target")
    if row["flag_safety_metrics"] == 1:
        practices.append("a safety rate")
    if row["flag_human_capital_metrics"] == 1:
        practices.append("a human-capital metric")
    if row["flag_climate_in_pay"] == 1 or row["flag_inclusion_in_pay"] == 1:
        practices.append("a values metric inside the pay design")
    if practices:
        bits.append("Operational signals present: " + "; ".join(practices) + ".")
    else:
        bits.append("No discretionary operational signal in the codebook fired.")
    if prior is None or not prior.get("word_count"):
        bits.append(f"Change from {row['year'] - 1} was not coded because that proxy is missing.")
    else:
        bits.append(
            f"Content-word similarity to {row['year'] - 1} is {row['similarity_to_prior']:.2f}."
        )
        shifts = []
        for label in ("commitment_per_1k", "positive_per_1k", "negative_per_1k"):
            note = notable_shift(row, prior, label)
            if note:
                shifts.append(note)
        inclusion_now = row.get("theme_per_1k_inclusion")
        inclusion_then = prior.get("theme_per_1k_inclusion")
        if inclusion_now is not None and inclusion_then is not None:
            delta = inclusion_now - inclusion_then
            if abs(delta) >= 0.4:
                direction = "rose" if delta > 0 else "fell"
                shifts.append(
                    f"inclusion density {direction} from {inclusion_then:.2f} to {inclusion_now:.2f} per 1,000 words"
                )
        if row["operational_dei"] != prior.get("operational_dei"):
            shifts.append(
                "operational DEI signal turned "
                + ("on" if row["operational_dei"] == 1 else "off")
            )
        if shifts:
            bits.append("Within-firm moves: " + "; ".join(shifts) + ".")
    return " ".join(bits)[:1200]


def build_rows() -> pd.DataFrame:
    records = []
    for company in COMPANIES:
        for year in YEARS:
            meta_path = META_DIR / f"{company.ticker}_{year}.json"
            meta = json.loads(meta_path.read_text()) if meta_path.exists() else {"status": "gap", "gap_reason": "not_attempted"}
            text = load_text(company.ticker, year) if meta.get("status") == "ok" else ""
            words = word_count(text)
            counts = theme_counts(text) if text else {theme: 0 for theme in THEME_ORDER}
            share = shares_from_counts(counts) if text else None
            flags = behavioral_flags(text) if text else {}
            ling = linguistic_features(text) if text else {}
            row = {
                "ticker": company.ticker,
                "company_name": company.name,
                "sector": company.sector,
                "year": year,
                "document_type": meta.get("form") or "DEF 14A",
                "source": "SEC EDGAR submissions API",
                "cik_used": meta.get("cik_used", ""),
                "accession": meta.get("accession", ""),
                "filing_date": meta.get("filing_date", ""),
                "source_url": meta.get("source_url", ""),
                "text_path": str(TEXT_DIR / f"{company.ticker}_{year}.txt") if text else "",
                "text_sha1": sha1_text(text) if text else "",
                "gap_reason": "" if text else (meta.get("gap_reason") or "not_attempted"),
                "word_count": words,
                "event_context": EVENT_CONTEXT[year],
                "rubric_version": RUBRIC_VERSION,
            }
            for theme in THEME_ORDER:
                row[f"theme_count_{theme}"] = counts[theme]
                row[f"theme_per_1k_{theme}"] = None if not text else round(per_thousand(counts[theme], words), 4)
                row[f"theme_share_{theme}"] = None if share is None else round(share[theme], 4)
            present = []
            if share:
                present = [theme for theme in THEME_ORDER if share[theme] >= 0.08]
            row["theme_categories"] = "|".join(present)
            for name, count in flags.items():
                row[f"{name}_count"] = count
                row[name] = 1 if count > 0 else 0
            if not text:
                for name in (
                    "flag_dei_metrics", "flag_pay_equity", "flag_inclusion_in_pay",
                    "flag_emissions_target", "flag_climate_in_pay", "flag_board_esg_oversight",
                    "flag_safety_metrics", "flag_safety_in_pay", "flag_human_capital_metrics",
                    "flag_customer_metric_in_pay", "flag_political_disclosure",
                    "flag_community_investment",
                ):
                    row[f"{name}_count"] = 0
                    row[name] = 0
            row["operational_dei"] = int(any(row.get(flag, 0) == 1 for flag in INCLUSION_FLAGS)) if text else 0
            row["operational_climate"] = int(
                bool(text) and (row.get("flag_emissions_target", 0) == 1 or row.get("flag_climate_in_pay", 0) == 1)
            )
            for key in ("commitment_per_1k", "positive_per_1k", "negative_per_1k", "uncertainty_per_1k", "we_our_per_1k", "numeric_token_share"):
                value = ling.get(key)
                row[key] = None if value is None else round(float(value), 4)
            row["tone_net"] = None
            if text:
                net = tone_net(ling.get("positive_per_1k"), ling.get("negative_per_1k"))
                row["tone_net"] = None if net is None else round(net, 4)
            records.append(row)

    lookup = {(row["ticker"], row["year"]): row for row in records}
    for row in records:
        prior = lookup.get((row["ticker"], row["year"] - 1))
        prior_text = load_text(row["ticker"], row["year"] - 1) if prior and not prior["gap_reason"] else ""
        current_text = load_text(row["ticker"], row["year"]) if not row["gap_reason"] else ""
        if not current_text or not prior_text:
            row["similarity_to_prior"] = None
            row["changed_from_prior"] = ""
            row["theme_mix_shift"] = None
        else:
            similarity = cosine_similarity(current_text, prior_text)
            row["similarity_to_prior"] = None if similarity is None else round(similarity, 4)
            row["changed_from_prior"] = (
                "true" if similarity is not None and similarity < CHANGE_THRESHOLD else "false"
            )
            distance = 0.0
            for theme in THEME_ORDER:
                distance += abs((row[f"theme_share_{theme}"] or 0) - (prior[f"theme_share_{theme}"] or 0))
            row["theme_mix_shift"] = round(distance / 2.0, 4)
        row["analyst_notes"] = narrate(row, prior if prior and not prior["gap_reason"] else None)
    return pd.DataFrame.from_records(records)


def write_figures(df: pd.DataFrame) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    usable = df[df["gap_reason"].eq("")].copy()
    coverage = df.assign(has_text=df["gap_reason"].eq("")).groupby(["sector", "year"], as_index=False)["has_text"].mean()
    fig, ax = new_figure()
    for sector, color in SECTOR_COLORS.items():
        part = coverage[coverage["sector"] == sector]
        ax.plot(part["year"], part["has_text"], marker="o", label=sector, color=color)
    ax.set_ylim(-0.05, 1.05)
    ax.set_xticks(YEARS)
    finish(ax, "Share of firms with a DEF 14A in the panel", "Filing year", "Share of firms", OUT_DIR / "coverage_by_sector.png")

    fig, ax = new_figure()
    for sector, color in SECTOR_COLORS.items():
        part = usable[usable["sector"] == sector]
        means = part.groupby("year")["theme_per_1k_inclusion"].mean()
        ax.plot(means.index, means.values, marker="o", label=sector, color=color)
    ax.set_xticks(YEARS)
    finish(ax, "Inclusion language in proxies, by sector", "Filing year", "Mentions per 1,000 words", OUT_DIR / "inclusion_density_by_sector.png")

    fig, ax = new_figure()
    for column, label, color in (
        ("operational_dei", "DEI practice", "#CC79A7"),
        ("operational_climate", "Climate target or pay link", "#009E73"),
        ("flag_safety_metrics", "Safety rate", "#D55E00"),
        ("flag_human_capital_metrics", "Human-capital metric", "#0072B2"),
    ):
        means = usable.groupby("year")[column].mean()
        ax.plot(means.index, means.values, marker="o", label=label, color=color)
    ax.set_ylim(-0.05, 1.05)
    ax.set_xticks(YEARS)
    finish(ax, "Share of proxies with a concrete practice", "Filing year", "Share of proxies", OUT_DIR / "operational_flags_by_year.png")


def write_stats(df: pd.DataFrame) -> dict:
    usable = df[df["gap_reason"].eq("")]
    stats = {
        "firm_years": int(len(df)),
        "with_text": int(len(usable)),
        "coverage_rate": round(float(df["gap_reason"].eq("").mean()), 4),
        "gap_reasons": df.loc[df["gap_reason"].ne(""), "gap_reason"].value_counts().to_dict(),
        "median_words": round(float(usable["word_count"].median()), 1) if len(usable) else None,
        "median_similarity": (
            None if usable["similarity_to_prior"].dropna().empty
            else round(float(usable["similarity_to_prior"].median()), 4)
        ),
        "operational_dei_rate": round(float(usable["operational_dei"].mean()), 4) if len(usable) else None,
        "operational_climate_rate": round(float(usable["operational_climate"].mean()), 4) if len(usable) else None,
        "inclusion_per_1k_by_year": {
            str(year): round(float(values), 3)
            for year, values in usable.groupby("year")["theme_per_1k_inclusion"].mean().items()
        },
    }
    (OUT_DIR / "stats.json").write_text(json.dumps(stats, indent=2))
    return stats


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    df = build_rows()
    front = [
        "ticker", "company_name", "sector", "year", "document_type",
        "theme_categories", "changed_from_prior", "analyst_notes",
    ]
    rest = [column for column in df.columns if column not in front]
    df = df[front + rest]
    df.to_csv(DATA_DIR / "proxy_company_year.csv", index=False)
    df[df["gap_reason"].ne("")][
        ["ticker", "company_name", "sector", "year", "gap_reason", "source_url"]
    ].to_csv(DATA_DIR / "coverage_gaps.csv", index=False)
    # A small year-level file for the event discussion, one row per year.
    usable = df[df["gap_reason"].eq("")]
    yearly = usable.groupby("year", as_index=False).agg(
        n=("ticker", "size"),
        inclusion_per_1k=("theme_per_1k_inclusion", "mean"),
        environment_per_1k=("theme_per_1k_environment", "mean"),
        integrity_per_1k=("theme_per_1k_integrity", "mean"),
        tone_net=("tone_net", "mean"),
        operational_dei=("operational_dei", "mean"),
        operational_climate=("operational_climate", "mean"),
        negative_per_1k=("negative_per_1k", "mean"),
    )
    yearly["event_context"] = yearly["year"].map(EVENT_CONTEXT)
    yearly.to_csv(OUT_DIR / "year_level_means.csv", index=False)
    write_figures(df)
    print(json.dumps(write_stats(df), indent=2))


if __name__ == "__main__":
    main()
