"""Collect one About-page snapshot per firm-year from the Wayback CDX API.

Page choice
-----------
Seeds are curated About / mission / values URLs, including historical
paths, and are listed in src/companies.py. A capture is eligible when
its normalized URL matches a seed. Redirect targets are eligible only
when they stay on the firm's domain and still look like an About page
(url score >= 1). Careers, news, investor, privacy, and diversity-only
paths are not accepted as substitutes. Among eligible captures in a
calendar year, the collector prefers the higher page score and then the
capture closest to July 1, so firms are compared at a similar point in
the year rather than on whatever date the crawler happened to visit.

Missing data
------------
If a year has no eligible capture, or every capture downloads as an empty
shell, the firm-year is stored as a gap. Text is never copied from the
previous or following year. Gaps are retried on a later run; successful
years are not downloaded again.

Redirects
---------
CDX is filtered to HTTP 200. A 200 page that is only a meta refresh is
followed one hop, and only to a URL that still qualifies as an About page
on the same company domain. If the hop leaves that family, the capture
is rejected and the next candidate is tried.
"""

from __future__ import annotations

import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.companies import COMPANIES, Company
from src.constants import MIN_ABOUT_CHARS, YEARS
from src.httputil import PoliteClient
from src.textutil import extract_about_text

PART1 = ROOT / "part1"
META_DIR = PART1 / "data" / "meta"
TEXT_DIR = PART1 / "data" / "text"
CACHE = ROOT / "data" / "cache" / "wayback"
CDX = "https://web.archive.org/cdx/search/cdx"

PENALTY = re.compile(
    r"career|jobs|news|blog|investor|press|/product|support|privacy|cookie|"
    r"legal|foundation|sustainability|diversity|inclusion|contact|login|search",
    re.IGNORECASE,
)
VALUES_PATH = re.compile(
    r"value|mission|purpose|who-we-are|our-story|guiding-principle|philosophy|"
    r"our-company|company-overview",
    re.IGNORECASE,
)


def normalize(url: str) -> tuple[str, str]:
    parsed = urlparse(url.strip())
    host = parsed.netloc.lower().split("@")[-1].split(":")[0]
    if host.startswith("www."):
        host = host[4:]
    path = parsed.path or "/"
    path = re.sub(r"/index\.html?$", "", path, flags=re.IGNORECASE)
    if path != "/":
        path = path.rstrip("/")
    return host, path.lower()


def host_allowed(url: str, company: Company) -> bool:
    host, _ = normalize(url)
    return any(host == domain or host.endswith("." + domain) for domain in company.domains)


def is_seed(url: str, company: Company) -> bool:
    host, path = normalize(url)
    for seed in company.seeds:
        seed_host, seed_path = normalize(seed)
        if host == seed_host and path == seed_path:
            return True
    return False


def url_score(url: str, company: Company) -> int:
    """Higher means 'more clearly a values page'. Used only to rank."""
    host, path = normalize(url)
    score = 0
    if host.startswith("about.") or "aboutamazon" in host or "aboutschwab" in host:
        score += 3
    if "about" in host or "about" in path:
        score += 3
    if VALUES_PATH.search(path):
        score += 5
    if PENALTY.search(path):
        score -= 8
    if host.startswith("ir.") or host.startswith("investor."):
        score -= 8
    if path == "/":
        score += 2 if (company.allow_homepage or host.startswith("about.")) else -2
    return score


def cdx_rows(client: PoliteClient, seed: str) -> list[dict]:
    target = re.sub(r"^https?://", "", seed)
    payload = client.get_json(CDX, params={
        "url": target,
        "from": "20160101",
        "to": "20241231",
        "output": "json",
        "fl": "timestamp,original,statuscode,mimetype,length",
        "filter": "statuscode:200",
        # One capture per URL per month. July can then be chosen in Python
        # without downloading every daily crawl.
        "collapse": "timestamp:6",
        "limit": "800",
    })
    if not isinstance(payload, list) or len(payload) < 2:
        return []
    header = payload[0]
    rows = []
    for raw in payload[1:]:
        row = dict(zip(header, raw))
        if "html" not in (row.get("mimetype") or ""):
            continue
        rows.append(row)
    if len(payload) - 1 >= 5000:
        print(f"  warning: CDX hit the 5000-row cap for {seed}", flush=True)
    return rows


def closest_key(row: dict, year: int, company: Company) -> tuple:
    stamp = datetime.strptime(row["timestamp"][:14], "%Y%m%d%H%M%S")
    distance = abs((stamp - datetime(year, 7, 1)).days)
    try:
        length = int(row.get("length") or 0)
    except ValueError:
        length = 0
    # Negative score sorts first after the sign flip. July proximity breaks ties.
    return (-url_score(row["original"], company), distance, -min(length, 2_000_000))


def meta_refresh(content: bytes, base_url: str) -> str | None:
    match = re.search(
        br"http-equiv=['\"]refresh['\"][^>]*content=['\"][^'\"]*url=([^'\">]+)",
        content,
        re.IGNORECASE,
    )
    if not match:
        match = re.search(
            br"content=['\"][^'\"]*url=([^'\">]+)['\"][^>]*http-equiv=['\"]refresh['\"]",
            content,
            re.IGNORECASE,
        )
    if not match:
        return None
    target = match.group(1).decode("utf-8", errors="ignore").strip()
    if target.startswith("/web/"):
        # A Wayback replay URL slipped through. Keep the original target only.
        parts = target.split("http", 1)
        if len(parts) == 2:
            target = "http" + parts[1]
    return urljoin(base_url, target)


