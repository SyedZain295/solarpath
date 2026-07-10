"""Solar Decision Report PDF – styled layout for installer-ready export."""

from __future__ import annotations

import re
from datetime import datetime
from io import BytesIO
from locale import LC_TIME, setlocale

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from i18n import translate

TEAL = colors.HexColor("#0f766e")
TEAL_DARK = colors.HexColor("#134e4a")
TEAL_LIGHT = colors.HexColor("#ccfbf1")
MINT = colors.HexColor("#99f6e4")
MINT_SOFT = colors.HexColor("#d1fae5")
PAGE_TINT = colors.HexColor("#f1f5f9")
SLATE = colors.HexColor("#1e293b")
SLATE_MUTED = colors.HexColor("#475569")
WHITE = colors.white
ROW_STRIPE = [MINT_SOFT, TEAL_LIGHT]
BORDER = colors.HexColor("#94a3b8")
BORDER_LIGHT = colors.HexColor("#cbd5e1")


def _safe(text) -> str:
    if text is None:
        return ""
    s = str(text).replace("\n", " ").strip()
    s = re.sub(r"[\U0001F300-\U0001FAFF\U00002700-\U000027BF]", "", s)
    return re.sub(r"\s+", " ", s)


def _rich(text) -> str:
    """ReportLab-safe rich text (subscripts, etc.)."""
    s = _safe(text)
    s = s.replace("CO₂", "CO<sub>2</sub>")
    return s


def _euro(value) -> str:
    if value is None or value == "":
        return "—"
    try:
        n = float(value)
        formatted = f"{abs(int(round(n))):,}".replace(",", ".")
        prefix = "−" if n < 0 else ""
        return f"{prefix}€{formatted}"
    except (TypeError, ValueError):
        return "—"


def _num(value, suffix="") -> str:
    if value is None or value == "":
        return "—"
    try:
        n = float(value)
        if n == int(n):
            return f"{int(n)}{suffix}"
        return f"{n:.1f}{suffix}"
    except (TypeError, ValueError):
        return "—"


def _readiness_color(score: int) -> colors.Color:
    s = max(0, min(100, int(score or 0)))
    if s >= 75:
        return colors.HexColor("#059669")
    if s >= 50:
        return colors.HexColor("#d97706")
    return colors.HexColor("#dc2626")


def _pkg_financials(pkg: dict) -> dict:
    fm = pkg.get("financial_model") or {}
    summary = fm.get("summary") or {}
    fin = pkg.get("financials") or {}
    proj = fm.get("projection_10yr") or {}
    return {
        "cost": (
            pkg.get("upfront_cost")
            or summary.get("system_cost_typical")
            or fin.get("system_cost_typical")
            or fm.get("upfront_cost")
        ),
        "cost_range": pkg.get("upfront_cost_range"),
        "payback": (
            pkg.get("payback_years")
            or summary.get("payback_years")
            or fin.get("payback_years")
            or fm.get("payback_years")
        ),
        "monthly_savings": (
            pkg.get("monthly_savings")
            or summary.get("monthly_savings")
            or fin.get("monthly_savings")
            or fm.get("monthly_savings")
        ),
        "savings_10yr": (
            pkg.get("savings_10yr") or summary.get("savings_10yr") or fin.get("savings_10yr") or proj.get("net_benefit")
        ),
        "production": pkg.get("annual_production_kwh") or fm.get("annual_production_kwh"),
        "co2": pkg.get("co2_reduction_tonnes") or fin.get("co2_reduction_tonnes"),
    }


