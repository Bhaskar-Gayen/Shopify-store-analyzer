from __future__ import annotations
import json
import re
from typing import Iterable
from bs4 import BeautifulSoup

SOCIAL_PATTERNS = {
    "instagram": re.compile(r"https?://(www\.)?instagram\.com/[A-Za-z0-9_\.\-/]+", re.I),
    "facebook": re.compile(r"https?://(www\.)?facebook\.com/[A-Za-z0-9_\.\-/]+", re.I),
    "tiktok": re.compile(r"https?://(www\.)?tiktok\.com/[A-Za-z0-9_\.\-/]+", re.I),
    "twitter": re.compile(r"https?://(www\.)?(twitter|x)\.com/[A-Za-z0-9_\.\-/]+", re.I),
    "youtube": re.compile(r"https?://(www\.)?youtube\.com/[A-Za-z0-9_\.\-/]+", re.I),
    "linkedin": re.compile(r"https?://(www\.)?linkedin\.com/[A-Za-z0-9_\.\-/]+", re.I),
    "pinterest": re.compile(r"https?://(www\.)?pinterest\.com/[A-Za-z0-9_\.\-/]+", re.I),
}

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"\+?\d[\d\s().-]{7,}\d")


def safe_text(s: str, limit: int = 400) -> str:
    s = re.sub(r"\s+", " ", s).strip()
    return s[:limit]


def extract_social_links(html: str) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for platform, pattern in SOCIAL_PATTERNS.items():
        for m in pattern.findall(html):
            out.append((platform, m.split("?", 1)[0]))
    # de-dup
    seen = set()
    uniq = []
    for p, url in out:
        key = (p, url.rstrip("/"))
        if key not in seen:
            seen.add(key)
            uniq.append((p, url.rstrip("/")))
    return uniq


def extract_emails_phones(text: str) -> tuple[list[str], list[str]]:
    emails = sorted(set(EMAIL_RE.findall(text)))
    phones = sorted(set(PHONE_RE.findall(text)))
    return emails, phones


def parse_faqs_from_ldjson(html: str) -> list[tuple[str, str]]:
    soup = BeautifulSoup(html, "lxml")
    faqs: list[tuple[str, str]] = []
    for script in soup.find_all("script", {"type": "application/ld+json"}):
        try:
            data = json.loads(script.text)
        except Exception:
            continue
        nodes = data if isinstance(data, list) else [data]
        for node in nodes:
            if isinstance(node, dict) and node.get("@type") == "FAQPage":
                for item in node.get("mainEntity", []) or []:
                    q = item.get("name") or item.get("headline") or ""
                    a = ""
                    accepted = item.get("acceptedAnswer") or {}
                    if isinstance(accepted, dict):
                        a = accepted.get("text", "")
                    faqs.append((safe_text(q, 500), safe_text(a, 800)))
    return faqs


def find_links_by_text(soup: BeautifulSoup, keywords: Iterable[str]) -> dict[str, str]:
    found: dict[str, str] = {}
    for a in soup.find_all("a"):
        label = (a.get_text(" ") or "").strip().lower()
        href = a.get("href") or ""
        for kw in keywords:
            if kw in label:
                found[kw] = href
    return found