def archive_fetch_url(timestamp: str, original: str) -> str:
    return f"https://web.archive.org/web/{timestamp}id_/{original}"


def year_done(company: Company, year: int) -> bool:
    meta_path = META_DIR / f"{company.ticker}_{year}.json"
    text_path = TEXT_DIR / f"{company.ticker}_{year}.txt"
    if not meta_path.exists():
        return False
    info = json.loads(meta_path.read_text())
    return info.get("status") == "ok" and text_path.exists() and text_path.stat().st_size > 0


def write_meta(company: Company, year: int, payload: dict) -> None:
    path = META_DIR / f"{company.ticker}_{year}.json"
    payload = {
        "ticker": company.ticker,
        "company_name": company.name,
        "sector": company.sector,
        "year": year,
        **payload,
    }
    path.write_text(json.dumps(payload, indent=2))


def collect_company(client: PoliteClient, company: Company) -> None:
    needed = [year for year in YEARS if not year_done(company, year)]
    if not needed:
        print(f"{company.ticker}: already complete", flush=True)
        return
    print(f"{company.ticker}: need {needed}", flush=True)
    captures: list[dict] = []
    seen_seeds = []
    for seed in company.seeds:
        seen_seeds.append(seed)
        try:
            rows = cdx_rows(client, seed)
        except Exception as exc:
            print(f"  CDX failed for {seed}: {exc}", flush=True)
            continue
        for row in rows:
            if host_allowed(row["original"], company) and is_seed(row["original"], company):
                captures.append(row)
        covered = {int(row["timestamp"][:4]) for row in captures}
        if all(year in covered for year in needed):
            break

    for year in needed:
        pool = [row for row in captures if row["timestamp"].startswith(str(year))]
        pool.sort(key=lambda row: closest_key(row, year, company))
        if not pool:
            write_meta(company, year, {
                "status": "gap",
                "gap_reason": "no_capture",
                "seeds_queried": seen_seeds,
                "candidates_considered": 0,
            })
            print(f"  {year} gap no_capture", flush=True)
            continue
        last_error = "extraction_empty"
        accepted = False
        for row in pool[:4]:
            original = row["original"]
            fetch = archive_fetch_url(row["timestamp"], original)
            hops = 0
            try:
                content = client.get_bytes(fetch, use_cache=True)
            except Exception as exc:
                last_error = "download_failed"
                print(f"  {year} download failed: {exc}", flush=True)
                # A 429 has already been retried inside the client. Hitting
                # more URLs immediately extends the ban, so stop this year.
                if "429" in str(exc):
                    time.sleep(120)
                    break
                continue
            if b"Robot Challenge" in content or b"has not archived that URL" in content:
                last_error = "download_failed"
                # Do not cache a block page as if it were the firm page.
                cache_key_cleanup(fetch)
                continue
            text = extract_about_text(content)
            refresh = meta_refresh(content, original)
            if len(text) < MIN_ABOUT_CHARS and refresh and hops < 1 and host_allowed(refresh, company):
                if url_score(refresh, company) >= 1 or is_seed(refresh, company):
                    hops = 1
                    # The refresh target needs its own July capture, not the
                    # timestamp of the page that pointed at it.
                    try:
                        hopped = cdx_rows(client, refresh)
                    except Exception:
                        hopped = []
                    same_year = [item for item in hopped if item["timestamp"].startswith(str(year))]
                    same_year.sort(key=lambda item: closest_key(item, year, company))
                    if same_year:
                        original = same_year[0]["original"]
                        fetch = archive_fetch_url(same_year[0]["timestamp"], original)
                        row = same_year[0]
                        try:
                            content = client.get_bytes(fetch, use_cache=True)
                            text = extract_about_text(content)
                        except Exception:
                            text = ""
            if len(text) < MIN_ABOUT_CHARS:
                last_error = "extraction_empty"
                continue
            text_path = TEXT_DIR / f"{company.ticker}_{year}.txt"
            text_path.write_text(text)
            write_meta(company, year, {
                "status": "ok",
                "gap_reason": "",
                "snapshot_timestamp": row["timestamp"],
                "original_url": original,
                "wayback_url": fetch,
                "redirect_hops": hops,
                "page_score": url_score(original, company),
                "text_chars": len(text),
                "seeds_queried": seen_seeds,
                "candidates_considered": len(pool),
            })
            print(f"  {year} ok {row['timestamp']} chars={len(text)} {original}", flush=True)
            accepted = True
            break
        if not accepted:
            write_meta(company, year, {
                "status": "gap",
                "gap_reason": last_error,
                "seeds_queried": seen_seeds,
                "candidates_considered": len(pool),
            })
            print(f"  {year} gap {last_error} ({len(pool)} candidates)", flush=True)


def cache_key_cleanup(url: str) -> None:
    """Drop a cached block page so a later run can try the real capture."""
    import hashlib
    key = hashlib.sha1(
        json.dumps({"url": url, "params": {}}, sort_keys=True).encode("utf-8")
    ).hexdigest()
    path = CACHE / key
    if path.exists():
        path.unlink()


def main() -> None:
    META_DIR.mkdir(parents=True, exist_ok=True)
    TEXT_DIR.mkdir(parents=True, exist_ok=True)
    client = PoliteClient(CACHE, min_interval=20.0, timeout=45)
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
    print(f"DONE about pages ok={ok} gap={gap} of {len(COMPANIES) * len(YEARS)}", flush=True)
    print(f"gap reasons: {reasons}", flush=True)


if __name__ == "__main__":
    main()
