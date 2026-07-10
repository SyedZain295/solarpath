"""German solar / heat incentives lookup by postcode region."""

from __future__ import annotations

from datetime import datetime, timezone

BAVARIA_PREFIXES = tuple(str(i) for i in range(80, 98))

PROGRAMS_NATIONAL = [
    {
        "name": "EEG 2023 feed-in tariff",
        "type": "feed_in",
        "status": "active",
        "detail": "Remuneration for exported solar electricity; rates depend on system size and date of commissioning.",
        "url": "https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/ErneuerbareEnergien/EEG/start.html",
    },
    {
        "name": "KfW 270 — Renewable energies (standard)",
        "type": "loan",
        "status": "active",
        "detail": "Low-interest loan for PV, storage, and heat pumps when combined with eligible measures.",
        "url": "https://www.kfw.de/inlandsfoerderung/Privatpersonen/Bestandsimmobilie/Energie/",
    },
    {
        "name": "0% VAT on residential PV (DE)",
        "type": "tax",
        "status": "active",
        "detail": "VAT exemption for typical residential PV supply and installation under applicable rules.",
    },
    {
        "name": "BAFA heat pump bonus (BEG)",
        "type": "grant",
        "status": "check_eligibility",
        "detail": "Federal efficiency grant for heat pumps; combine with PV for lower running costs.",
        "url": "https://www.bafa.de/DE/Energie/Effiziente_Gebaeude/effiziente_gebaeude_node.html",
    },
]

PROGRAMS_BAVARIA = [
    {
        "name": "Bayern Innovativ — energy advisory",
        "type": "advisory",
        "status": "active",
        "detail": "Regional guidance for SMEs and municipalities on renewable projects.",
    },
    {
        "name": "Municipal PV bonus (varies by Gemeinde)",
        "type": "grant",
        "status": "varies",
        "detail": "Some Bavarian municipalities offer one-off bonuses — check your Stadt/Gemeinde website.",
    },
]


def _region_for_postcode(postcode: str) -> str:
    plz = (postcode or "").strip()[:5]
    if len(plz) >= 2 and plz[:2] in BAVARIA_PREFIXES:
        return "Bayern"
    if plz.startswith(("0", "1")):
        return "East Germany"
    if plz.startswith(("2", "3", "4", "5", "6", "7")):
        return "Germany"
    return "Germany"


def incentives_lookup(postcode: str) -> dict:
    plz = (postcode or "").strip()[:5]
    region = _region_for_postcode(plz)
    programs = list(PROGRAMS_NATIONAL)
    if region == "Bayern":
        programs.extend(PROGRAMS_BAVARIA)
    return {
        "ok": True,
        "stub": False,
        "postcode": plz,
        "region": region,
        "programs": programs,
        "count": len(programs),
        "disclaimer": "Program rules change — verify eligibility with KfW, BAFA, or your installer before committing.",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
