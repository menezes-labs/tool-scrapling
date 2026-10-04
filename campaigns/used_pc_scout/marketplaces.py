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
