"""Project-wide rules that more than one part needs to share.

These values are research decisions, not tuning knobs discovered after
looking at the results. Parts 3 and 4 import them so the measure and the
event windows cannot drift apart from the text the READMEs describe.
"""

# One snapshot / one proxy per calendar year, inclusive.
YEARS = list(range(2016, 2025))

# Content-word cosine below this means the About page "changed from the
# prior year". 0.85 keeps identical and lightly edited pages in the
# "stable" group and treats a real rewrite as a change. The raw similarity
# is stored so the cutoff can be recomputed without rescraping.
CHANGE_THRESHOLD = 0.85

# Cleaned About-page text shorter than this is treated as a failed
# extraction (navigation shell, blocked page, or empty JavaScript render).
# Berkshire's real homepage is short but still above this bar; a page of
# only menu labels is not.
MIN_ABOUT_CHARS = 120

# A stated theme is "emphasized" when it accounts for at least this share
# of all codebook hits on the About page. One stray mention on a long
# values page does not create an operationalization test.
STATED_EMPHASIS_SHARE = 0.12

# Added to a proxy theme's per-1,000-word density when a behavioral
# indicator for that theme fires. 2.0 is about a moderate verbal emphasis,
# so a concrete practice matters, but it does not erase the prose.
LIVED_FLAG_BONUS = 2.0

# Organizational Authenticity Index weights. They sum to 1.
# Cosine = rhetorical alignment of theme mix.
# Follow-through = share of emphasized, operationalizable stated themes
# that show up as a concrete practice in that year's proxy.
OAI_WEIGHT_COSINE = 0.50
OAI_WEIGHT_FOLLOW = 0.50

RUBRIC_VERSION = "codebook-1.0"

# Fixed calendar, identical for every firm. It is context for joining,
# not a claim that the event affected that firm.
EVENT_CONTEXT = {
    2016: "Paris Agreement entered into force; US election",
    2017: "US announced intent to withdraw from the Paris Agreement",
    2018: "Peak corporate response to #MeToo",
    2019: "Business Roundtable statement on corporate purpose",
    2020: "COVID-19; George Floyd protests; SEC adopted human-capital disclosure amendment",
    2021: "First full proxy season under the human-capital rule; COP26",
    2022: "Russia-Ukraine energy shock; organized US anti-ESG push",
    2023: "SFFA v. Harvard; state anti-ESG legislation and shareholder proposals",
    2024: "Post-backlash proxy season; DEI language under political pressure",
}

# Chosen before scores were computed. They are interpretation cases,
# not a sample that was picked because the scores looked convenient.
FACE_VALIDITY_TICKERS = ["WFC", "CRM", "BRK.B", "XOM", "NKE", "META"]

# Part 4 windows. 2022 is reported as a transition year and is not folded
# into either contrast.
WINDOWS = {
    "pre": (2018, 2019),
    "shock": (2020, 2021),
    "transition": (2022, 2022),
    "backlash": (2023, 2024),
}

# Identifies this project to Wayback and EDGAR. SEC asks filers' APIs
# to receive a descriptive user agent; a generic Python agent is blocked.
# EDGAR returns 403 unless the user agent contains a contact email.
USER_AGENT = (
    "OrganizationalAuthenticityResearch/1.0 "
    "(academic research; contact: research-local@example.com)"
)
