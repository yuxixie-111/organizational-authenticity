"""Value codebook used on both About pages and proxy statements.

The categories are an LLM analyst's rubric that has been frozen in code.
Freezing it is the point: every firm-year, and later the other 450 S&P
firms, is coded with the same include and exclude rules. A fresh chat
completion per page would not be comparable and would not scale.

Why these ten categories
------------------------
Corporate "values" language collapses into a shareholder pole and a
stakeholder pole, but those two poles hide the shifts this project is
built to see. Inclusion is separated from generic employee language so
that 2020 is not confused with ordinary talent talk. Environment is
separated from community so that climate language is not credited as
philanthropy. Safety and quality are included because they are real
operational values in Energy and Healthcare, not marketing filler.
Innovation, customers, integrity, and collaboration cover the remaining
language that About pages actually use.

What was deliberately left out
------------------------------
"Excellence", "world-class", "passionate", and similar words are near
universal and low information. They are counted as boilerplate, not as
a value. Bare "technology" and bare "AI" are product descriptions,
especially for this Technology subsample, so they are not innovation.
Bare "equity" is accounting language. Bare "environment" is usually
"work environment". Bare "trust" is a bank product. Bare "safe" collides
with "safe harbor" in securities filings. Bare "partners" collides with
Starbucks' name for its employees.
"""

from __future__ import annotations

import re

# Stable order used for vectors, column names, and cosine similarity.
THEME_ORDER = [
    "integrity",
    "innovation",
    "customer",
    "people",
    "inclusion",
    "community",
    "environment",
    "shareholder",
    "safety_quality",
    "collaboration",
]

THEME_LABELS = {
    "integrity": "Integrity and trust",
    "innovation": "Innovation",
    "customer": "Customers and users",
    "people": "Employees and talent",
    "inclusion": "Diversity, equity, and inclusion",
    "community": "Community and social impact",
    "environment": "Environment and climate",
    "shareholder": "Shareholders and financial returns",
    "safety_quality": "Safety and quality",
    "collaboration": "Collaboration and stakeholders",
}

# Themes for which a proxy can show a concrete practice, not only a word.
# Innovation, shareholder, and collaboration have no indicator that is both
# discretionary and reliable in a DEF 14A. Shareholder language is
# structurally required by the document. Clawbacks are nearly universal
# after Dodd-Frank, so they are not used as an integrity practice.
OPERATIONAL_THEMES = [
    "integrity",
    "customer",
    "people",
    "inclusion",
    "community",
    "environment",
    "safety_quality",
]

# Behavioral flags that add evidence for a theme. A theme may have several;
# any one of them is enough to call the theme operationalized.
THEME_FLAGS = {
    "integrity": ["flag_political_disclosure"],
    "customer": ["flag_customer_metric_in_pay"],
    "people": ["flag_human_capital_metrics"],
    "inclusion": ["flag_dei_metrics", "flag_pay_equity", "flag_inclusion_in_pay"],
    "community": ["flag_community_investment"],
    "environment": ["flag_emissions_target", "flag_climate_in_pay", "flag_board_esg_oversight"],
    "safety_quality": ["flag_safety_metrics", "flag_safety_in_pay"],
}


def _compile(patterns: list[str]) -> list[re.Pattern[str]]:
    return [re.compile(p, re.IGNORECASE) for p in patterns]


