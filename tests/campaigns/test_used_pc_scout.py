from pathlib import Path

from campaigns.used_pc_scout.scoring import (
    classify_defect_risk,
    extract_hardware_signals,
    is_service_ad,
    parse_brl_price,
    score_listing,
)


def test_parse_brl_price_handles_marketplace_formats():
    assert parse_brl_price("R$ 425") == 425.0
    assert parse_brl_price("R$ 1.570") == 1570.0
    assert parse_brl_price("R$ 1.500,00") == 1500.0


def test_service_ads_are_rejected():
    assert is_service_ad("Conserto de computador e notebook - assistência técnica") is True
    assert is_service_ad("PC gamer com defeito, não liga, vendo para peças") is False


def test_hardware_signals_extract_upgrade_parts():
    signals = extract_hardware_signals("Ryzen 5 3600, RX 580 8GB, 16GB DDR4, SSD 480GB")
    assert "ryzen_5_3600" in signals
    assert "rx_580" in signals
    assert "ddr4_16gb" in signals
    assert "ssd" in signals


def test_defect_risk_distinguishes_unknown_from_catastrophic():
    assert classify_defect_risk("PC não liga, não sei o defeito") == "unknown"
    assert classify_defect_risk("placa oxidada por água, queimou e entrou em curto") == "high"
    assert classify_defect_risk("sem HD e sem memória, gabinete amassado") == "low"


def test_good_donor_pc_beats_old_junk_at_same_price():
    donor = score_listing(
        title="PC gamer com defeito Ryzen 5 3600 RX 580 8GB 16GB DDR4 SSD 480GB",
        description="não liga, vendo no estado para retirada de peças",
        price=425.0,
    )
    junk = score_listing(
        title="Computador Pentium 4 com defeito",
        description="não liga, sem garantia",
        price=425.0,
    )
    assert donor["eligible"] is True
    assert donor["score"] > junk["score"] + 40


def test_service_listing_is_ineligible_even_when_cheap():
    result = score_listing(
        title="Conserto PC gamer - não liga? nós resolvemos",
        description="assistência técnica em placas de vídeo",
        price=50.0,
    )
    assert result["eligible"] is False
    assert result["rejection_reason"] == "service_ad"


from campaigns.used_pc_scout.marketplaces import discover_listing_urls, marketplace_from_url


def test_marketplace_url_discovery_keeps_real_listing_links_and_dedupes():
    hrefs = [
        "https://sp.olx.com.br/sao-paulo-e-regiao/informatica/computadores-e-desktops/pc-gamer-com-defeito-1530710625?lis=listing_1000",
        "https://sp.olx.com.br/sao-paulo-e-regiao/informatica/computadores-e-desktops/pc-gamer-com-defeito-1530710625",
        "https://produto.mercadolivre.com.br/MLB-1234567890-pc-gamer-com-defeito-_JM#polycard_client=search-nordic",
        "https://www.olx.com.br/anuncios/pc-nao-liga",
        "https://lista.mercadolivre.com.br/pc-gamer-com-defeito",
    ]
    urls = discover_listing_urls(hrefs)
    assert urls == [
        "https://sp.olx.com.br/sao-paulo-e-regiao/informatica/computadores-e-desktops/pc-gamer-com-defeito-1530710625",
        "https://produto.mercadolivre.com.br/MLB-1234567890-pc-gamer-com-defeito-_JM",
    ]


def test_marketplace_from_url():
    assert marketplace_from_url("https://sp.olx.com.br/x/informatica/computadores-e-desktops/foo-1234567890") == "olx"
    assert marketplace_from_url("https://produto.mercadolivre.com.br/MLB-123-foo-_JM") == "mercadolivre"


def test_shared_codebuild_job_invokes_campaign_as_module():
    repo_root = Path(__file__).resolve().parents[2]
    job = (repo_root / ".codebuild" / "jobs" / "used-pc-scout.sh").read_text(encoding="utf-8")
    assert "python -m campaigns.used_pc_scout.run" in job
    assert "python campaigns/used_pc_scout/run.py" not in job


from campaigns.used_pc_scout.marketplaces import (
    listing_seed_priority,
    select_listing_urls,
)
from campaigns.used_pc_scout.scout import UsedPcScoutSpider


def test_seed_priority_prefers_useful_donor_hardware_over_generic_pc():
    useful = listing_seed_priority(
        "PC gamer com defeito Ryzen 5 3600 RX 580 16GB DDR4 R$ 450",
        "https://sp.olx.com.br/x/informatica/computadores-e-desktops/pc-ryzen-rx580-1530710625",
    )
    generic = listing_seed_priority(
        "Computador com defeito R$ 450",
        "https://sp.olx.com.br/x/informatica/computadores-e-desktops/computador-defeito-1530710626",
    )
    assert useful > generic


def test_select_listing_urls_caps_fanout_but_keeps_exploration_slots():
    links = [
        (
            f"https://sp.olx.com.br/x/informatica/computadores-e-desktops/generico-{1530710700 + i}",
            f"Computador com defeito número {i} R$ {100 + i}",
        )
        for i in range(12)
    ]
    links.extend(
        [
            (
                "https://sp.olx.com.br/x/informatica/computadores-e-desktops/ryzen-rx580-1530710998",
                "Ryzen 5 3600 RX 580 16GB DDR4 com defeito R$ 500",
            ),
            (
                "https://sp.olx.com.br/x/informatica/computadores-e-desktops/i5-gtx1660-1530710999",
                "i5 9400 GTX 1660 16GB DDR4 para peças R$ 650",
            ),
        ]
    )

    selected = select_listing_urls(links, limit=6, exploration_slots=2)

    assert len(selected) == 6
    assert selected[0].endswith("ryzen-rx580-1530710998")
    assert selected[1].endswith("i5-gtx1660-1530710999")
    assert any("generico-" in url for url in selected[-2:])


def test_spider_is_rate_limit_conservative_by_default():
    assert UsedPcScoutSpider.concurrent_requests == 2
    assert UsedPcScoutSpider.concurrent_requests_per_domain == 1
    assert UsedPcScoutSpider.max_blocked_retries == 0
    assert UsedPcScoutSpider.download_delay >= 2.0
    assert UsedPcScoutSpider.autothrottle_max_delay >= 60.0


def test_seed_priority_prefers_cheap_donor_when_hardware_is_equal():
    cheap = listing_seed_priority(
        "Ryzen 5 3600 RX 580 16GB DDR4 usado R$ 350",
        "https://sp.olx.com.br/x/informatica/computadores-e-desktops/cheap-1530711201",
    )
    expensive = listing_seed_priority(
        "Ryzen 5 3600 RX 580 16GB DDR4 usado R$ 2.500",
        "https://sp.olx.com.br/x/informatica/computadores-e-desktops/expensive-1530711202",
    )
    assert cheap > expensive + 30


def test_listing_item_keeps_description_excerpt_for_human_review():
    sample = "Ryzen 5 5500, 16GB DDR4, SSD NVMe 512GB. Placa de vídeo com defeito."
    excerpt = UsedPcScoutSpider._description_excerpt(sample)
    assert "Ryzen 5 5500" in excerpt
    assert "Placa de vídeo com defeito" in excerpt
    assert len(excerpt) <= 2000
