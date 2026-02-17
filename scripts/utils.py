"""
TherapistIndex — Shared Utilities
Common functions used across the data pipeline scripts.
"""

import json
import logging
import os
import re
import sys
from pathlib import Path

# Project root is one level up from scripts/
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"
DATA_DIR = PROJECT_ROOT / "data"


def setup_logging(name: str, level=logging.INFO) -> logging.Logger:
    """Configure logging with consistent format across scripts."""
    logger = logging.getLogger(name)
    logger.setLevel(level)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)
        fmt = logging.Formatter(
            "%(asctime)s [%(name)s] %(levelname)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(fmt)
        logger.addHandler(handler)
    return logger


def load_config(filename: str) -> dict:
    """Load a JSON config file from the config/ directory."""
    path = CONFIG_DIR / filename
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_insurance_lookup() -> dict[str, str]:
    """Build alias -> canonical name lookup from insurance_list.json."""
    config = load_config("insurance_list.json")
    lookup = {}
    for provider in config["insurance_providers"]:
        canonical = provider["canonical_name"]
        for alias in provider["aliases"]:
            lookup[alias.lower().strip()] = canonical
    return lookup


def load_specialization_lookup() -> dict[str, str]:
    """Build alias -> canonical name lookup from specializations.json."""
    config = load_config("specializations.json")
    lookup = {}
    for spec in config["specializations"]:
        canonical = spec["canonical_name"]
        for alias in spec["aliases"]:
            lookup[alias.lower().strip()] = canonical
    return lookup


def load_approach_lookup() -> dict[str, str]:
    """Build alias -> canonical name lookup for therapy approaches."""
    config = load_config("specializations.json")
    lookup = {}
    for approach in config["therapy_approaches"]:
        canonical = approach["canonical_name"]
        for alias in approach["aliases"]:
            lookup[alias.lower().strip()] = canonical
    return lookup


def load_filter_keywords() -> dict:
    """Load filter keywords for excluding non-therapist results."""
    return load_config("filter_keywords.json")


def standardize_phone(phone: str) -> str:
    """
    Standardize phone number to (XXX) XXX-XXXX format.
    Returns empty string if phone can't be parsed.
    """
    if not phone or not isinstance(phone, str):
        return ""
    # Strip everything except digits
    digits = re.sub(r"\D", "", phone)
    # Handle country code prefix
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    if len(digits) != 10:
        return ""
    return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"


def standardize_state(state: str) -> str:
    """Convert state name to two-letter abbreviation."""
    if not state or not isinstance(state, str):
        return ""
    state = state.strip()
    # Already an abbreviation
    if len(state) == 2:
        return state.upper()
    STATE_MAP = {
        "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR",
        "california": "CA", "colorado": "CO", "connecticut": "CT",
        "delaware": "DE", "district of columbia": "DC", "florida": "FL",
        "georgia": "GA", "hawaii": "HI", "idaho": "ID", "illinois": "IL",
        "indiana": "IN", "iowa": "IA", "kansas": "KS", "kentucky": "KY",
        "louisiana": "LA", "maine": "ME", "maryland": "MD",
        "massachusetts": "MA", "michigan": "MI", "minnesota": "MN",
        "mississippi": "MS", "missouri": "MO", "montana": "MT",
        "nebraska": "NE", "nevada": "NV", "new hampshire": "NH",
        "new jersey": "NJ", "new mexico": "NM", "new york": "NY",
        "north carolina": "NC", "north dakota": "ND", "ohio": "OH",
        "oklahoma": "OK", "oregon": "OR", "pennsylvania": "PA",
        "rhode island": "RI", "south carolina": "SC", "south dakota": "SD",
        "tennessee": "TN", "texas": "TX", "utah": "UT", "vermont": "VT",
        "virginia": "VA", "washington": "WA", "west virginia": "WV",
        "wisconsin": "WI", "wyoming": "WY",
    }
    return STATE_MAP.get(state.lower(), state.upper()[:2])


def standardize_address(address: str) -> str:
    """
    Clean and standardize an address string.
    - Proper title case
    - Standardize common abbreviations (St, Ave, Blvd, etc.)
    """
    if not address or not isinstance(address, str):
        return ""
    address = address.strip()
    # Title case the whole thing, then fix known abbreviations
    parts = address.split(",")
    cleaned_parts = []
    for part in parts:
        part = part.strip().title()
        # Fix state abbreviations that got title-cased
        part = re.sub(r"\b(Dc)\b", "DC", part)
        part = re.sub(r"\b(Md)\b", "MD", part)
        part = re.sub(r"\b(Va)\b", "VA", part)
        part = re.sub(r"\b(Nw)\b", "NW", part)
        part = re.sub(r"\b(Nw|Ne|Sw|Se)\b", lambda m: m.group().upper(), part)
        part = re.sub(r"\b(Usa?)\b", lambda m: m.group().upper(), part)
        cleaned_parts.append(part)
    return ", ".join(cleaned_parts)


def is_valid_url(url: str) -> bool:
    """Basic URL validation — checks structure, not reachability."""
    if not url or not isinstance(url, str):
        return False
    url = url.strip()
    pattern = re.compile(
        r"^https?://"
        r"(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+"
        r"[a-zA-Z]{2,}"
        r"(?:/[^\s]*)?$"
    )
    return bool(pattern.match(url))


def normalize_url(url: str) -> str:
    """Ensure URL has https:// prefix and strip trailing slashes."""
    if not url or not isinstance(url, str):
        return ""
    url = url.strip().rstrip("/")
    if not url:
        return ""
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url


def guess_license_type(name: str, category: str = "") -> str:
    """
    Attempt to guess license type from business name/category.
    Returns one of: LCSW, LPC, LMFT, PsyD, PhD, MD/Psychiatrist, LCPC, LCMFT, or empty string.
    """
    text = f"{name} {category}".lower()
    if "psychiatr" in text or ", md" in text or "m.d." in text:
        return "MD/Psychiatrist"
    if "psyd" in text or "psy.d" in text:
        return "PsyD"
    if "ph.d" in text or "phd" in text or "psychologist" in text:
        return "PhD"
    if "lcsw" in text or "lcsw-c" in text:
        return "LCSW"
    if "lcpc" in text:
        return "LCPC"
    if "lpc" in text:
        return "LPC"
    if "lcmft" in text:
        return "LCMFT"
    if "lmft" in text or "marriage and family" in text:
        return "LMFT"
    return ""


def is_group_practice(name: str) -> bool:
    """Detect if a listing is a group practice vs solo practitioner."""
    indicators = [
        "group", "associates", "& associates", "center", "centre",
        "clinic", "institute", "practice", "services", "wellness",
        "counseling center", "therapy center", "behavioral health",
        "mental health services", "psychological services",
        "partners", "collective", "collaborative",
    ]
    name_lower = name.lower() if name else ""
    return any(ind in name_lower for ind in indicators)


def match_insurance(text: str, lookup: dict[str, str]) -> list[str]:
    """
    Scan text for insurance provider mentions.
    Returns list of canonical insurance names found.
    """
    if not text:
        return []
    text_lower = text.lower()
    found = set()
    for alias, canonical in lookup.items():
        if alias in text_lower:
            found.add(canonical)
    return sorted(found)


def match_specializations(text: str, lookup: dict[str, str]) -> list[str]:
    """
    Scan text for specialization mentions.
    Returns list of canonical specialization names found.
    """
    if not text:
        return []
    text_lower = text.lower()
    found = set()
    for alias, canonical in lookup.items():
        # Use word boundary matching for short aliases to avoid false positives
        if len(alias) <= 3:
            if re.search(r"\b" + re.escape(alias) + r"\b", text_lower):
                found.add(canonical)
        else:
            if alias in text_lower:
                found.add(canonical)
    return sorted(found)


def detect_accepting_patients(text: str) -> str:
    """
    Scan text for indicators about accepting new patients.
    Returns: Yes, No, Waitlist, or Unknown.
    """
    if not text:
        return "Unknown"
    text_lower = text.lower()
    no_indicators = [
        "not accepting new",
        "not currently accepting",
        "no longer accepting",
        "practice is full",
        "caseload is full",
        "currently full",
    ]
    waitlist_indicators = [
        "waitlist",
        "wait list",
        "waiting list",
        "join the waitlist",
    ]
    yes_indicators = [
        "accepting new patients",
        "accepting new clients",
        "currently accepting",
        "now accepting",
        "welcoming new",
        "taking new patients",
        "taking new clients",
        "open to new",
        "availability for new",
        "schedule an appointment",
        "book an appointment",
        "book a session",
        "free consultation",
        "complimentary consultation",
    ]
    for phrase in no_indicators:
        if phrase in text_lower:
            return "No"
    for phrase in waitlist_indicators:
        if phrase in text_lower:
            return "Waitlist"
    for phrase in yes_indicators:
        if phrase in text_lower:
            return "Yes"
    return "Unknown"


def detect_telehealth(text: str) -> str:
    """
    Scan text for telehealth indicators.
    Returns: Yes - Video, Yes - Phone, Yes - Both, No, or Unknown.
    """
    if not text:
        return "Unknown"
    text_lower = text.lower()
    video_indicators = [
        "telehealth", "teletherapy", "video session", "video therapy",
        "online therapy", "online counseling", "virtual session",
        "virtual therapy", "virtual appointment", "doxy", "zoom",
        "simplepractice telehealth", "remote therapy",
    ]
    phone_indicators = [
        "phone session", "phone therapy", "telephone session",
        "telephone therapy", "phone counseling",
    ]
    no_indicators = [
        "in-person only", "in person only", "office visits only",
        "no telehealth", "does not offer telehealth",
    ]
    for phrase in no_indicators:
        if phrase in text_lower:
            return "No"
    has_video = any(ind in text_lower for ind in video_indicators)
    has_phone = any(ind in text_lower for ind in phone_indicators)
    if has_video and has_phone:
        return "Yes - Both"
    if has_video:
        return "Yes - Video"
    if has_phone:
        return "Yes - Phone"
    return "Unknown"


def detect_sliding_scale(text: str) -> str:
    """Detect if therapist offers sliding scale fees. Returns Yes, No, or Unknown."""
    if not text:
        return "Unknown"
    text_lower = text.lower()
    yes_indicators = [
        "sliding scale", "sliding fee", "income-based",
        "reduced fee", "reduced rate", "financial hardship",
        "ability to pay", "affordable rates",
    ]
    no_indicators = [
        "no sliding scale", "does not offer sliding",
        "do not offer sliding",
    ]
    for phrase in no_indicators:
        if phrase in text_lower:
            return "No"
    for phrase in yes_indicators:
        if phrase in text_lower:
            return "Yes"
    return "Unknown"


def extract_price_range(text: str) -> tuple[int | None, int | None]:
    """
    Extract price range from text.
    Returns (min_price, max_price) or (None, None) if not found.
    """
    if not text:
        return None, None
    # Match patterns like "$150", "$100-$200", "$100 - $200", "$100 to $200"
    pattern = r"\$\s*(\d{2,4})\s*(?:[-–—to]+\s*\$?\s*(\d{2,4}))?"
    matches = re.findall(pattern, text)
    if not matches:
        return None, None
    prices = []
    for match in matches:
        prices.append(int(match[0]))
        if match[1]:
            prices.append(int(match[1]))
    # Filter out unreasonable prices (therapy typically $50-$500/session)
    valid = [p for p in prices if 20 <= p <= 600]
    if not valid:
        return None, None
    return min(valid), max(valid)


def detect_telehealth_platform(text: str) -> str:
    """Detect which telehealth platform is mentioned in text."""
    if not text:
        return ""
    text_lower = text.lower()
    platforms = {
        "doxy.me": ["doxy", "doxy.me"],
        "Zoom": ["zoom"],
        "SimplePractice": ["simplepractice", "simple practice"],
        "TherapyNotes": ["therapynotes", "therapy notes"],
        "VSee": ["vsee"],
        "Google Meet": ["google meet"],
        "Microsoft Teams": ["microsoft teams", "ms teams"],
        "TheraNest": ["theranest"],
        "Jane App": ["jane app", "janeapp"],
    }
    found = []
    for platform, keywords in platforms.items():
        if any(kw in text_lower for kw in keywords):
            found.append(platform)
    return ", ".join(found) if found else ""
