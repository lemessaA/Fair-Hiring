"""PII masking utilities for resumes.

Masks the categories the user opted into:
- Email addresses
- Phone numbers
- Addresses (street + ZIP/postal codes)
- Gender pronouns / gendered terms (neutralized to they/them/their)
"""

from __future__ import annotations

import re
from dataclasses import dataclass


EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")

# Catches common phone formats: +1 (415) 555-1234, 415-555-1234, 415.555.1234, etc.
PHONE_RE = re.compile(
    r"""
    (?<!\w)
    (?:\+?\d{1,3}[\s.-]?)?      # optional country code
    (?:\(?\d{2,4}\)?[\s.-]?)    # area code
    \d{3}[\s.-]?\d{3,4}         # local number
    (?!\w)
    """,
    re.VERBOSE,
)

# US-style ZIP and common postal code patterns
ZIP_RE = re.compile(r"\b\d{5}(?:-\d{4})?\b")

# Street address patterns: "123 Main Street", "45 Oak Ave", etc.
STREET_RE = re.compile(
    r"\b\d{1,5}\s+(?:[A-Z][\w'-]*\s+){1,4}"
    r"(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|"
    r"Lane|Ln|Way|Court|Ct|Place|Pl|Square|Sq|Highway|Hwy|Parkway|Pkwy)\.?",
    re.IGNORECASE,
)

# City, State pattern (e.g. "San Francisco, CA" or "Austin, TX 78701")
CITY_STATE_RE = re.compile(
    r"\b[A-Z][a-zA-Z\s.'-]+,\s*(?:[A-Z]{2}|[A-Z][a-zA-Z]+)(?:\s+\d{5}(?:-\d{4})?)?\b"
)

# Gender pronoun substitutions (case-insensitive, word boundaries)
GENDER_SUBS: dict[str, str] = {
    r"\bhe\b": "they",
    r"\bshe\b": "they",
    r"\bhim\b": "them",
    r"\bher\b": "them",
    r"\bhis\b": "their",
    r"\bhers\b": "theirs",
    r"\bhimself\b": "themself",
    r"\bherself\b": "themself",
    r"\bmr\.\b": "Mx.",
    r"\bmrs\.\b": "Mx.",
    r"\bms\.\b": "Mx.",
    r"\bmiss\b": "Mx.",
    r"\bsir\b": "they",
    r"\bma'am\b": "they",
    r"\bmadam\b": "they",
    r"\bgentleman\b": "person",
    r"\bgentlemen\b": "people",
    r"\blady\b": "person",
    r"\bladies\b": "people",
    r"\bfemale\b": "person",
    r"\bmale\b": "person",
    r"\bwoman\b": "person",
    r"\bwomen\b": "people",
    r"\bman\b": "person",
    r"\bmen\b": "people",
}


@dataclass
class MaskingReport:
    emails: int = 0
    phones: int = 0
    addresses: int = 0
    gendered_terms: int = 0

    def total(self) -> int:
        return self.emails + self.phones + self.addresses + self.gendered_terms


def mask_pii(text: str) -> tuple[str, MaskingReport]:
    """Mask PII from a resume.

    Returns the masked text along with a small report of how many items
    were redacted, useful for UI transparency.
    """
    report = MaskingReport()

    def _sub_count(pattern: re.Pattern[str], replacement: str, source: str) -> tuple[str, int]:
        new_text, count = pattern.subn(replacement, source)
        return new_text, count

    masked = text

    masked, report.emails = _sub_count(EMAIL_RE, "[EMAIL]", masked)
    masked, report.phones = _sub_count(PHONE_RE, "[PHONE]", masked)

    # Address-ish patterns
    masked, addr_zip = _sub_count(ZIP_RE, "[POSTAL]", masked)
    masked, addr_street = _sub_count(STREET_RE, "[ADDRESS]", masked)
    masked, addr_city = _sub_count(CITY_STATE_RE, "[LOCATION]", masked)
    report.addresses = addr_zip + addr_street + addr_city

    # Gendered terms / pronouns
    gendered_count = 0
    for pattern, replacement in GENDER_SUBS.items():
        compiled = re.compile(pattern, re.IGNORECASE)
        masked, n = compiled.subn(replacement, masked)
        gendered_count += n
    report.gendered_terms = gendered_count

    return masked, report
