from __future__ import annotations

import hashlib
import re
import unicodedata


def clean_text(value: object) -> str:
    if value is None:
        return ""
    text = " ".join(str(value).strip().split())
    return "" if text.lower() in {"nan", "none", "nat"} else text


def normalized_text(value: object) -> str:
    text = clean_text(value).lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(character for character in text if not unicodedata.combining(character))
    return text.replace("ß", "ss")


def technical_location_area(value: object) -> str:
    text = clean_text(value)
    return text.split("/")[0] if text else "UNKNOWN"


def frequency_hint(value: object) -> str:
    text = normalized_text(value)
    matches: list[str] = []

    quarter_match = bool(
        re.search(r"vierteljaehr|vierteljahr|quartal|\b3\s*m\b", text)
    )
    half_year_match = bool(
        re.search(r"halbjaehr|halbjahr|\b6\s*m\b", text)
    )

    if re.search(r"zaehler|counter|stueckzahl|hubzahl|betriebsstund", text):
        matches.append("counter_based")
    if re.search(r"taeglich|taglich|\b\d+(?:[.,]\d+)?\s*t\b", text):
        matches.append("day")
    if re.search(r"woechentlich|wochentlich|\b\d+(?:\s*/\s*\d+)*\s*w\b", text):
        matches.append("week")
    if quarter_match:
        matches.append("quarter")
    if half_year_match:
        matches.append("half_year")

    generic_month = bool(re.search(r"monatlich", text))
    numeric_months = re.findall(r"\b(\d+(?:[.,]\d+)?)\s*m\b", text)
    if generic_month or any(value not in {"3", "6"} for value in numeric_months):
        matches.append("month")

    generic_year = bool(re.search(r"jaehrlich|jahrlich|jahres", text))
    numeric_year = bool(re.search(r"\b\d+(?:[.,]\d+)?\s*j\b", text))
    if numeric_year or (generic_year and not quarter_match and not half_year_match):
        matches.append("year")

    unique = list(dict.fromkeys(matches))
    if not unique:
        return "unknown"
    if len(unique) > 1:
        return "multiple"
    return unique[0]


def task_signature(*parts: object) -> str:
    text = "||".join(normalized_text(part) for part in parts)
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:16]


def hash_bucket(value: object, buckets: int = 128) -> str:
    digest = hashlib.sha1(normalized_text(value).encode("utf-8")).hexdigest()
    return str(int(digest[:8], 16) % buckets)


def keyword_features(value: object) -> dict[str, int]:
    text = normalized_text(value)
    keyword_patterns = {
        "contains_tpm": r"\btpm\b",
        "contains_5s": r"\b5s\b",
        "contains_reinigung": r"reinigung|saeuber",
        "contains_pruefung": r"pruefung|prufen|kontrolle",
        "contains_inspektion": r"inspektion",
        "contains_austausch": r"austausch|wechsel",
        "contains_schmierung": r"schmier",
        "contains_extern": r"extern|dienstleister|edl",
    }
    output = {
        name: int(bool(re.search(pattern, text)))
        for name, pattern in keyword_patterns.items()
    }
    output["task_text_length"] = len(text)
    output["task_token_count"] = len(text.split())
    return output