def _styles():
    base = getSampleStyleSheet()
    return {
        "brand": ParagraphStyle(
            "Brand",
            parent=base["Normal"],
            fontSize=9,
            textColor=colors.HexColor("#ccfbf1"),
            leading=11,
            spaceAfter=2,
        ),
        "title": ParagraphStyle(
            "Title",
            parent=base["Heading1"],
            fontSize=22,
            leading=26,
            textColor=WHITE,
            spaceAfter=0,
        ),
        "section": ParagraphStyle(
            "Section",
            parent=base["Heading2"],
            fontSize=12,
            leading=15,
            textColor=TEAL_DARK,
            spaceBefore=0,
            spaceAfter=6,
            fontName="Helvetica-Bold",
        ),
        "body": ParagraphStyle(
            "Body",
            parent=base["Normal"],
            fontSize=10,
            leading=14,
            textColor=SLATE,
            spaceAfter=6,
        ),
        "muted": ParagraphStyle(
            "Muted",
            parent=base["Normal"],
            fontSize=9,
            leading=12,
            textColor=SLATE_MUTED,
            spaceAfter=4,
        ),
        "small": ParagraphStyle(
            "Small",
            parent=base["Normal"],
            fontSize=8.5,
            leading=11,
            textColor=SLATE_MUTED,
        ),
        "metric_label": ParagraphStyle(
            "MetricLabel",
            parent=base["Normal"],
            fontSize=8,
            leading=10,
            textColor=SLATE_MUTED,
        ),
        "metric_value": ParagraphStyle(
            "MetricValue",
            parent=base["Normal"],
            fontSize=11,
            leading=13,
            textColor=TEAL_DARK,
            fontName="Helvetica-Bold",
        ),
        "score_num": ParagraphStyle(
            "ScoreNum",
            parent=base["Normal"],
            fontSize=28,
            leading=30,
            fontName="Helvetica-Bold",
            alignment=1,
        ),
        "score_label": ParagraphStyle(
            "ScoreLabel",
            parent=base["Normal"],
            fontSize=9,
            leading=11,
            alignment=1,
            fontName="Helvetica-Bold",
        ),
    }


def _t(lang: str, key: str, default: str | None = None) -> str:
    return translate(lang, key, default or key)


def _header_block(st, lang: str) -> list:
    bar = Table(
        [[Paragraph("Solar Path", st["brand"]), Paragraph(_t(lang, "pdf.title"), st["title"])]],
        colWidths=[4 * cm, 12 * cm],
    )
    bar.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), TEAL),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 14),
                ("RIGHTPADDING", (0, 0), (-1, -1), 14),
                ("TOPPADDING", (0, 0), (-1, -1), 14),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
            ]
        )
    )
    return [bar, Spacer(1, 0.45 * cm)]


def _binding_notice_block(st, lang: str) -> list:
    text = _t(
        lang,
        "pdf.not_binding",
        "NOT A BINDING QUOTE — illustrative pre-assessment only. Final price, yield, and equipment require a site survey and installer offer.",
    )
    notice_style = ParagraphStyle(
        "BindingNotice",
        parent=st["body"],
        textColor=colors.HexColor("#78350f"),
        fontName="Helvetica-Bold",
    )
    box = Table([[Paragraph(text, notice_style)]], colWidths=[16 * cm])
    box.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fde68a")),
                ("BOX", (0, 0), (-1, -1), 1.5, colors.HexColor("#d97706")),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    return [box, Spacer(1, 0.35 * cm)]


def _meta_block(rec: dict, customer: dict, st, lang: str) -> list:
    loc = _safe(rec.get("location", {}).get("name"))
    pvgis = rec.get("pvgis") or {}
    data_src = "PVGIS" if pvgis else _t(lang, "pdf.regional_estimate", "Regional estimate")
    rows = [
        [Paragraph(f"<b>{_t(lang, 'pdf.location')}</b>", st["muted"]), Paragraph(loc or "—", st["body"])],
        [
            Paragraph(f"<b>{_t(lang, 'pdf.date')}</b>", st["muted"]),
            Paragraph(datetime.now().strftime("%d %B %Y"), st["body"]),
        ],
        [Paragraph(f"<b>{_t(lang, 'pdf.data_source')}</b>", st["muted"]), Paragraph(data_src, st["body"])],
    ]
    if customer.get("name"):
        rows.append(
            [
                Paragraph(f"<b>{_t(lang, 'pdf.prepared_for')}</b>", st["muted"]),
                Paragraph(_safe(customer["name"]), st["body"]),
            ]
        )
    table = Table(rows, colWidths=[3.2 * cm, 12.8 * cm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), MINT),
                ("BACKGROUND", (1, 0), (1, -1), TEAL_LIGHT),
                ("BOX", (0, 0), (-1, -1), 1, TEAL),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, BORDER_LIGHT),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    return [table, Spacer(1, 0.5 * cm)]


