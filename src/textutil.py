"""Visible-text extraction, similarity, and small linguistic features.

About pages and proxy statements need different extractors. An About page
is a short marketing document wrapped in navigation, so the extractor
drops nav, footer, and UI boilerplate and keeps headings and lists
(values pages are often lists of single principles). A proxy statement
is the document: tables hold the numbers, so they are kept, while
scripts, styles, and hidden XBRL blocks are not.
"""

from __future__ import annotations

import hashlib
import re
from collections import Counter

from bs4 import BeautifulSoup, Comment, XMLParsedAsHTMLWarning
import warnings

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

from src.taxonomy import (
    BOILERPLATE_PATTERNS,
    COMMITMENT_PATTERNS,
    NEGATIVE_WORDS,
    POSITIVE_WORDS,
    UNCERTAINTY_PATTERNS,
    count_patterns,
)

# UI strings that survive tag removal because they sit in generic divs.
# Matched against a full line after lowercasing, not against the middle
# of a real sentence.
BOILERPLATE_LINES = {
    "cart",
    "skip to content",
    "skip to main content",
    "skip to main",
    "search",
    "sign in",
    "log in",
    "login",
    "subscribe",
    "follow us",
    "share",
    "cookie settings",
    "accept all",
    "accept cookies",
    "reject all",
    "privacy policy",
    "terms of use",
    "terms of service",
    "all rights reserved",
    "site map",
    "sitemap",
    "contact us",
    "back to top",
    "select your location",
    "choose your location",
    "united states",
}

NAV_ATTR = re.compile(
    r"nav|menu|footer|cookie|breadcrumb|masthead|utility-nav|global-header|"
    r"global-footer|consent|pagination|share-bar|social-link|legal-links|"
    r"skip-link|wm-ipp|donato",
    re.IGNORECASE,
)

STOPWORDS = {
    "the", "and", "for", "that", "this", "with", "from", "are", "was", "were",
    "been", "being", "have", "has", "had", "not", "but", "its", "our", "ours",
    "you", "your", "they", "them", "their", "she", "her", "his", "him", "who",
    "what", "when", "where", "which", "will", "can", "may", "into", "over",
    "than", "then", "also", "more", "most", "other", "such", "about", "after",
    "before", "between", "through", "across", "while", "because", "there",
    "here", "all", "any", "each", "few", "own", "same", "too", "very", "just",
    "how", "why", "our", "we", "us",
}

WORD_RE = re.compile(r"[A-Za-z0-9']+")
CONTENT_RE = re.compile(r"[a-z][a-z']+")
SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")
WE_OUR_RE = re.compile(r"\b(?:we|our|ours|ourselves)\b", re.IGNORECASE)
NUMERIC_RE = re.compile(r"\d")


def _soup(content: bytes | str) -> BeautifulSoup:
    try:
        return BeautifulSoup(content, "lxml")
    except Exception:
        return BeautifulSoup(content, "html.parser")


def _drop_chrome(soup: BeautifulSoup, drop_layout: bool) -> None:
    for comment in soup.find_all(string=lambda t: isinstance(t, Comment)):
        comment.extract()
    for tag in soup.find_all(["script", "style", "noscript", "svg", "canvas", "iframe", "form"]):
        tag.decompose()
    # Inline XBRL and collapsed blocks add thousands of hidden tokens.
    hidden = []
    for tag in soup.find_all(True):
        if tag.attrs is None:
            continue
        style = " ".join(tag.get("style", []) if isinstance(tag.get("style"), list) else [tag.get("style") or ""])
        if "display:none" in style.lower().replace(" ", ""):
            hidden.append(tag)
            continue
        if tag.name and tag.name.lower().startswith("ix"):
            # Keep visible inline facts; drop the header/references block.
            if tag.name.lower() in {"ix:header", "ix:hidden", "ix:references"}:
                hidden.append(tag)
    for tag in hidden:
        tag.decompose()
    if not drop_layout:
        return
    remove = []
    for tag in soup.find_all(["nav", "footer", "header"]):
        remove.append(tag)
    for tag in soup.find_all(True):
        if tag.name in {"main", "article", "body"}:
            continue
        attr_text = " ".join([
            " ".join(tag.get("class") or []),
            str(tag.get("id") or ""),
            str(tag.get("role") or ""),
            str(tag.get("aria-label") or ""),
        ])
        if NAV_ATTR.search(attr_text):
            remove.append(tag)
    for tag in remove:
        if tag.parent is not None:
            tag.decompose()


