from __future__ import annotations

import re

EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
COUNTRY_RE = re.compile(r"^[A-Z]{2}$")


def normalize_email(value: str) -> str:
    email = value.strip().lower()
    if len(email) > 320 or not EMAIL_RE.fullmatch(email):
        raise ValueError("Enter a valid email address")
    return email


def normalize_name(value: str) -> str:
    name = " ".join(value.split())
    if not 1 <= len(name) <= 160:
        raise ValueError("Enter your name")
    return name


def normalize_country(value: str) -> str:
    country = value.strip().upper()
    if not COUNTRY_RE.fullmatch(country):
        raise ValueError("Select a valid country")
    return country