THEME_PATTERNS = {
    "integrity": _compile([
        r"\bintegrity\b",
        r"\bethics?\b",
        r"\bethical\b",
        r"\bunethical\b",
        r"\bhonesty\b",
        r"\bhonest\b",
        r"\btrustworthy\b",
        r"\btransparency\b",
        r"\baccountab(?:le|ility)\b",
        r"\bdo the right thing\b",
        r"\bpublic trust\b",
        r"\bcustomer trust\b",
    ]),
    "innovation": _compile([
        r"\binnov(?:ation|ate|ates|ating|ative|ativeness)\b",
        r"\binvent(?:ion|ing|ive|or)?\b",
        r"\bresearch and development\b",
        r"\br\s*&\s*d\b",
        r"\bbreakthroughs?\b",
        r"\bpioneering\b",
    ]),
    "customer": _compile([
        r"\bcustomers?\b",
        r"\bconsumers?\b",
        r"\bclients?\b",
        r"\bpatients?\b",
        r"\bour guests\b",
    ]),
    "people": _compile([
        r"\bemployees?\b",
        r"\bworkforce\b",
        r"\btalent\b",
        r"\bour people\b",
        r"\bteam members\b",
        r"\bassociates\b",
        r"\bcolleagues\b",
        r"\bhuman capital\b",
    ]),
    "inclusion": _compile([
        r"\bdiversity\b",
        r"\binclusion\b",
        r"\binclusive\b",
        r"\bbelonging\b",
        r"\bunderrepresented\b",
        r"\bequity and inclusion\b",
        r"\bdiversity,\s+equity\b",
        r"\bracial equity\b",
        r"\bgender equity\b",
        r"\bpay equity\b",
        r"\bequal opportunity\b",
    ]),
    "community": _compile([
        r"\bcommunit(?:y|ies)\b",
        r"\bphilanthrop(?:y|ic)\b",
        r"\bsocial impact\b",
        r"\bhuman rights\b",
        r"\bgiving back\b",
        r"\bcharitable\b",
    ]),
    "environment": _compile([
        r"\bclimate\b",
        r"\bnet[\s-]?zero\b",
        r"\bemissions?\b",
        r"\bcarbon\b",
        r"\bsustainab(?:le|ility)\b",
        r"\brenewable\b",
        r"\bbiodiversity\b",
        r"\benvironmental\b",
    ]),
    "shareholder": _compile([
        r"\bshareholders?\b",
        r"\bstockholders?\b",
        r"\bshareholder value\b",
        r"\binvestor returns\b",
    ]),
    "safety_quality": _compile([
        r"\bsafety\b",
        r"\bproduct quality\b",
        r"\bquality of care\b",
        r"\breliab(?:le|ility)\b",
        r"\boperational excellence\b",
        r"\bquality\b",
    ]),
    "collaboration": _compile([
        r"\bcollaborat(?:e|ion|ive)\b",
        r"\bpartnerships?\b",
        r"\bteamwork\b",
        r"\bstakeholders?\b",
    ]),
}

BOILERPLATE_PATTERNS = _compile([
    r"\bexcellence\b",
    r"\bworld[\s-]?class\b",
    r"\bpassionate\b",
    r"\bbest[\s-]in[\s-]class\b",
    r"\bcutting[\s-]edge\b",
])

# Original compact tone lists for within-firm comparison. These are not
# the Loughran-McDonald dictionaries and should not be treated as a
# general-purpose financial sentiment model.
POSITIVE_WORDS = _compile([
    r"\bopportunit(?:y|ies)\b",
    r"\bprogress\b",
    r"\bimproved?\b",
    r"\bimprovement\b",
    r"\bconfident\b",
    r"\bproud\b",
    r"\badvance[ds]?\b",
    r"\bsuccess(?:ful|es)?\b",
    r"\bbenefit(?:s|ed)?\b",
])
NEGATIVE_WORDS = _compile([
    r"\blitigation\b",
    r"\bmisconduct\b",
    r"\bviolation\b",
    r"\bharm\b",
    r"\badverse\b",
    r"\bfailure\b",
    r"\bscandal\b",
    r"\bpenalty\b",
    r"\bremediation\b",
    r"\bcontroversy\b",
    r"\blawsuit\b",
    r"\bcrisis\b",
])
# "Will" and "may" are too common in securities prose to be informative.
COMMITMENT_PATTERNS = _compile([
    r"\bcommits?\b",
    r"\bcommitted\b",
    r"\bcommitment\b",
    r"\bpledge[ds]?\b",
    r"\bensure\b",
    r"\bpromise[ds]?\b",
])
UNCERTAINTY_PATTERNS = _compile([
    r"\buncertain(?:ty|ties)?\b",
    r"\bmight\b",
    r"\bcould\b",
    r"\bapproximately\b",
    r"\bpossibl(?:e|y)\b",
])