def _section_title(title: str, st) -> list:
    bar_style = ParagraphStyle(
        "SectionBar",
        parent=st["section"],
        textColor=WHITE,
        fontSize=11,
    )
    wrap = Table([[Paragraph(title, bar_style)]], colWidths=[16 * cm])
    wrap.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), TEAL_DARK),
                ("LINEBEFORE", (0, 0), (0, -1), 4, colors.HexColor("#14b8a6")),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    return [Spacer(1, 0.15 * cm), wrap, Spacer(1, 0.2 * cm)]


def _keep_section(title: str, body: list, st, trailing_spacer: float = 0.35) -> list:
    """Keep section heading and body on the same page when possible."""
    block = _section_title(title, st) + body
    items = [KeepTogether(block)]
    if trailing_spacer:
        items.append(Spacer(1, trailing_spacer * cm))
    return items


def _readiness_block(readiness: dict, st, lang: str) -> list:
    if not readiness.get("label"):
        return []
    score = int(readiness.get("score") or 0)
    score_color = _readiness_color(score)
    score_style = ParagraphStyle(
        "ScoreDynamic",
        parent=st["score_num"],
        textColor=score_color,
    )
    score_cell = Table(
        [
            [Paragraph(str(score), score_style)],
            [Paragraph(_t(lang, "pdf.index_suffix", "index"), st["muted"])],
        ],
        colWidths=[2.4 * cm],
    )
    score_cell.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), TEAL_LIGHT),
                ("BOX", (0, 0), (-1, -1), 1.5, score_color),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    detail = Table(
        [
            [
                score_cell,
                Paragraph(
                    f"<b>{_safe(readiness.get('label'))}</b><br/>{_safe(readiness.get('summary', ''))}",
                    st["body"],
                ),
            ],
        ],
        colWidths=[2.8 * cm, 13.2 * cm],
    )
    detail.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), MINT_SOFT),
                ("BOX", (0, 0), (-1, -1), 1, TEAL),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    items = []
    items.extend(_section_title(_t(lang, "pdf.suitability"), st))
    items.append(detail)
    factors = readiness.get("factors") or []
    if factors:
        factor_rows = []
        for f in factors[:4]:
            impact = f.get("impact", "neutral")
            tag = {
                "positive": _t(lang, "pdf.impact_good"),
                "negative": _t(lang, "pdf.impact_review"),
                "neutral": _t(lang, "pdf.impact_note"),
            }.get(impact, _t(lang, "pdf.impact_note"))
            factor_rows.append(
                [
                    Paragraph(f"<b>{_safe(f.get('factor'))}</b>", st["body"]),
                    Paragraph(f"{tag} · {_safe(f.get('detail'))}", st["muted"]),
                ]
            )
        ft = Table(factor_rows, colWidths=[4.5 * cm, 11.5 * cm])
        ft.setStyle(
            TableStyle(
                [
                    ("ROWBACKGROUNDS", (0, 0), (-1, -1), ROW_STRIPE),
                    ("BACKGROUND", (0, 0), (0, -1), MINT),
                    ("BOX", (0, 0), (-1, -1), 1, TEAL),
                    ("INNERGRID", (0, 0), (-1, -1), 0.5, BORDER_LIGHT),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        items.append(Spacer(1, 0.2 * cm))
        items.append(ft)
    items.append(Spacer(1, 0.35 * cm))
    return [KeepTogether(items)]


def _why_block(rec: dict, st, lang: str) -> list:
    why = _safe(rec.get("why_explanation", ""))
    bullets = [_safe(b).replace("**", "") for b in rec.get("why_recommend", []) if b]
    if not why and not bullets:
        return []
    items = _section_title(_t(lang, "pdf.why"), st)
    if why:
        items.append(Paragraph(why, st["body"]))
    if bullets:
        for b in bullets[:4]:
            items.append(Paragraph(f"• {b}", st["body"]))
    items.append(Spacer(1, 0.35 * cm))
    return [KeepTogether(items)]


def _packages_table(pkgs: dict, st, lang: str) -> list:
    if not pkgs:
        return []
    rows = [
        [
            _t(lang, "pdf.pkg_col"),
            _t(lang, "pdf.system_col"),
            _t(lang, "pdf.battery_col"),
            _t(lang, "pdf.cost_col"),
            _t(lang, "pdf.payback_col"),
        ]
    ]
    for _key, pkg in pkgs.items():
        fin = _pkg_financials(pkg)
        cost = fin["cost_range"] or _euro(fin["cost"])
        rows.append(
            [
                _safe(pkg.get("label", _key)),
                f"{_num(pkg.get('system_kwp'))} kWp",
                f"{_num(pkg.get('battery_kwh'))} kWh" if pkg.get("battery_kwh") else _t(lang, "pdf.none"),
                cost,
                f"{_num(fin['payback'])} yr" if fin["payback"] not in (None, "") else "—",
            ]
        )
    table = Table(rows, colWidths=[4.2 * cm, 2.6 * cm, 2.4 * cm, 3.4 * cm, 3.4 * cm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), TEAL),
                ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), ROW_STRIPE),
                ("BOX", (0, 0), (-1, -1), 1, TEAL),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, BORDER_LIGHT),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return _keep_section(_t(lang, "pdf.packages"), [table], st)