def _lines_from_elements(soup: BeautifulSoup) -> list[str]:
    lines: list[str] = []
    for el in soup.find_all(["h1", "h2", "h3", "h4", "p", "li", "blockquote"]):
        text = " ".join(el.get_text(" ", strip=True).split())
        if text:
            lines.append(text)
    return lines


def _clean_lines(lines: list[str]) -> list[str]:
    kept: list[str] = []
    seen_prev = None
    for line in lines:
        key = line.strip().lower()
        if not key or key in BOILERPLATE_LINES:
            continue
        if key.startswith("copyright") or key.startswith("©"):
            continue
        if key == seen_prev:
            continue
        seen_prev = key
        kept.append(line.strip())
    return kept


def extract_about_text(content: bytes | str) -> str:
    """Return visible About-page prose with navigation and footer removed.

    Headings and list items are kept on purpose. Many values pages are a
    stack of short principles ("Integrity", "Respect for people") rather
    than paragraphs. A minimum length check elsewhere decides whether the
    result is usable.
    """
    soup = _soup(content)
    _drop_chrome(soup, drop_layout=True)
    lines = _clean_lines(_lines_from_elements(soup))
    text = "\n".join(lines).strip()
    # Pages that put the mission in generic divs still deserve a fallback,
    # but only when the structured pass found almost nothing.
    if len(text) < 80:
        fallback = soup.get_text("\n", strip=True)
        fallback_lines = _clean_lines([" ".join(line.split()) for line in fallback.splitlines()])
        text = "\n".join(fallback_lines).strip()
    return text


def extract_proxy_text(content: bytes | str) -> str:
    """Return proxy text, including table cells, without scripts or hidden XBRL."""
    soup = _soup(content)
    _drop_chrome(soup, drop_layout=False)
    raw = soup.get_text("\n", strip=True)
    lines = []
    prev = None
    for line in raw.splitlines():
        cleaned = " ".join(line.split())
        if not cleaned or cleaned == prev:
            continue
        prev = cleaned
        lines.append(cleaned)
    return "\n".join(lines).strip()


def word_count(text: str) -> int:
    if not text:
        return 0
    return len(WORD_RE.findall(text))


