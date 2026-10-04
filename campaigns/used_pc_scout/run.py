from __future__ import annotations

import json
import os
from pathlib import Path

from campaigns.used_pc_scout.scout import UsedPcScoutSpider


def _render_markdown(items: list[dict], stats: dict) -> str:
    lines = [
        "# Used PC salvage scout",
        "",
        f"- candidates: {len(items)}",
        f"- requests: {stats.get('requests_count', 0)}",
        f"- failedRequests: {stats.get('failed_requests_count', 0)}",
        f"- blockedRequests: {stats.get('blocked_requests_count', 0)}",
        f"- robotsDisallowed: {stats.get('robots_disallowed_count', 0)}",
        "",
        "| # | score | preço | risco | sinais | anúncio |",
        "|---:|---:|---:|---|---|---|",
    ]
    for idx, item in enumerate(items[:100], 1):
        price = item.get("price_brl")
        price_text = f"R$ {price:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if price is not None else "?"
        title = str(item.get("title", "")).replace("|", "\\|")
        signals = ", ".join(item.get("signals") or []).replace("|", "\\|")
        lines.append(
            f"| {idx} | {item.get('score')} | {price_text} | {item.get('risk')} | {signals} | "
            f"[{title}]({item.get('url')}) |"
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    out_dir = Path(os.getenv("SCOUT_OUTPUT_DIR", "artifacts/used-pc-scout"))
    crawl_dir = Path(os.getenv("SCOUT_CRAWL_DIR", ".crawl/used-pc-scout"))
    out_dir.mkdir(parents=True, exist_ok=True)
    crawl_dir.mkdir(parents=True, exist_ok=True)

    result = UsedPcScoutSpider(crawldir=crawl_dir, interval=120.0).start()
    items = sorted(
        list(result.items),
        key=lambda item: (float(item.get("score", 0)), -float(item.get("price_brl") or 10**9)),
        reverse=True,
    )
    stats = result.stats.to_dict()

    (out_dir / "candidates.json").write_text(
        json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (out_dir / "stats.json").write_text(
        json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    report = _render_markdown(items, stats)
    (out_dir / "report.md").write_text(report, encoding="utf-8")

    print(report)
    print("STATS_JSON=" + json.dumps(stats, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