def _scenarios_table(scenarios: list, disclaimer: str, st, lang: str) -> list:
    if not scenarios:
        return []
    rows = [[_t(lang, "pdf.scenario_col"), _t(lang, "pdf.payback_col"), _t(lang, "pdf.ten_year_col")]]
    for s in scenarios:
        rows.append(
            [
                _safe(s.get("label", "")),
                f"{_num(s.get('payback_years'))} yr",
                _euro(s.get("ten_year_net_eur")),
            ]
        )
    table = Table(rows, colWidths=[6 * cm, 4 * cm, 6 * cm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), TEAL_DARK),
                ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), ROW_STRIPE),
                ("BOX", (0, 0), (-1, -1), 1, TEAL_DARK),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, BORDER_LIGHT),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    body = [table]
    if disclaimer:
        body.extend([Spacer(1, 0.15 * cm), Paragraph(_safe(disclaimer), st["small"])])
    return _keep_section(_t(lang, "pdf.scenarios"), body, st)


def _metric_cards(metrics: list, st) -> Table:
    rows = []
    for i in range(0, len(metrics), 2):
        left_label, left_val = metrics[i]
        if i + 1 < len(metrics):
            right_label, right_val = metrics[i + 1]
        else:
            right_label, right_val = "", ""
        rows.append(
            [
                Paragraph(_rich(left_label), st["metric_label"]),
                Paragraph(_safe(left_val), st["metric_value"]),
                Paragraph(_rich(right_label), st["metric_label"]) if right_label else "",
                Paragraph(_safe(right_val), st["metric_value"]) if right_label else "",
            ]
        )
    table = Table(rows, colWidths=[4.2 * cm, 3.8 * cm, 4.2 * cm, 3.8 * cm], hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), TEAL_LIGHT),
                ("BOX", (0, 0), (-1, -1), 1, TEAL),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, BORDER_LIGHT),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("ROWBACKGROUNDS", (0, 0), (-1, -1), ROW_STRIPE),
            ]
        )
    )
    return table


