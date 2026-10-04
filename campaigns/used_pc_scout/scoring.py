from __future__ import annotations

import re
import unicodedata
from typing import Any


def _norm(value: str) -> str:
    value = unicodedata.normalize("NFKD", value or "")
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", value.lower()).strip()


def parse_brl_price(value: str | None) -> float | None:
    if not value:
        return None
    text = re.sub(r"[^0-9,.]", "", value)
    if not text:
        return None
    if "," in text:
        text = text.replace(".", "").replace(",", ".")
    elif text.count(".") >= 1:
        tail = text.rsplit(".", 1)[-1]
        if len(tail) == 3 or text.count(".") > 1:
            text = text.replace(".", "")
    try:
        return float(text)
    except ValueError:
        return None


_SERVICE_TERMS = (
    "conserto", "assistencia tecnica", "manutencao", "orcamento", "formatacao",
    "reparo de", "tecnico de", "nos resolvemos", "servico de", "limpeza de pc",
)


def is_service_ad(text: str) -> bool:
    normalized = _norm(text)
    return any(term in normalized for term in _SERVICE_TERMS)


_SIGNAL_PATTERNS: tuple[tuple[str, str, float], ...] = (
    (r"\b(?:ryzen\s*5\s*3600)\b", "ryzen_5_3600", 34),
    (r"\b(?:ryzen\s*5\s*(?:2600|3500x|4500|5500|5600g?|5600x))\b", "ryzen_5", 28),
    (r"\b(?:ryzen\s*7\s*\d{4}[a-z]?)\b", "ryzen_7", 36),
    (r"\b(?:i7[-\s]?(?:8700|9700)[a-z]?)\b", "intel_i7_8_9", 34),
    (r"\b(?:i5[-\s]?(?:8400|8500|8600|9400|9500|9600)[a-z]?)\b", "intel_i5_8_9", 27),
    (r"\brx\s*580\b", "rx_580", 34),
    (r"\brx\s*(?:5500|5600|5700|6600|6650)\s*(?:xt)?\b", "radeon_modern", 45),
    (r"\bgtx\s*1060\b", "gtx_1060", 32),
    (r"\bgtx\s*(?:1650|1660)\s*(?:super|ti)?\b", "gtx_16", 39),
    (r"\brtx\s*(?:2060|2070|3050|3060)\b", "rtx", 52),
    (r"\b16\s*gb\b.{0,20}\bddr4\b|\bddr4\b.{0,20}\b16\s*gb\b", "ddr4_16gb", 18),
    (r"\b(?:8|16|32)\s*gb\b.{0,20}\bddr4\b|\bddr4\b.{0,20}\b(?:8|16|32)\s*gb\b", "ddr4", 10),
    (r"\bssd\b", "ssd", 8),
    (r"\bnvme\b|\bm\.2\b", "nvme", 10),
)


def extract_hardware_signals(text: str) -> set[str]:
    normalized = _norm(text)
    return {name for pattern, name, _ in _SIGNAL_PATTERNS if re.search(pattern, normalized, re.I)}


_HIGH_RISK = ("oxid", "agua", "molhou", "queim", "curto", "fumaca", "carboniz")
_LOW_RISK = ("sem hd", "sem ssd", "sem memoria", "sem ram", "gabinete amassado", "tampa quebrada", "cosmetico")
_UNKNOWN_RISK = ("nao liga", "sem teste", "nao testado", "defeito desconhecido", "nao sei o defeito")


def classify_defect_risk(text: str) -> str:
    normalized = _norm(text)
    if any(term in normalized for term in _HIGH_RISK):
        return "high"
    if any(term in normalized for term in _LOW_RISK):
        return "low"
    if any(term in normalized for term in _UNKNOWN_RISK):
        return "unknown"
    return "medium"


_OBSOLETE_TERMS = (
    "pentium 4", "core 2 duo", "core2duo", "athlon 64", "ddr2",
    "lga 775", "socket 775", "c2d",
)


def score_listing(*, title: str, description: str = "", price: float | None) -> dict[str, Any]:
    combined = f"{title} {description}".strip()
    if is_service_ad(combined):
        return {
            "eligible": False,
            "score": 0.0,
            "rejection_reason": "service_ad",
            "signals": [],
            "risk": classify_defect_risk(combined),
        }

    normalized = _norm(combined)
    signals = extract_hardware_signals(combined)
    weights = {name: weight for _, name, weight in _SIGNAL_PATTERNS}
    hardware_score = sum(weights[s] for s in signals)
    if any(term in normalized for term in _OBSOLETE_TERMS):
        hardware_score -= 55

    risk = classify_defect_risk(combined)
    risk_penalty = {"low": 2, "medium": 8, "unknown": 13, "high": 42}[risk]
    price_penalty = 0 if price is None else min(max(price, 0) / 35.0, 45)
    defect_bonus = 5 if any(term in normalized for term in ("com defeito", "nao liga", "para pecas", "retirada de pecas")) else 0
    completeness_bonus = 5 if any(term in normalized for term in ("pc completo", "computador completo", "pc gamer")) else 0

    score = round(hardware_score + defect_bonus + completeness_bonus - risk_penalty - price_penalty, 2)
    eligible = hardware_score > -30 and (price is None or price <= 2500)
    return {
        "eligible": eligible,
        "score": score,
        "rejection_reason": None if eligible else "low_upgrade_value",
        "signals": sorted(signals),
        "risk": risk,
    }
