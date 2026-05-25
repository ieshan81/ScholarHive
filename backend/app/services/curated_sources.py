"""Curated search targets — leads for Tavily queries, not fake scholarship records."""

CURATED_SOURCE_HINTS = [
    "site:.edu financial aid international students engineering",
    "ASME scholarship mechanical engineering",
    "SME Education Foundation scholarship",
    "international student scholarship mechanical engineering undergraduate",
    "IEEE scholarship engineering students",
    "university financial aid office international F-1 scholarship",
    "Engineers Without Borders scholarship engineering",
    "Society of Women Engineers scholarship international",
]

CURATED_DOMAINS_TRUSTED = (
    ".edu",
    ".org",
    "asme.org",
    "sme.org",
    "ieee.org",
    "swe.org",
    "fastweb.com",
    "internationalstudent.com",
    "collegeboard.org",
)

SUSPICIOUS_DOMAIN_HINTS = (
    "bit.ly",
    "tinyurl",
    "click here",
    "pay to apply",
    "application fee required",
    "guaranteed scholarship",
    "win money fast",
)