def _financial_block(rec: dict, pkg: dict, st, lang: str) -> list:
    fin = _pkg_financials(pkg)
    root_fin = rec.get("financials") or {}
    cost_min = root_fin.get("system_cost_min")
    cost_max = root_fin.get("system_cost_max")
    cost_typical = fin["cost"] or root_fin.get("system_cost_typical")
    if cost_min and cost_max:
        cost_text = f"{_euro(cost_min)} – {_euro(cost_max)}"
    else:
        cost_text = fin["cost_range"] or _euro(cost_typical)

    production = pkg.get("annual_production_kwh") or rec.get("annual_production_kwh") or 0
    battery = pkg.get("battery_kwh") or rec.get("battery_kwh") or 0
    co2 = fin["co2"] or root_fin.get("co2_reduction_tonnes") or 0

    metrics = [
        (_t(lang, "pdf.system_size"), f"{_num(pkg.get('system_kwp') or rec.get('system_kwp'))} kWp"),
        (_t(lang, "pdf.battery_storage"), f"{_num(battery)} kWh" if battery else _t(lang, "pdf.none_recommended")),
        (_t(lang, "pdf.annual_production"), f"{int(production):,}".replace(",", ".") + " kWh" if production else "—"),
        (_t(lang, "pdf.estimated_cost"), cost_text),
        (_t(lang, "pdf.monthly_savings"), _euro(fin["monthly_savings"] or root_fin.get("monthly_savings"))),
        (
            _t(lang, "pdf.payback_period"),
            f"{_num(fin['payback'] or root_fin.get('payback_years'))} {_t(lang, 'pdf.years')}",
        ),
        (_t(lang, "pdf.ten_year_savings"), _euro(fin["savings_10yr"] or root_fin.get("savings_10yr"))),
        (_t(lang, "pdf.co2"), f"{_num(co2)} {_t(lang, 'pdf.tonnes_year')}"),
    ]
    return _keep_section(_t(lang, "pdf.financial"), [_metric_cards(metrics, st)], st)


