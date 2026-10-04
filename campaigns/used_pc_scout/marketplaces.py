from __future__ import annotations

import re
from urllib.parse import urlsplit, urlunsplit


def canonical_listing_url(url: str) -> str:
    parts = urlsplit(url.strip())
    return urlunsplit((parts.scheme, parts.netloc, parts.path.rstrip("/"), "", ""))


def marketplace_from_url(url: str) -> str | None:
    host = urlsplit(url).netloc.lower()
    if host.endswith(".olx.com.br") or host == "olx.com.br":
        return "olx"
    if host == "produto.mercadolivre.com.br" or host.endswith(".mercadolivre.com.br"):
        return "mercadolivre"
    return None


def is_listing_url(url: str) -> bool:
    clean = canonical_listing_url(url)
    parts = urlsplit(clean)
    host = parts.netloc.lower()
    path = parts.path
    if host.endswith(".olx.com.br") and "/informatica/computadores-e-desktops/" in path:
        return bool(re.search(r"-\d{8,}$", path))
    if host == "produto.mercadolivre.com.br":
        return bool(re.search(r"/MLB-\d+", path, re.I))
    return False


def discover_listing_urls(hrefs: list[str] | tuple[str, ...]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for href in hrefs:
        if not href or not href.startswith(("http://", "https://")):
            continue
        clean = canonical_listing_url(href)
        if is_listing_url(clean) and clean not in seen:
            seen.add(clean)
            out.append(clean)
    return out


_PRIORITY_TERMS: tuple[tuple[str, int], ...] = (
    ("ryzen", 30),
    ("i5 ", 22),
    ("i5-", 22),
    ("i7 ", 28),
    ("i7-", 28),
    ("rx 580", 28),
    ("rx580", 28),
    ("rx 5", 26),
    ("rx 6", 34),
    ("gtx 1060", 25),
    ("gtx 16", 30),
    ("rtx ", 40),
    ("ddr4", 14),
    ("16gb", 10),
    ("16 gb", 10),
    ("nvme", 10),
    ("ssd", 6),
    ("pc gamer", 5),
    ("com defeito", 8),
    ("não liga", 8),
    ("nao liga", 8),
    ("para peças", 7),
    ("para pecas", 7),
    ("retirada de peças", 7),
    ("retirada de pecas", 7),
)

_LOW_VALUE_TERMS = (
    "pentium 4",
    "core 2 duo",
    "core2duo",
    "ddr2",
    "lga 775",
    "socket 775",
)


def listing_seed_priority(text: str, url: str = "") -> int:
    normalized = re.sub(r"\s+", " ", (text or "").lower()).strip()
    score = sum(weight for term, weight in _PRIORITY_TERMS if term in normalized)
    if any(term in normalized for term in _LOW_VALUE_TERMS):
        score -= 60
    if "sp.olx.com.br" in (url or "").lower():
        score += 3
    return score


def select_listing_urls(
    links: list[tuple[str, str]] | tuple[tuple[str, str], ...],
    *,
    limit: int,
    exploration_slots: int = 2,
) -> list[str]:
    if limit <= 0:
        return []

    best_by_url: dict[str, tuple[int, str]] = {}
    for href, label in links:
        if not href or not href.startswith(("http://", "https://")):
            continue
        clean = canonical_listing_url(href)
        if not is_listing_url(clean):
            continue
        score = listing_seed_priority(label, clean)
        current = best_by_url.get(clean)
        if current is None or score > current[0]:
            best_by_url[clean] = (score, label)

    ranked = sorted(
        best_by_url.items(),
        key=lambda pair: (-pair[1][0], pair[0]),
    )
    if len(ranked) <= limit:
        return [url for url, _ in ranked]

    explore = max(0, min(exploration_slots, limit))
    exploit_count = limit - explore
    chosen = ranked[:exploit_count]
    remaining = ranked[exploit_count:]

    if explore:
        exploration = sorted(
            remaining,
            key=lambda pair: (pair[1][0], pair[0]),
        )[:explore]
        chosen.extend(exploration)

    return [url for url, _ in chosen]
