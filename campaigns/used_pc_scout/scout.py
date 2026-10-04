from __future__ import annotations

import os
import re
from typing import AsyncGenerator

from scrapling.fetchers import FetcherSession
from scrapling.spiders import Request, Response, Spider

from campaigns.used_pc_scout.marketplaces import marketplace_from_url, select_listing_urls
from campaigns.used_pc_scout.scoring import parse_brl_price, score_listing


DEFAULT_SEEDS = [
    "https://www.olx.com.br/anuncios/pc-nao-liga",
    "https://www.olx.com.br/anuncios/pc-com-defeito",
    "https://www.olx.com.br/anuncios/computador-com-defeito",
    "https://www.olx.com.br/anuncios/pc-gamer-com-defeito",
    "https://www.olx.com.br/anuncios/computador-para-retirar-pecas",
    "https://www.olx.com.br/anuncios/pc-gamer-para-pecas",
    "https://www.olx.com.br/anuncios/pc-gamer-usado",
    "https://www.olx.com.br/anuncios/computador-gamer-usado",
    "https://www.olx.com.br/anuncios/kit-pc-gamer",
    "https://www.olx.com.br/anuncios/pc-gamer-barato",
    "https://www.olx.com.br/anuncios/computador-usado-barato",
    "https://lista.mercadolivre.com.br/pc-gamer-com-defeito-usado",
    "https://lista.mercadolivre.com.br/pc-gamer-usado",
    "https://lista.mercadolivre.com.br/kit-pc-gamer-usado",
    "https://lista.mercadolivre.com.br/computador-com-defeito-usado",
    "https://lista.mercadolivre.com.br/pc-nao-liga-usado",
]

_PRICE_RE = re.compile(r"R\$\s*([0-9][0-9.]*?(?:,[0-9]{2})?)(?:\s|$)")
_NEXT_WORDS = ("proxima", "próxima", "seguinte", "next")


class UsedPcScoutSpider(Spider):
    name = "used-pc-salvage-scout"
    allowed_domains = {"olx.com.br", "mercadolivre.com.br"}
    robots_txt_obey = True
    concurrent_requests = 2
    concurrent_requests_per_domain = 1
    download_delay = 2.5
    autothrottle_enabled = True
    autothrottle_start_delay = 2.5
    autothrottle_max_delay = 60.0
    autothrottle_target_concurrency = 0.75
    max_blocked_retries = 0

    def __init__(self, *args, **kwargs):
        self.max_seed_pages = int(os.getenv("SCOUT_MAX_SEED_PAGES", "10"))
        self.max_price = float(os.getenv("SCOUT_MAX_PRICE", "1200"))
        self.min_score = float(os.getenv("SCOUT_MIN_SCORE", "5"))
        self.details_per_seed = int(os.getenv("SCOUT_DETAILS_PER_SEED", "8"))
        self.exploration_slots = int(os.getenv("SCOUT_EXPLORATION_SLOTS", "2"))
        custom_seeds = os.getenv("SCOUT_SEEDS", "").strip()
        self.start_urls = [x.strip() for x in custom_seeds.split(",") if x.strip()] or list(DEFAULT_SEEDS)
        super().__init__(*args, **kwargs)

    def configure_sessions(self, manager):
        manager.add("fast", FetcherSession(impersonate="chrome"))

    async def start_requests(self) -> AsyncGenerator[Request, None]:
        for url in self.start_urls:
            yield Request(url, sid="fast", callback=self.parse_seed, meta={"seed_depth": 1})

    async def parse(self, response: Response):
        async for item in self.parse_seed(response):
            yield item

    async def parse_seed(self, response: Response):
        candidates: list[tuple[str, str]] = []
        for link in response.css("a"):
            href = link.attrib.get("href")
            if not href:
                continue
            url = response.urljoin(str(href))
            label = str(link.get_all_text(" ", strip=True))
            candidates.append((url, label))

        selected_urls = select_listing_urls(
            candidates,
            limit=self.details_per_seed,
            exploration_slots=self.exploration_slots,
        )
        for url in selected_urls:
            yield Request(
                url,
                sid="fast",
                callback=self.parse_listing,
                priority=10,
                meta={"selected_from_seed": response.url},
            )

        request_meta = response.request.meta if response.request else {}
        depth = int(request_meta.get("seed_depth", 1))
        if depth >= self.max_seed_pages:
            return

        for link in response.css("a"):
            href = link.attrib.get("href")
            if not href:
                continue
            label = str(link.get_all_text(" ", strip=True)).lower()
            rel = str(link.attrib.get("rel", "")).lower()
            if rel == "next" or any(word in label for word in _NEXT_WORDS):
                yield response.follow(
                    str(href),
                    sid="fast",
                    callback=self.parse_seed,
                    meta={"seed_depth": depth + 1},
                    priority=-10,
                )
                return

    async def parse_listing(self, response: Response):
        full_text = str(response.get_all_text(" ", strip=True))
        title = self._first_text(response, ("h1", "meta[property='og:title']")) or full_text[:180]
        description = self._first_text(
            response,
            (
                "[data-testid='ad-description']",
                ".ui-pdp-description__content",
                "[itemprop='description']",
                "article",
            ),
        )
        description = description or full_text[:8000]
        price = self._extract_price(response, full_text)
        score = score_listing(title=title, description=description, price=price)

        yield {
            "marketplace": marketplace_from_url(response.url),
            "url": response.url,
            "title": title[:300],
            "description_excerpt": self._description_excerpt(description),
            "price_brl": price,
            "risk": score["risk"],
            "signals": score["signals"],
            "score": score["score"],
            "eligible": score["eligible"],
            "rejection_reason": score["rejection_reason"],
        }

    async def on_scraped_item(self, item):
        if not item.get("eligible"):
            return None
        price = item.get("price_brl")
        if price is None or price > self.max_price:
            return None
        if float(item.get("score", 0)) < self.min_score:
            return None
        return item

    @staticmethod
    def _description_excerpt(value: str) -> str:
        return re.sub(r"\s+", " ", value or "").strip()[:2000]

    @staticmethod
    def _first_text(response: Response, selectors: tuple[str, ...]) -> str:
        for selector in selectors:
            nodes = response.css(selector)
            if not nodes:
                continue
            node = nodes[0]
            if node.tag == "meta":
                content = node.attrib.get("content")
                if content:
                    return str(content).strip()
            text = str(node.get_all_text(" ", strip=True)).strip()
            if text:
                return text
        return ""

    @staticmethod
    def _extract_price(response: Response, full_text: str) -> float | None:
        for selector in (
            "meta[itemprop='price']",
            "meta[property='product:price:amount']",
            "meta[property='og:price:amount']",
        ):
            nodes = response.css(selector)
            if nodes:
                raw = nodes[0].attrib.get("content")
                price = parse_brl_price(str(raw)) if raw is not None else None
                if price is not None:
                    return price

        match = _PRICE_RE.search(full_text)
        return parse_brl_price(match.group(1)) if match else None
