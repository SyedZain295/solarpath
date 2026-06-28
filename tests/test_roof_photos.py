"""Roof photo upload and installer handoff tests."""

import io

from roof_photo_store import (
    add_photos_to_set,
    can_view_photo,
    create_photo_set,
    get_set_summary,
)


TINY_JPEG = (
    b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
    b"\xff\xd9"
)


class FakeUpload:
    def __init__(self, data: bytes, filename: str = "roof.jpg", content_type: str = "image/jpeg"):
        self._data = data
        self.filename = filename
        self.content_type = content_type

    def read(self):
        return self._data


def test_create_and_upload_roof_photos():
    set_id = create_photo_set(postcode="80331")
    result = add_photos_to_set(set_id, [FakeUpload(TINY_JPEG)])
    assert result["ok"] is True
    summary = get_set_summary(set_id)
    assert summary["count"] == 1
    assert summary["photos"][0]["url"].startswith("/api/roof-photos/")


def test_api_roof_photos_upload(client):
    data = {
        "photos": (io.BytesIO(TINY_JPEG), "roof-front.jpg"),
        "postcode": "80331",
    }
    resp = client.post(
        "/api/roof-photos/upload",
        data=data,
        content_type="multipart/form-data",
    )
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["count"] >= 1
    assert body["set_id"]


def test_roof_photos_in_lead_profile():
    set_id = create_photo_set(postcode="80331")
    add_photos_to_set(set_id, [FakeUpload(TINY_JPEG)])
    summary = get_set_summary(set_id)

    rec = {
        "system_kwp": 8,
        "goals": ["lower_bill"],
        "financials": {"annual_consumption_kwh": 4500},
        "calculator_inputs": {
            "monthly_kwh": 375,
            "owner_status": "owner",
            "housing_type": "detached",
            "installation_timeframe": "asap",
            "roof_photo_set_id": set_id,
            "has_roof_photos": True,
        },
        "roof_photo_set_id": set_id,
        "roof_photos": summary,
    }

    from lead_qualification import build_lead_profile

    profile = build_lead_profile(rec, {"customer_postcode": "80331"}, [], roof_photos=summary)
    assert profile["roof"]["roof_photo_count"] >= 1
    assert "attached" in profile["roof"]["installer_handoff"]


def test_can_view_with_set_id_before_quote():
    set_id = create_photo_set()
    result = add_photos_to_set(set_id, [FakeUpload(TINY_JPEG)])
    photo_id = result["photos"][0]["id"]
    assert can_view_photo(photo_id, set_id=set_id) is True
    assert can_view_photo(photo_id) is False
    assert can_view_photo(photo_id, admin=True) is True
