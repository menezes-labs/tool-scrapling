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
