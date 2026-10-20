"""Code About-page snapshots with the frozen values rubric.

Change detection compares a year with the immediately previous calendar
year, not with the last observed year. If the previous year is missing,
changed_from_prior is left blank. Copying the older text forward would
invent a "no change" that the archive does not support.

Theme presence is one or more codebook hits. Shares are the composition
of those hits. Analyst notes state the theme list, the similarity, any
theme that entered or left, and any linguistic move that clears both a
relative bar (35%) and an absolute floor. A distinctive new sentence is
quoted when one exists.
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
from src.taxonomy import THEME_LABELS, THEME_ORDER, theme_counts
from src.textutil import (
    cosine_similarity,
    distinctive_sentence,
    linguistic_features,
    notable_shift,
    sha1_text,
    shares_from_counts,
    word_count,
)

PART1 = ROOT / "part1"
META_DIR = PART1 / "data" / "meta"
TEXT_DIR = PART1 / "data" / "text"
OUT_DIR = PART1 / "output"
DATA_DIR = PART1 / "data"

SHIFT_LABELS = [
    "we_our_per_1k",
    "commitment_per_1k",
    "boilerplate_per_1k",
    "numeric_token_share",
]


def load_text(ticker: str, year: int) -> str:
    path = TEXT_DIR / f"{ticker}_{year}.txt"
    if not path.exists():
        return ""
    kept = []
    for line in path.read_text().splitlines():
        lowered = line.strip().lower()
        if lowered in {"cart", "menu", "no thanks", "newsroom", "investors", "sustainability", "blog", "careers", "visual computing"}:
            continue
        if "try microsoft edge" in lowered:
            continue
        kept.append(line)
    return "\n".join(kept).strip()


def theme_list(shares: dict[str, float] | None) -> list[str]:
    if not shares:
        return []
    ordered = sorted(THEME_ORDER, key=lambda theme: shares.get(theme, 0.0), reverse=True)
    return [theme for theme in ordered if shares.get(theme, 0.0) > 0]


def narrate(row: dict, prior_text: str, prior_features: dict | None, prior_themes: list[str]) -> str:
    if row["gap_reason"]:
        return (
            f"No stated-values text for {row['year']}. Reason: {row['gap_reason']}. "
            "Text was not copied from an adjacent year."
        )
    themes = [item.split(":")[0] for item in row["theme_categories"].split("|") if item]
    sentences = []
    if themes:
        pretty = ", ".join(THEME_LABELS[theme] for theme in themes)
        sentences.append(f"Stated themes present: {pretty}.")
    else:
        sentences.append("The snapshot has no codebook theme. It may be a short corporate description rather than a values statement.")
    if prior_features is None:
        sentences.append(
            f"Change from {row['year'] - 1} was not coded because that year's snapshot is missing."
        )
    elif row["changed_from_prior"] == "true":
        sentences.append(
            f"Material wording change from {row['year'] - 1} "
            f"(content-word similarity {row['similarity_to_prior']:.2f}; "
            f"threshold {CHANGE_THRESHOLD})."
        )
        added = [theme for theme in themes if theme not in prior_themes]
        dropped = [theme for theme in prior_themes if theme not in themes]
        if added:
            sentences.append("Themes that entered: " + ", ".join(THEME_LABELS[theme] for theme in added) + ".")
        if dropped:
            sentences.append("Themes that dropped out: " + ", ".join(THEME_LABELS[theme] for theme in dropped) + ".")
        if not added and not dropped:
            sentences.append("The theme list is the same; the wording inside it changed.")
    else:
        sentences.append(
            f"No material wording change from {row['year'] - 1} "
            f"(similarity {row['similarity_to_prior']:.2f})."
        )
    if prior_features is not None:
        shifts = []
        current = {label: row.get(label) for label in SHIFT_LABELS}
        for label in SHIFT_LABELS:
            note = notable_shift(current, prior_features, label)
            if note:
                shifts.append(note)
        if shifts:
            sentences.append("Linguistic shifts: " + "; ".join(shifts) + ".")
        else:
            sentences.append("No notable linguistic shift beyond ordinary editing.")
    quote = distinctive_sentence(
        row["page_text_clean"],
        prior_text,
        lambda sentence: sum(theme_counts(sentence).values()),
    )
    if quote:
        sentences.append(f'Distinctive sentence: "{quote}"')
    note = " ".join(sentences)
    return note[:1200]


def build_rows() -> pd.DataFrame:
    records = []
    texts: dict[tuple[str, int], str] = {}
    features: dict[tuple[str, int], dict] = {}
    themes: dict[tuple[str, int], list[str]] = {}
    for company in COMPANIES:
        for year in YEARS:
            meta_path = META_DIR / f"{company.ticker}_{year}.json"
            if meta_path.exists():
                meta = json.loads(meta_path.read_text())
            else:
                meta = {"status": "gap", "gap_reason": "not_attempted"}
            text = load_text(company.ticker, year) if meta.get("status") == "ok" else ""
            counts = theme_counts(text) if text else {theme: 0 for theme in THEME_ORDER}
            share = shares_from_counts(counts) if text else None
            ling = linguistic_features(text) if text else {}
            present = theme_list(share)
            texts[(company.ticker, year)] = text
            features[(company.ticker, year)] = ling
            themes[(company.ticker, year)] = present
            row = {
                "ticker": company.ticker,
                "company_name": company.name,
                "sector": company.sector,
                "year": year,
                "page_text_clean": text,
                "snapshot_timestamp": meta.get("snapshot_timestamp", ""),
                "source_url": meta.get("original_url", ""),
                "wayback_url": meta.get("wayback_url", ""),
                "redirect_hops": meta.get("redirect_hops", 0),
                "page_score": meta.get("page_score", ""),
                "gap_reason": "" if text else (meta.get("gap_reason") or "not_attempted"),
                "text_sha1": sha1_text(text) if text else "",
                "word_count": word_count(text),
                "theme_categories": "|".join(present),
                "event_context": EVENT_CONTEXT[year],
                "rubric_version": RUBRIC_VERSION,
            }
            for theme in THEME_ORDER:
                row[f"theme_count_{theme}"] = counts[theme]
                row[f"theme_share_{theme}"] = None if share is None else round(share[theme], 4)
            for key, value in ling.items():
                if key == "word_count":
                    continue
                row[key] = None if value is None else round(float(value), 4)
            records.append(row)

    for row in records:
        prior_key = (row["ticker"], row["year"] - 1)
        prior_text = texts.get(prior_key, "")
        prior_features = features.get(prior_key) if prior_text else None
        prior_theme_list = themes.get(prior_key, []) if prior_text else []
        if not row["page_text_clean"] or not prior_text:
            row["similarity_to_prior"] = None
            row["changed_from_prior"] = ""
            row["theme_mix_shift"] = None
            row["themes_added"] = ""
            row["themes_dropped"] = ""
        else:
            similarity = cosine_similarity(row["page_text_clean"], prior_text)
            row["similarity_to_prior"] = None if similarity is None else round(similarity, 4)
            row["changed_from_prior"] = "true" if similarity is not None and similarity < CHANGE_THRESHOLD else "false"
            current_shares = [row[f"theme_share_{theme}"] or 0.0 for theme in THEME_ORDER]
            # Prior shares live on the prior record; recompute from stored texts' themes via the row list later.
            row["themes_added"] = "|".join(
                theme for theme in row["theme_categories"].split("|") if theme and theme not in prior_theme_list
            )
            row["themes_dropped"] = "|".join(
                theme for theme in prior_theme_list if theme not in row["theme_categories"].split("|")
            )
        row["analyst_notes"] = narrate(row, prior_text, prior_features, prior_theme_list)

    # Total-variation distance between this year and the prior year theme mix.
    lookup = {(row["ticker"], row["year"]): row for row in records}
    for row in records:
        prior = lookup.get((row["ticker"], row["year"] - 1))
        if not row["page_text_clean"] or prior is None or not prior["page_text_clean"]:
            row["theme_mix_shift"] = None
            continue
        distance = 0.0
        for theme in THEME_ORDER:
            distance += abs((row[f"theme_share_{theme}"] or 0.0) - (prior[f"theme_share_{theme}"] or 0.0))
        row["theme_mix_shift"] = round(distance / 2.0, 4)
    return pd.DataFrame.from_records(records)


def write_figures(df: pd.DataFrame) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    coverage = (
        df.assign(has_text=df["page_text_clean"].str.len().gt(0))
        .groupby(["sector", "year"], as_index=False)["has_text"]
        .mean()
    )
    fig, ax = new_figure()
    for sector, color in SECTOR_COLORS.items():
        part = coverage[coverage["sector"] == sector]
        ax.plot(part["year"], part["has_text"], marker="o", label=sector, color=color)
    ax.set_ylim(-0.05, 1.05)
    ax.set_xticks(YEARS)
    finish(ax, "Share of firms with a usable About-page snapshot", "Year", "Share of firms", OUT_DIR / "coverage_by_sector.png")

    # Four themes that the later parts use in the authenticity argument.
    focus = ["inclusion", "environment", "integrity", "innovation"]
    present = df[df["page_text_clean"].str.len().gt(0)].copy()
    fig, ax = new_figure()
    for theme, color in zip(focus, ["#CC79A7", "#009E73", "#0072B2", "#E69F00"]):
        rates = []
        for year in YEARS:
            part = present[present["year"] == year]
            if part.empty:
                rates.append(float("nan"))
            else:
                rates.append((part[f"theme_share_{theme}"].fillna(0) > 0).mean())
        ax.plot(YEARS, rates, marker="o", label=THEME_LABELS[theme], color=color)
    ax.set_ylim(-0.05, 1.05)
    ax.set_xticks(YEARS)
    finish(ax, "Share of collected About pages that mention each theme", "Year", "Share of pages", OUT_DIR / "theme_prevalence.png")


def write_stats(df: pd.DataFrame) -> dict:
    has_text = df["page_text_clean"].str.len().gt(0)
    comparable = df[df["changed_from_prior"].isin(["true", "false"])]
    stats = {
        "firm_years": int(len(df)),
        "with_text": int(has_text.sum()),
        "coverage_rate": round(float(has_text.mean()), 4),
        "gap_reasons": df.loc[~has_text, "gap_reason"].value_counts().to_dict(),
        "changed_share_of_comparable": (
            None if comparable.empty else round(float((comparable["changed_from_prior"] == "true").mean()), 4)
        ),
        "median_similarity": (
            None if comparable.empty else round(float(comparable["similarity_to_prior"].median()), 4)
        ),
        "median_words": round(float(df.loc[has_text, "word_count"].median()), 1) if has_text.any() else None,
        "by_sector": (
            df.assign(has_text=has_text)
            .groupby("sector")["has_text"]
            .mean()
            .round(4)
            .to_dict()
        ),
    }
    (OUT_DIR / "stats.json").write_text(json.dumps(stats, indent=2))
    return stats


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    df = build_rows()
    # Column order keeps the required fields first.
    front = [
        "ticker", "company_name", "sector", "year", "page_text_clean",
        "changed_from_prior", "theme_categories", "analyst_notes",
    ]
    rest = [column for column in df.columns if column not in front]
    df = df[front + rest]
    df.to_csv(DATA_DIR / "company_year.csv", index=False)
    gaps = df[df["page_text_clean"].str.len().eq(0)][
        ["ticker", "company_name", "sector", "year", "gap_reason", "source_url"]
    ]
    gaps.to_csv(DATA_DIR / "coverage_gaps.csv", index=False)
    write_figures(df)
    stats = write_stats(df)
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