def _checklist_block(title: str, items_list: list, st) -> list:
    if not items_list:
        return []
    rows = []
    for i in range(0, len(items_list), 2):
        left = _safe(items_list[i])
        right = _safe(items_list[i + 1]) if i + 1 < len(items_list) else ""
        rows.append(
            [
                Paragraph(f"• {left}", st["body"]) if left else "",
                Paragraph(f"• {right}", st["body"]) if right else "",
            ]
        )
    table = Table(rows, colWidths=[8 * cm, 8 * cm])
    table.setStyle(
        TableStyle(
            [
                ("ROWBACKGROUNDS", (0, 0), (-1, -1), ROW_STRIPE),
                ("BOX", (0, 0), (-1, -1), 1, TEAL),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return _keep_section(title, [table], st, trailing_spacer=0.3)


def _assumptions_block(assumptions: list, st, lang: str) -> list:
    if not assumptions:
        return []
    items = _section_title(_t(lang, "pdf.assumptions"), st)
    for a in assumptions[:10]:
        items.append(Paragraph(f"• {_rich(a)}", st["body"]))
    items.append(Spacer(1, 0.25 * cm))
    return items


def _disclaimer_block(st, lang: str) -> list:
    text = _t(lang, "pdf.disclaimer")
    box = Table([[Paragraph(f"<i>{text}</i>", st["small"])]], colWidths=[16 * cm])
    box.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), TEAL_LIGHT),
                ("BOX", (0, 0), (-1, -1), 1, TEAL),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    return [Spacer(1, 0.2 * cm), box]


def _page_background(canvas, doc) -> None:
    canvas.saveState()
    canvas.setFillColor(PAGE_TINT)
    canvas.rect(0, 0, doc.pagesize[0], doc.pagesize[1], fill=1, stroke=0)
    canvas.restoreState()


def _profile_assessments_block(rec: dict, st) -> list:
    items = []
    ev = rec.get("ev_assessment") or {}
    hp = rec.get("hp_assessment") or {}
    if ev.get("ownership"):
        items.append(Paragraph("<b>EV charging profile</b>", st["section"]))
        items.append(
            Paragraph(
                _rich(
                    f"{ev.get('ownership_label', '—')} · {ev.get('annual_charging_kwh', 0):,} kWh/yr charging · "
                    f"Priority: {ev.get('charging_priority_label', '—')}"
                ),
                st["body"],
            )
        )
        items.append(Spacer(1, 0.15 * cm))
    if hp.get("status"):
        items.append(Paragraph("<b>Heating / heat pump profile</b>", st["section"]))
        items.append(
            Paragraph(
                _rich(
                    f"{hp.get('status_label', '—')} · {hp.get('type_label', '—')} · "
                    f"~{hp.get('annual_heat_kwh', 0):,} kWh/yr heat electricity · "
                    f"Priority: {hp.get('priority_label', '—')}"
                ),
                st["body"],
            )
        )
        items.append(Spacer(1, 0.2 * cm))
    sizing = rec.get("sizing_summary") or {}
    if sizing.get("capped_by_roof") and sizing.get("demand_note"):
        items.append(Paragraph("<b>Roof limit note</b>", st["section"]))
        items.append(Paragraph(_rich(sizing["demand_note"]), st["body"]))
        items.append(Spacer(1, 0.2 * cm))
    return items


def generate_decision_report_pdf(
    rec: dict,
    customer: dict | None = None,
    selected: dict | None = None,
    lang: str = "en",
) -> BytesIO:
    customer = customer or {}
    lang = lang if lang in ("en", "de") else "en"
    try:
        setlocale(LC_TIME, "de_DE.UTF-8" if lang == "de" else "en_GB.UTF-8")
    except Exception:
        try:
            setlocale(LC_TIME, "German_Germany.1252" if lang == "de" else "English_United Kingdom.1252")
        except Exception:
            pass
    st = _styles()
    pkgs = rec.get("three_packages", {}).get("packages", {})
    selected_id = rec.get("selected_package_id", "best_value")
    pkg = selected or pkgs.get(selected_id, {}) or rec
    dr = rec.get("decision_report", {})

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=1.6 * cm,
        bottomMargin=1.8 * cm,
        title=_t(lang, "pdf.title"),
        author="Solar Path",
    )

    elements = []
    elements.extend(_header_block(st, lang))
    elements.extend(_binding_notice_block(st, lang))
    elements.extend(_meta_block(rec, customer, st, lang))
    elements.extend(_readiness_block(rec.get("readiness", {}), st, lang))
    elements.extend(_why_block(rec, st, lang))
    elements.extend(_packages_table(pkgs, st, lang))

    scenarios = rec.get("price_scenarios", {}).get("scenarios", [])
    disclaimer = rec.get("price_scenarios", {}).get("disclaimer", "")
    elements.extend(_scenarios_table(scenarios, disclaimer, st, lang))
    elements.extend(_financial_block(rec, pkg, st, lang))
    elements.extend(_profile_assessments_block(rec, st))

    site_gaps = dr.get("site_gaps") or rec.get("confidence", {}).get("missing_data", [])
    elements.extend(_checklist_block(_t(lang, "pdf.site_gaps"), site_gaps, st))

    checklist = dr.get("quote_checklist") or rec.get("quote_quality_checklist", [])
    elements.extend(_checklist_block(_t(lang, "pdf.quote_checklist"), checklist, st))
    elements.extend(_assumptions_block(rec.get("assumptions", []), st, lang))
    elements.extend(_disclaimer_block(st, lang))

    doc.build(elements, onFirstPage=_page_background, onLaterPages=_page_background)
    buffer.seek(0)
    return buffer
