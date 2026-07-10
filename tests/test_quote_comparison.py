"""Tests for quote comparison engine and APIs."""

from quote_comparison import compare_quotes, normalize_quote
from quote_parse_stub import parse_quotes_from_text, split_quote_texts

SAMPLE_A = """SolarTech München GmbH
Photovoltaik Komplettanlage 8,4 kWp
Gesamtpreis: 18.450,00 EUR brutto
Module: 20× Trina Vertex 420 Wp
Wechselrichter: Fronius Primo 8.0 kW
Speicher: 10,2 kWh BYD
Jahresertrag ca. 8.900 kWh
Garantie: 25 Jahre Module
Enthalten: Montage, Gerüst, Netzanmeldung, MaStR, Monitoring
Gültig 30 Tage"""

SAMPLE_B = """BayerSolar GmbH
Angebot Nr. 9921
8,4 kWp PV-Anlage
Gesamtpreis: 15.200,00 EUR
Module: 20× JA Solar 420 Wp
Wechselrichter SMA Sunny Tripower 6.0 kW
Jahresertrag 8.500 kWh
Garantie: 12 Jahre Module
Montage inklusive
Gültig 7 Tage"""


def test_split_quote_texts():
    combined = SAMPLE_A + "\n---\n" + SAMPLE_B
    parts = split_quote_texts(combined)
    assert len(parts) == 2


def test_parse_quotes_from_text_multi():
    combined = SAMPLE_A + "\n---\n" + SAMPLE_B
    quotes = parse_quotes_from_text(combined)
    assert len(quotes) == 2
    assert quotes[0]["total_eur"] == 18450
    assert quotes[1]["total_eur"] == 15200


def test_compare_quotes_warnings():
    q1 = parse_quotes_from_text(SAMPLE_A)[0]
    q2 = parse_quotes_from_text(SAMPLE_B)[0]
    result = compare_quotes([q1, q2])
    assert result["summary"]["count"] == 2
    assert "rows" in result
    low_quote = result["quotes"][1]
    codes = {w["code"] for w in low_quote["warnings"]}
    assert "no_grid" in codes
    assert "short_validity" in codes


def test_normalize_includes_mounting():
    q = normalize_quote({"includes_mounting": True, "total_eur": 10000, "kwp": 8})
    assert q["checks"]["includes_mounting"] is True


def test_api_compare_quotes(client):
    q1 = parse_quotes_from_text(SAMPLE_A)[0]
    q2 = parse_quotes_from_text(SAMPLE_B)[0]
    r = client.post("/api/quotes/compare", json={"quotes": [q1, q2]})
    assert r.status_code == 200
    data = r.get_json()
    assert data["summary"]["count"] == 2
    assert len(data["quotes"][0]["warnings"]) >= 0


def test_api_parse_text_multi(client):
    combined = SAMPLE_A + "\n---\n" + SAMPLE_B
    r = client.post("/api/quotes/parse-text", json={"text": combined, "multi": True})
    assert r.status_code == 200
    data = r.get_json()
    assert data["count"] == 2