def sha1_text(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8", errors="replace")).hexdigest()


def content_tokens(text: str) -> list[str]:
    """Tokens used for similarity. Pronouns and stopwords are excluded.

    Pronoun style is measured separately. Leaving "we" and "our" in the
    similarity vector would treat a tone shift as a content rewrite.
    """
    if not text:
        return []
    return [
        token
        for token in CONTENT_RE.findall(text.lower())
        if len(token) > 2 and token not in STOPWORDS
    ]


def cosine_similarity(text_a: str | None, text_b: str | None) -> float | None:
    if not text_a or not text_b:
        return None
    counts_a = Counter(content_tokens(text_a))
    counts_b = Counter(content_tokens(text_b))
    if not counts_a or not counts_b:
        return None
    dot = norm_a = norm_b = 0.0
    for token in set(counts_a) | set(counts_b):
        value_a = float(counts_a[token])
        value_b = float(counts_b[token])
        dot += value_a * value_b
        norm_a += value_a * value_a
        norm_b += value_b * value_b
    if norm_a == 0 or norm_b == 0:
        return None
    return dot / ((norm_a ** 0.5) * (norm_b ** 0.5))


def per_thousand(count: int, words: int) -> float | None:
    if words <= 0:
        return None
    return 1000.0 * count / words


def linguistic_features(text: str) -> dict[str, float | None]:
    words = word_count(text)
    sentences = [part for part in SENTENCE_SPLIT.split(text or "") if part.strip()]
    sentence_lengths = [word_count(part) for part in sentences if word_count(part) > 0]
    return {
        "word_count": words,
        "we_our_per_1k": per_thousand(len(WE_OUR_RE.findall(text or "")), words),
        "commitment_per_1k": per_thousand(count_patterns(text, COMMITMENT_PATTERNS), words),
        "boilerplate_per_1k": per_thousand(count_patterns(text, BOILERPLATE_PATTERNS), words),
        "positive_per_1k": per_thousand(count_patterns(text, POSITIVE_WORDS), words),
        "negative_per_1k": per_thousand(count_patterns(text, NEGATIVE_WORDS), words),
        "uncertainty_per_1k": per_thousand(count_patterns(text, UNCERTAINTY_PATTERNS), words),
        "numeric_token_share": (
            None if words == 0 else sum(1 for token in WORD_RE.findall(text) if NUMERIC_RE.search(token)) / words
        ),
        "avg_sentence_length": (
            None if not sentence_lengths else sum(sentence_lengths) / len(sentence_lengths)
        ),
    }


def tone_net(positive: float | None, negative: float | None) -> float | None:
    if positive is None or negative is None:
        return None
    total = positive + negative
    if total <= 0:
        return None
    return (positive - negative) / total


def shares_from_counts(counts: dict[str, int]) -> dict[str, float] | None:
    """Turn raw hits into a composition. Zero total means 'no codable theme'."""
    total = sum(counts.values())
    if total <= 0:
        return None
    return {key: value / total for key, value in counts.items()}


def cosine_vectors(left: list[float], right: list[float]) -> float | None:
    if len(left) != len(right) or not left:
        return None
    dot = norm_l = norm_r = 0.0
    for value_l, value_r in zip(left, right):
        dot += value_l * value_r
        norm_l += value_l * value_l
        norm_r += value_r * value_r
    if norm_l == 0 or norm_r == 0:
        return None
    return dot / ((norm_l ** 0.5) * (norm_r ** 0.5))


def notable_shift(current: dict, prior: dict, label: str) -> str | None:
    """Flag a linguistic move that is both relatively and absolutely large.

    A 35% change on a tiny base (0.2 to 0.27 per 1,000 words) is noise.
    The absolute floor is in the same units as the feature.
    """
    floors = {
        "we_our_per_1k": 5.0,
        "commitment_per_1k": 1.5,
        "boilerplate_per_1k": 1.5,
        "positive_per_1k": 2.0,
        "negative_per_1k": 1.0,
        "numeric_token_share": 0.01,
    }
    if label not in floors:
        return None
    new = current.get(label)
    old = prior.get(label)
    if new is None or old is None:
        return None
    delta = new - old
    base = abs(old)
    relative = abs(delta) / base if base > 1e-9 else (1.0 if abs(delta) > 0 else 0.0)
    if abs(delta) < floors[label] or relative < 0.35:
        return None
    direction = "rose" if delta > 0 else "fell"
    if label == "numeric_token_share":
        return f"share of numeric tokens {direction} from {old:.3f} to {new:.3f}"
    pretty = {
        "we_our_per_1k": "we/our density",
        "commitment_per_1k": "commitment wording",
        "boilerplate_per_1k": "generic excellence wording",
        "positive_per_1k": "positive tone",
        "negative_per_1k": "negative tone",
    }[label]
    return f"{pretty} {direction} from {old:.1f} to {new:.1f} per 1,000 words"


def distinctive_sentence(text: str, prior_text: str | None, score_fn) -> str | None:
    """A new sentence that carries the most codebook hits. Used in notes."""
    if not text:
        return None
    prior = (prior_text or "").lower()
    best = None
    best_score = 0
    for sentence in SENTENCE_SPLIT.split(text):
        sentence = " ".join(sentence.split())
        if len(sentence) < 40 or len(sentence) > 280:
            continue
        if prior and sentence.lower() in prior:
            continue
        score = score_fn(sentence)
        if score > best_score:
            best = sentence
            best_score = score
    if best_score < 1:
        return None
    return best
