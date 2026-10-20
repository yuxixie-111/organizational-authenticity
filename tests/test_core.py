"""Unit tests for extraction, the codebook, and the authenticity formula.

These tests lock the exclude rules (safe harbor, shareholders' equity,
inventory, work environment) and the index arithmetic. They do not
touch the network.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.taxonomy import behavioral_flags, theme_counts
from src.textutil import cosine_vectors, extract_about_text
from src.measure import authenticity_score


ABOUT_HTML = b"""
<html><body>
<nav class="global-nav"><a>Careers</a><a>Investors</a></nav>
<header id="masthead">Search Sign in</header>
<main>
<h1>About Us</h1>
<p>We build products our customers love. Integrity guides our work.</p>
<ul><li>Innovation</li><li>Inclusion</li></ul>
</main>
<footer>Copyright 2020 Privacy Policy All rights reserved</footer>
</body></html>
"""


class ExtractTests(unittest.TestCase):
    def test_nav_and_footer_removed_values_kept(self):
        text = extract_about_text(ABOUT_HTML)
        self.assertIn("Integrity", text)
        self.assertIn("Innovation", text)
        self.assertIn("Inclusion", text)
        self.assertNotIn("Careers", text)
        self.assertNotIn("Privacy Policy", text)
        self.assertNotIn("Sign in", text)


class CodebookTests(unittest.TestCase):
    def test_exclusions(self):
        text = (
            "This safe harbor statement discusses shareholders' equity, "
            "inventory management, and a respectful work environment."
        )
        counts = theme_counts(text)
        self.assertGreater(counts["shareholder"], 0)
        self.assertEqual(counts["safety_quality"], 0)
        self.assertEqual(counts["innovation"], 0)
        self.assertEqual(counts["environment"], 0)
        self.assertEqual(counts["inclusion"], 0)

    def test_inclusions(self):
        text = (
            "Diversity, equity, and inclusion is a stated value. "
            "We published a pay equity study and a net-zero climate plan."
        )
        counts = theme_counts(text)
        self.assertGreater(counts["inclusion"], 0)
        self.assertGreater(counts["environment"], 0)
        flags = behavioral_flags(text)
        self.assertGreater(flags["flag_pay_equity"], 0)
        self.assertGreater(flags["flag_emissions_target"], 0)


class IndexTests(unittest.TestCase):
    def test_perfect_alignment_without_operational_test(self):
        # Innovation is not an operationalizable theme, so follow-through
        # is undefined and the index falls back to cosine.
        stated = {"innovation": 1.0}
        lived = {"innovation": 1.0}
        score = authenticity_score(stated, lived, flags={})
        self.assertEqual(score["cosine_alignment"], 1.0)
        self.assertIsNone(score["follow_through"])
        self.assertEqual(score["oai"], 100.0)

    def test_claim_without_practice_scores_lower_than_full_alignment(self):
        stated = {"inclusion": 0.5, "environment": 0.5}
        lived = {"inclusion": 0.5, "environment": 0.5}
        flags = {"flag_dei_metrics": 1}
        score = authenticity_score(stated, lived, flags)
        self.assertEqual(score["follow_through"], 0.5)
        self.assertAlmostEqual(score["cosine_alignment"], 1.0)
        self.assertAlmostEqual(score["oai"], 75.0)

    def test_orthogonal_mixes_have_zero_cosine(self):
        left = [1.0, 0.0]
        right = [0.0, 1.0]
        self.assertEqual(cosine_vectors(left, right), 0.0)


if __name__ == "__main__":
    unittest.main()
