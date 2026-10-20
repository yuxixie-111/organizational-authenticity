"""The 50-firm sample and the page-finding rules that depend on it.

The assignment fixes the firms: the 10 largest names, by market cap, in
five GICS sectors, using the S&P 500 composition as of January 2024.
This file does not re-rank market caps. The list is taken as given.

Each firm has an ordered set of historical About-page URLs. The collector
tries them until every year from 2016 through 2024 has a capture, and
then stops, so a later seed cannot replace an earlier successful one.
URL scoring (in the collector) still breaks ties when several seeds hit
the same year.

Alternate CIKs cover reincorporations where the pre-switch proxy lives
under a different EDGAR filer. The primary CIK wins if both filed a
DEF 14A in the same year.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Company:
    ticker: str
    name: str
    sector: str
    cik: int
    seeds: tuple[str, ...]
    domains: tuple[str, ...]
    alternate_ciks: tuple[int, ...] = ()
    # Berkshire's public face is the corporate homepage. It has no
    # separate values URL. The homepage is accepted only in that case.
    allow_homepage: bool = False


COMPANIES: tuple[Company, ...] = (
    Company(
        "MSFT", "Microsoft", "Technology", 789019,
        ("https://www.microsoft.com/en-us/about", "https://www.microsoft.com/about/"),
        ("microsoft.com",),
    ),
    Company(
        "AAPL", "Apple", "Technology", 320193,
        ("https://www.apple.com/about/",),
        ("apple.com",),
    ),
    Company(
        "NVDA", "NVIDIA", "Technology", 1045810,
        (
            "https://www.nvidia.com/en-us/about-nvidia/",
            "https://www.nvidia.com/object/about-nvidia.html",
        ),
        ("nvidia.com",),
    ),
    Company(
        "GOOGL", "Alphabet", "Technology", 1652044,
        (
            "https://about.google/",
            "https://about.google/intl/en/",
            "https://www.google.com/about/philosophy.html",
            "https://abc.xyz/",
        ),
        ("about.google", "google.com", "abc.xyz"),
    ),
    Company(
        "META", "Meta Platforms", "Technology", 1326801,
        (
            "https://about.meta.com/",
            "https://about.facebook.com/",
            "https://about.fb.com/",
            "https://www.facebook.com/about",
        ),
        ("meta.com", "facebook.com", "fb.com", "about.meta.com"),
    ),
    Company(
        "AVGO", "Broadcom", "Technology", 1730168,
        (
            "https://www.broadcom.com/company/about-us",
            "https://www.broadcom.com/company/about-us/about-us",
        ),
        ("broadcom.com",),
        # Broadcom Limited filings before the 2018 Delaware reincorporation.
        alternate_ciks=(1649338,),
    ),
    Company(
        "CRM", "Salesforce", "Technology", 1108524,
        (
            "https://www.salesforce.com/company/our-story/",
            "https://www.salesforce.com/company/",
            "https://www.salesforce.com/company/values/",
        ),
        ("salesforce.com",),
    ),
    Company(
        "ORCL", "Oracle", "Technology", 1341439,
        (
            "https://www.oracle.com/corporate/",
            "https://www.oracle.com/us/corporate/index.html",
        ),
        ("oracle.com",),
    ),
    Company(
        "IBM", "IBM", "Technology", 51143,
        ("https://www.ibm.com/about", "https://www.ibm.com/us-en/about"),
        ("ibm.com",),
    ),
    Company(
        "INTC", "Intel", "Technology", 50863,
        (
            "https://www.intel.com/content/www/us/en/company-overview/company-overview.html",
            "https://www.intel.com/content/www/us/en/company-overview.html",
        ),
        ("intel.com",),
    ),
    Company(
        "BRK.B", "Berkshire Hathaway", "Financials", 1067983,
        ("https://www.berkshirehathaway.com/",),
        ("berkshirehathaway.com",),
        allow_homepage=True,
    ),
    Company(
        "JPM", "JPMorgan Chase", "Financials", 19617,
        (
            "https://www.jpmorganchase.com/about",
            "https://www.jpmorganchase.com/corporate/About-JPMC/about-us.htm",
        ),
        ("jpmorganchase.com",),
    ),
    Company(
        "BAC", "Bank of America", "Financials", 70858,
        (
            "https://about.bankofamerica.com/",
            "https://about.bankofamerica.com/en/about-us",
            "https://www.bankofamerica.com/about/",
        ),
        ("bankofamerica.com",),
    ),
    Company(
        "WFC", "Wells Fargo", "Financials", 72971,
        (
            "https://www.wellsfargo.com/about/",
            "https://www.wellsfargo.com/about/corporate/",
        ),
        ("wellsfargo.com",),
    ),
    Company(
        "GS", "Goldman Sachs", "Financials", 886982,
        (
            "https://www.goldmansachs.com/about-us/",
            "https://www.goldmansachs.com/our-firm/index.html",
            "https://www.goldmansachs.com/who-we-are/",
        ),
        ("goldmansachs.com",),
    ),
    Company(
        "MS", "Morgan Stanley", "Financials", 895421,
        (
            "https://www.morganstanley.com/about-us",
            "https://www.morganstanley.com/about-us/our-story",
        ),
        ("morganstanley.com",),
    ),
    Company(
        "BLK", "BlackRock", "Financials", 1364742,
        (
            "https://www.blackrock.com/corporate/about-us",
            "https://www.blackrock.com/corporate/about-blackrock",
        ),
        ("blackrock.com",),
    ),
    Company(
        "SCHW", "Charles Schwab", "Financials", 316709,
        (
            "https://www.aboutschwab.com/",
            "https://www.aboutschwab.com/who-we-are",
            "https://www.schwab.com/about-us",
        ),
        ("aboutschwab.com", "schwab.com"),
    ),
    Company(
        "AXP", "American Express", "Financials", 4962,
        (
            "https://about.americanexpress.com/",
            "https://www.americanexpress.com/about/",
            "https://www.americanexpress.com/us/company.html",
        ),
        ("americanexpress.com",),
    ),
    Company(
        "C", "Citigroup", "Financials", 831001,
        (
            "https://www.citigroup.com/global/about-us",
            "https://www.citigroup.com/citi/about/",
        ),
        ("citigroup.com", "citi.com"),
    ),
    Company(
        "LLY", "Eli Lilly", "Healthcare", 59478,
        ("https://www.lilly.com/who-we-are", "https://www.lilly.com/about"),
        ("lilly.com",),
    ),
    Company(
        "UNH", "UnitedHealth Group", "Healthcare", 731766,
        (
            "https://www.unitedhealthgroup.com/about.html",
            "https://www.unitedhealthgroup.com/about/who-we-are.html",
        ),
        ("unitedhealthgroup.com",),
    ),
    Company(
        "JNJ", "Johnson & Johnson", "Healthcare", 200406,
        ("https://www.jnj.com/about-jnj", "https://www.jnj.com/our-company"),
        ("jnj.com",),
    ),
    Company(
        "ABBV", "AbbVie", "Healthcare", 1551152,
        (
            "https://www.abbvie.com/who-we-are.html",
            "https://www.abbvie.com/our-company.html",
        ),
        ("abbvie.com",),
    ),
    Company(
        "MRK", "Merck", "Healthcare", 310158,
        ("https://www.merck.com/company-overview/", "https://www.merck.com/about/"),
        ("merck.com",),
    ),
    Company(
        "TMO", "Thermo Fisher Scientific", "Healthcare", 97745,
        (
            "https://corporate.thermofisher.com/us/en/index/about.html",
            "https://www.thermofisher.com/us/en/home/about-us.html",
        ),
        ("thermofisher.com",),
    ),
    Company(
        "ABT", "Abbott Laboratories", "Healthcare", 1800,
        (
            "https://www.abbott.com/about-abbott.html",
            "https://www.abbott.com/about-abbott/who-we-are.html",
        ),
        ("abbott.com",),
    ),
    Company(
        "PFE", "Pfizer", "Healthcare", 78003,
        ("https://www.pfizer.com/about", "https://www.pfizer.com/about/purpose"),
        ("pfizer.com",),
    ),
    Company(
        "MDT", "Medtronic", "Healthcare", 1613103,
        (
            "https://www.medtronic.com/us-en/our-company.html",
            "https://www.medtronic.com/en-us/our-company.html",
        ),
        ("medtronic.com",),
        alternate_ciks=(64670,),
    ),
    Company(
        "BMY", "Bristol-Myers Squibb", "Healthcare", 14272,
        (
            "https://www.bms.com/about-us.html",
            "https://www.bms.com/about-us/our-company.html",
        ),
        ("bms.com",),
    ),
    Company(
        "AMZN", "Amazon", "Consumer Discretionary", 1018724,
        ("https://www.aboutamazon.com/", "https://www.aboutamazon.com/about-us"),
        ("aboutamazon.com", "amazon.com"),
    ),
    Company(
        "TSLA", "Tesla", "Consumer Discretionary", 1318605,
        ("https://www.tesla.com/about", "https://www.tesla.com/about#mission"),
        ("tesla.com",),
    ),
    Company(
        "HD", "Home Depot", "Consumer Discretionary", 354950,
        (
            "https://corporate.homedepot.com/about",
            "https://corporate.homedepot.com/page/about",
        ),
        ("homedepot.com",),
    ),
    Company(
        "MCD", "McDonald's", "Consumer Discretionary", 63908,
        (
            "https://corporate.mcdonalds.com/corpmcd/our-company/who-we-are.html",
            "https://corporate.mcdonalds.com/corpmcd/our-company.html",
            "https://www.mcdonalds.com/us/en-us/about-us.html",
        ),
        ("mcdonalds.com",),
    ),
    Company(
        "NKE", "Nike", "Consumer Discretionary", 320187,
        ("https://about.nike.com/", "https://purpose.nike.com/", "https://www.nike.com/about"),
        ("nike.com",),
    ),
    Company(
        "SBUX", "Starbucks", "Consumer Discretionary", 829224,
        (
            "https://about.starbucks.com/",
            "https://www.starbucks.com/about-us/",
            "https://www.starbucks.com/about-us/company-information",
        ),
        ("starbucks.com",),
    ),
    Company(
        "TGT", "Target", "Consumer Discretionary", 27419,
        (
            "https://corporate.target.com/about",
            "https://corporate.target.com/about/purpose-history",
        ),
        ("target.com",),
    ),
    Company(
        "LOW", "Lowe's", "Consumer Discretionary", 60667,
        (
            "https://corporate.lowes.com/who-we-are",
            "https://corporate.lowes.com/about-lowes",
        ),
        ("lowes.com",),
    ),
    Company(
        "TJX", "TJX Companies", "Consumer Discretionary", 109198,
        ("https://www.tjx.com/company", "https://www.tjx.com/company/about-tjx"),
        ("tjx.com",),
    ),
    Company(
        "F", "Ford Motor", "Consumer Discretionary", 37996,
        (
            "https://corporate.ford.com/about.html",
            "https://corporate.ford.com/about/our-purpose.html",
            "https://corporate.ford.com/about-ford/our-purpose.html",
        ),
        ("ford.com",),
    ),
    Company(
        "XOM", "ExxonMobil", "Energy", 34088,
        (
            "https://corporate.exxonmobil.com/who-we-are",
            "https://corporate.exxonmobil.com/who-we-are/our-guiding-principles",
            "https://corporate.exxonmobil.com/About-us",
        ),
        ("exxonmobil.com",),
    ),
    Company(
        "CVX", "Chevron", "Energy", 93410,
        ("https://www.chevron.com/about", "https://www.chevron.com/about/who-we-are"),
        ("chevron.com",),
    ),
    Company(
        "COP", "ConocoPhillips", "Energy", 1163165,
        (
            "https://www.conocophillips.com/about-us/",
            "https://www.conocophillips.com/about-us/who-we-are/",
        ),
        ("conocophillips.com",),
    ),
    Company(
        "EOG", "EOG Resources", "Energy", 821189,
        (
            "https://www.eogresources.com/about/",
            "https://www.eogresources.com/company/",
        ),
        ("eogresources.com",),
    ),
    Company(
        "SLB", "SLB (Schlumberger)", "Energy", 87347,
        ("https://www.slb.com/about", "https://www.slb.com/who-we-are", "https://www.schlumberger.com/about"),
        ("slb.com", "schlumberger.com"),
    ),
    Company(
        "MPC", "Marathon Petroleum", "Energy", 1510295,
        (
            "https://www.marathonpetroleum.com/About/",
            "https://www.marathonpetroleum.com/About/Our-Company/",
        ),
        ("marathonpetroleum.com",),
    ),
    Company(
        "PSX", "Phillips 66", "Energy", 1534701,
        ("https://www.phillips66.com/about", "https://www.phillips66.com/about-us"),
        ("phillips66.com",),
    ),
    Company(
        "VLO", "Valero Energy", "Energy", 1035002,
        ("https://www.valero.com/about", "https://www.valero.com/about-us"),
        ("valero.com",),
    ),
    Company(
        "OXY", "Occidental Petroleum", "Energy", 797468,
        ("https://www.oxy.com/about/", "https://www.oxy.com/about/our-company/"),
        ("oxy.com",),
    ),
    Company(
        "HAL", "Halliburton", "Energy", 45012,
        (
            "https://www.halliburton.com/en/about-us",
            "https://www.halliburton.com/en-us/about-us.html",
        ),
        ("halliburton.com",),
    ),
)


def by_ticker() -> dict[str, Company]:
    return {company.ticker: company for company in COMPANIES}
