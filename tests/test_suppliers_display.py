def test_directory_listings_hide_placeholder_contact(client):
    r = client.get("/api/suppliers?limit=500")
    assert r.status_code == 200
    payload = r.get_json()
    items = payload.get("items")
    if items is None:
        items = payload if isinstance(payload, list) else []
    directory = [s for s in items if s.get("is_directory_listing")]
    assert len(directory) >= 1
    for s in directory:
        assert s.get("display_phone") is None
        assert s.get("display_email") is None
        assert s.get("display_rating") is None
        assert s.get("quality_score") is None


def test_munich_search_includes_real_osm_contact(client):
    r = client.get("/api/suppliers?city=München&radius_km=50&limit=10")
    assert r.status_code == 200
    items = r.get_json().get("items") or []
    with_contact = [s for s in items if s.get("display_phone") or s.get("display_website")]
    assert len(with_contact) >= 1
    top = items[0]
    assert top.get("is_directory_listing") is False