# Discretionary practices in the proxy. Patterns are intentionally
# specific so that ordinary legal boilerplate does not count as a
# lived value.
BEHAVIORAL_PATTERNS = {
    "flag_dei_metrics": _compile([
        r"\beeo-?1\b",
        r"\b\d{1,3}(?:\.\d+)?\s*(?:%|percent)\b(?:\s+\w+){0,8}\s+"
        r"(?:women|female|black|african[\s-]american|hispanic|latino|latina|"
        r"asian|underrepresented|people of color|racially|ethnically)",
        r"(?:women|female|black|hispanic|latino|latina|asian|underrepresented|"
        r"people of color).{0,50}\b\d{1,3}(?:\.\d+)?\s*(?:%|percent)\b",
        r"\brepresentation goals?\b",
    ]),
    "flag_pay_equity": _compile([
        r"\bpay equity\b",
        r"\bpay gap\b",
        r"\bgender pay\b",
        r"\bracial pay\b",
        r"\bequal pay\b",
    ]),
    "flag_inclusion_in_pay": _compile([
        r"(?:diversity|inclusion|representation).{0,90}"
        r"(?:metric|modifier|scorecard|incentive|bonus|compensation|performance measure)",
        r"(?:metric|modifier|scorecard|incentive|bonus|performance measure).{0,90}"
        r"(?:diversity|inclusion|representation)",
    ]),
    "flag_emissions_target": _compile([
        r"\bnet[\s-]?zero\b",
        r"\bscience[\s-]based targets?\b",
        r"\bsbti\b",
        r"\bscope\s*[12]\b",
        r"\bcarbon neutral\b",
        r"\bgreenhouse gas\b",
        r"\bghg\b",
    ]),
    "flag_climate_in_pay": _compile([
        r"(?:emissions?|climate|sustainability|\besg\b|\bghg\b).{0,90}"
        r"(?:metric|modifier|scorecard|incentive|bonus|compensation|performance measure)",
        r"(?:metric|modifier|scorecard|incentive|bonus|performance measure).{0,90}"
        r"(?:emissions?|climate|sustainability|\besg\b|\bghg\b)",
    ]),
    "flag_board_esg_oversight": _compile([
        r"\b(?:sustainability|esg|corporate responsibility|public responsibility|"
        r"safety and sustainability|environmental(?:,| and) social)"
        r"(?:\s+\w+){0,4}\s+committee\b",
    ]),
    "flag_safety_metrics": _compile([
        r"\btrir\b",
        r"\bltir\b",
        r"\btotal recordable\b",
        r"\blost[\s-]time incident\b",
        r"\bprocess safety\b",
        r"\bdart rate\b",
    ]),
    "flag_safety_in_pay": _compile([
        r"\bsafety\b.{0,80}(?:metric|modifier|scorecard|incentive|bonus|performance measure)",
        r"(?:metric|modifier|scorecard|incentive|bonus|performance measure).{0,80}\bsafety\b",
    ]),
    "flag_human_capital_metrics": _compile([
        r"\btraining hours\b",
        r"\baverage hours of training\b",
        r"\bvoluntary turnover\b",
        r"\bturnover rate\b",
        r"\bemployee engagement (?:score|survey|index)\b",
        r"\bliving wage\b",
        r"\btuition (?:assistance|reimbursement)\b",
    ]),
    "flag_customer_metric_in_pay": _compile([
        r"(?:net promoter|customer satisfaction|client satisfaction|\bnps\b).{0,90}"
        r"(?:metric|modifier|scorecard|incentive|bonus|compensation|performance measure)",
        r"(?:metric|modifier|scorecard|incentive|bonus|performance measure).{0,90}"
        r"(?:net promoter|customer satisfaction|client satisfaction|\bnps\b)",
    ]),
    "flag_political_disclosure": _compile([
        r"\bpolitical contributions?\b",
        r"\bpolitical spending\b",
        r"\blobbying expenditures?\b",
        r"\bpac contributions?\b",
    ]),
    "flag_community_investment": _compile([
        r"(?:donated|charitable giving|charitable contributions|philanthropic|"
        r"community investments?).{0,40}\$\s?\d",
        r"\$\s?\d[\d,\.]+\s*(?:million|billion).{0,50}"
        r"(?:donat|charitable|philanthrop|community invest)",
    ]),
}


def count_patterns(text: str, patterns: list[re.Pattern[str]]) -> int:
    """Count non-overlapping matches across patterns.

    Patterns within one theme can hit the same sentence more than once
    ("diversity" and "inclusion"). That is intentional: a sentence that
    uses several words from the category is stronger evidence than a
    sentence that uses one.
    """
    if not text:
        return 0
    return sum(len(pattern.findall(text)) for pattern in patterns)


def theme_counts(text: str) -> dict[str, int]:
    return {theme: count_patterns(text, THEME_PATTERNS[theme]) for theme in THEME_ORDER}


def behavioral_flags(text: str) -> dict[str, int]:
    """Return match counts. Callers treat a positive count as presence."""
    return {
        name: count_patterns(text, patterns)
        for name, patterns in BEHAVIORAL_PATTERNS.items()
    }
