"""Organizational Authenticity Index, as a pure function.

Alignment has two parts, because "saying the same topics" and "attaching
a practice to the topics you emphasize" are different claims.

Rhetorical alignment is the cosine similarity of two compositions:
the share of codebook hits on the About page, and the share of
(word density + practice bonus) on that year's proxy. Both vectors are
non-negative and sum to one, so cosine runs from 0 to 1.

Follow-through looks only at themes the About page actually emphasizes
and that a proxy can operationalize. A firm is not punished for staying
silent. A firm is scored down when an emphasized theme has none of the
behavioral flags mapped to it.

If the About page has no emphasized operationalizable theme, follow-through
is undefined and the index equals rhetorical alignment. If either
composition is missing, the index is missing. Missing is not zero:
absence of a values page is a different fact from a values page that
contradicts the proxy.
"""

from __future__ import annotations

from src.constants import (
    LIVED_FLAG_BONUS,
    OAI_WEIGHT_COSINE,
    OAI_WEIGHT_FOLLOW,
    STATED_EMPHASIS_SHARE,
)
from src.taxonomy import OPERATIONAL_THEMES, THEME_FLAGS, THEME_ORDER
from src.textutil import cosine_vectors


def lived_composition(per_1k: dict[str, float | None], flags: dict[str, int]) -> dict[str, float] | None:
    """Proxy theme mix. A practice adds LIVED_FLAG_BONUS to that theme."""
    raw: dict[str, float] = {}
    for theme in THEME_ORDER:
        verbal = per_1k.get(theme) or 0.0
        practice = 0.0
        for flag in THEME_FLAGS.get(theme, []):
            if flags.get(flag, 0) > 0:
                practice = LIVED_FLAG_BONUS
                break
        raw[theme] = verbal + practice
    total = sum(raw.values())
    if total <= 0:
        return None
    return {theme: value / total for theme, value in raw.items()}


def follow_through(stated_shares: dict[str, float], flags: dict[str, int]) -> tuple[float | None, int, int]:
    """Return (rate, n_emphasized, n_operationalized).

    Rate is None when the page emphasizes no operationalizable theme.
    """
    emphasized = [
        theme
        for theme in OPERATIONAL_THEMES
        if stated_shares.get(theme, 0.0) >= STATED_EMPHASIS_SHARE
    ]
    if not emphasized:
        return None, 0, 0
    hit = 0
    for theme in emphasized:
        if any(flags.get(flag, 0) > 0 for flag in THEME_FLAGS.get(theme, [])):
            hit += 1
    return hit / len(emphasized), len(emphasized), hit


def cosine_excluding(
    stated_shares: dict[str, float] | None,
    lived_shares: dict[str, float] | None,
    exclude: tuple[str, ...] = ("shareholder",),
) -> float | None:
    """Cosine after dropping themes that the proxy genre forces.

    Shareholder language is required in a DEF 14A. Leaving it in the
    composition makes every proxy look shareholder-heavy and compresses
    the alignment score. This robustness check renormalizes both vectors
    over the remaining themes.
    """
    themes = [theme for theme in THEME_ORDER if theme not in exclude]

    def renorm(shares: dict[str, float] | None) -> list[float] | None:
        if not shares:
            return None
        total = sum(shares.get(theme, 0.0) for theme in themes)
        if total <= 0:
            return None
        return [shares.get(theme, 0.0) / total for theme in themes]

    left = renorm(stated_shares)
    right = renorm(lived_shares)
    if left is None or right is None:
        return None
    return cosine_vectors(left, right)


def authenticity_score(
    stated_shares: dict[str, float] | None,
    lived_shares: dict[str, float] | None,
    flags: dict[str, int],
) -> dict[str, float | int | None]:
    empty = {
        "cosine_alignment": None,
        "follow_through": None,
        "n_emphasized_themes": 0,
        "n_operationalized_themes": 0,
        "oai": None,
    }
    if not stated_shares or not lived_shares:
        return empty
    cosine = cosine_vectors(
        [stated_shares.get(theme, 0.0) for theme in THEME_ORDER],
        [lived_shares.get(theme, 0.0) for theme in THEME_ORDER],
    )
    rate, n_emph, n_ops = follow_through(stated_shares, flags)
    if cosine is None:
        return empty
    if rate is None:
        oai = 100.0 * cosine
    else:
        oai = 100.0 * (OAI_WEIGHT_COSINE * cosine + OAI_WEIGHT_FOLLOW * rate)
    return {
        "cosine_alignment": cosine,
        "follow_through": rate,
        "n_emphasized_themes": n_emph,
        "n_operationalized_themes": n_ops,
        "oai": oai,
    }
