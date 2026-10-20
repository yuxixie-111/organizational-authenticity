"""Collect DEF 14A proxy statements from SEC EDGAR for 2016-2024.

Why a proxy, and not a sustainability report
--------------------------------------------
The lived-values side has to be something the firm does even when it
would rather not write a values essay. Every US public firm files a
proxy. Sustainability reports are voluntary, so the firms that publish
them are already the firms willing to talk. A proxy is where the board
describes oversight, human capital, and the metrics that determine pay.
That is as close as a public document gets to revealed priorities.

Rules
-----
One DEF 14A per firm per calendar year, assigned by filing date. If a
year has several (a special meeting plus the annual meeting), keep the
HTML filing closest to April 30. If the primary CIK has a filing, it
wins over an alternate CIK from a reincorporation. PDF primaries are
replaced with the longest HTML file in the filing index when one exists.
Missing years stay missing. Nothing is borrowed from the next proxy.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.companies import COMPANIES, Company
from src.constants import YEARS
from src.httputil import PoliteClient
from src.textutil import extract_proxy_text, word_count

PART2 = ROOT / "part2"
META_DIR = PART2 / "data" / "meta"
TEXT_DIR = PART2 / "data" / "text"
CACHE = ROOT / "data" / "cache" / "edgar"
MIN_PROXY_WORDS = 400


def parse_block(block: dict, cik: int) -> list[dict]:
    forms = block.get("form") or []
    dates = block.get("filingDate") or []
    accessions = block.get("accessionNumber") or []
    documents = block.get("primaryDocument") or []
    rows = []
    for form, date, accession, document in zip(forms, dates, accessions, documents):
        rows.append({
            "cik": cik,
            "form": str(form).strip().upper(),
            "filing_date": date,
            "accession": accession,
            "primary": document,
        })
    return rows


def load_filings(client: PoliteClient, cik: int) -> list[dict]:
    payload = client.get_json(f"https://data.sec.gov/submissions/CIK{cik:010d}.json")
    rows = parse_block(payload["filings"]["recent"], cik)
    for extra in payload["filings"].get("files") or []:
        start = extra.get("filingFrom", "")
        end = extra.get("filingTo", "")
        # Skip historical files that end before the window.
        if end and end < "2016-01-01":
            continue
        if start and start > "2024-12-31":
            continue
        extra_payload = client.get_json("https://data.sec.gov/submissions/" + extra["name"])
        rows.extend(parse_block(extra_payload, cik))
    return rows


def season_distance(filing_date: str) -> int:
    year, month, day = (int(part) for part in filing_date.split("-"))
    return abs((datetime(year, month, day) - datetime(year, 4, 30)).days)


def choose_filings(company: Company, filings: list[dict]) -> dict[int, dict]:
    """Pick one proxy per calendar year.

    DEF 14A is the definitive proxy. A PRE 14A is used only when that
    year has no DEF 14A. McDonald's 2022 is the case: the preliminary
    proxy was filed and no definitive version appears in EDGAR.
    Additional materials (DEFA14A) are never used. They are often
    fight letters rather than the board's own statement.
    """
    by_year: dict[int, dict[str, list[dict]]] = {}
    for row in filings:
        if row["form"] not in {"DEF 14A", "PRE 14A"}:
            continue
        year = int(row["filing_date"][:4])
        if year not in YEARS:
            continue
        by_year.setdefault(year, {}).setdefault(row["form"], []).append(row)
    chosen = {}
    for year, forms in by_year.items():
        pool = forms.get("DEF 14A") or forms.get("PRE 14A") or []
        primary = [row for row in pool if row["cik"] == company.cik]
        pool = primary or pool

        def sort_key(row: dict) -> tuple:
            name = str(row["primary"]).lower()
            html = name.endswith((".htm", ".html"))
            notice = "notice" in name and "proxy" not in name
            proxyish = "proxy" in name or "def14a" in name or "def14" in name
            return (
                0 if html else 1,
                1 if notice else 0,
                0 if proxyish else 1,
                season_distance(row["filing_date"]),
            )

        chosen[year] = sorted(pool, key=sort_key)[0]
    return chosen


def archive_url(cik: int, accession: str, filename: str) -> str:
    folder = accession.replace("-", "")
    return f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{folder}/{filename}"


def longest_html(client: PoliteClient, cik: int, accession: str) -> str | None:
    folder = accession.replace("-", "")
    payload = client.get_json(
        f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{folder}/index.json"
    )
    items = payload.get("directory", {}).get("item", [])
    if isinstance(items, dict):
        items = [items]
    html_items = [
        item for item in items
        if str(item.get("name", "")).lower().endswith((".htm", ".html"))
    ]
    if not html_items:
        return None
    html_items.sort(key=lambda item: int(item.get("size") or 0), reverse=True)
    return html_items[0]["name"]


def year_done(ticker: str, year: int) -> bool:
    meta_path = META_DIR / f"{ticker}_{year}.json"
    text_path = TEXT_DIR / f"{ticker}_{year}.txt"
    if not meta_path.exists() or not text_path.exists():
        return False
    info = json.loads(meta_path.read_text())
    return info.get("status") == "ok" and text_path.stat().st_size > 0


def write_meta(company: Company, year: int, payload: dict) -> None:
    path = META_DIR / f"{company.ticker}_{year}.json"
    path.write_text(json.dumps({
        "ticker": company.ticker,
        "company_name": company.name,
        "sector": company.sector,
        "year": year,
        **payload,
    }, indent=2))


def collect_company(client: PoliteClient, company: Company) -> None:
    needed = [year for year in YEARS if not year_done(company.ticker, year)]
    if not needed:
        print(f"{company.ticker}: proxies already complete", flush=True)
        return
    filings = load_filings(client, company.cik)
    for alternate in company.alternate_ciks:
        try:
            filings.extend(load_filings(client, alternate))
        except Exception as exc:
            print(f"  alternate CIK {alternate} failed: {exc}", flush=True)
    chosen = choose_filings(company, filings)
    for year in needed:
        filing = chosen.get(year)
        if filing is None:
            write_meta(company, year, {"status": "gap", "gap_reason": "no_def14a"})
            print(f"  {year} gap no_def14a", flush=True)
            continue
        filename = filing["primary"]
        if not str(filename).lower().endswith((".htm", ".html")):
            try:
                filename = longest_html(client, filing["cik"], filing["accession"]) or filename
            except Exception as exc:
                print(f"  {year} index lookup failed: {exc}", flush=True)
        url = archive_url(filing["cik"], filing["accession"], filename)
        try:
            content = client.get_bytes(url)
        except Exception as exc:
            write_meta(company, year, {
                "status": "gap",
                "gap_reason": "download_failed",
                "source_url": url,
                "accession": filing["accession"],
                "filing_date": filing["filing_date"],
            })
            print(f"  {year} download failed: {exc}", flush=True)
            continue
        if not str(filename).lower().endswith((".htm", ".html")):
            write_meta(company, year, {
                "status": "gap",
                "gap_reason": "pdf_only",
                "source_url": url,
                "accession": filing["accession"],
                "filing_date": filing["filing_date"],
                "cik_used": filing["cik"],
            })
            print(f"  {year} gap pdf_only", flush=True)
            continue
        text = extract_proxy_text(content)
        words = word_count(text)
        if words < MIN_PROXY_WORDS:
            write_meta(company, year, {
                "status": "gap",
                "gap_reason": "extraction_empty",
                "source_url": url,
                "accession": filing["accession"],
                "filing_date": filing["filing_date"],
                "word_count": words,
            })
            print(f"  {year} gap extraction_empty words={words}", flush=True)
            continue
        (TEXT_DIR / f"{company.ticker}_{year}.txt").write_text(text)
        write_meta(company, year, {
            "status": "ok",
            "gap_reason": "",
            "source_url": url,
            "accession": filing["accession"],
            "filing_date": filing["filing_date"],
            "form": filing["form"],
            "cik_used": filing["cik"],
            "primary_document": filename,
            "word_count": words,
        })
        print(f"  {year} ok {filing['filing_date']} words={words}", flush=True)


def main() -> None:
    META_DIR.mkdir(parents=True, exist_ok=True)
    TEXT_DIR.mkdir(parents=True, exist_ok=True)
    # EDGAR's published fair-access limit is 10 requests per second.
    # Stay well under it.
    client = PoliteClient(CACHE, min_interval=0.2)
    selected = set(sys.argv[1:])
    firms = [company for company in COMPANIES if not selected or company.ticker in selected]
    for company in firms:
        try:
            collect_company(client, company)
        except Exception as exc:
            print(f"{company.ticker}: stopped early ({exc})", flush=True)
    ok = gap = 0
    reasons: dict[str, int] = {}
    for company in COMPANIES:
        for year in YEARS:
            path = META_DIR / f"{company.ticker}_{year}.json"
            if not path.exists():
                gap += 1
                reasons["not_attempted"] = reasons.get("not_attempted", 0) + 1
                continue
            info = json.loads(path.read_text())
            if info.get("status") == "ok":
                ok += 1
            else:
                gap += 1
                reason = info.get("gap_reason") or "unknown"
                reasons[reason] = reasons.get(reason, 0) + 1
    print(f"DONE proxies ok={ok} gap={gap} of {len(COMPANIES) * len(YEARS)}", flush=True)
    print(f"gap reasons: {reasons}", flush=True)


if __name__ == "__main__":
    main()
