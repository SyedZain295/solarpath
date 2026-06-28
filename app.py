"""Flask application – Solar Pre-Assessment & Lead Generation Platform."""

import json
import logging
import math
import os
import re
import secrets
import uuid
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

from flask import Flask, jsonify, request, send_file, render_template, session, g, redirect, url_for
from pdf_report import generate_decision_report_pdf
from i18n import translate, TRANSLATIONS

from solar_engine import CalculatorInput, generate_recommendation
from pvgis_client import get_pv_estimate, geocode_location, geocode_postcode, roof_type_to_pvgis_params
from platform_features import match_suppliers, build_quote_status
from lead_qualification import build_lead_inp, build_lead_profile, evaluate_qualified_lead
from email_service import notify_quote_request, send_email_with_attachment
from supplier_utils import ensure_intake_slug, public_installer_brand, slugify, prepare_supplier_for_public_listing, is_directory_listing
from product_catalog import load_catalog, save_catalog, catalog_for_ui, check_component_compatibility, find_alternatives
from quote_parse_stub import parse_quote_text
from gsa_client import get_gsa_yield_estimate, validate_yield
from api_stubs import stub_bill_upload, stub_roof_analysis, stub_financing_offers, stub_incentives
from price_list_import import parse_csv_text, merge_products
from database import (
    init_db, db_session, db_health,
    Customer, Subscription, Quote, Assessment, Document, InstallerQuote,
    EvDealer, EvVehicle, EvBuyerLead,
)
from auth_customer import (
    hash_password, verify_password, login_customer, logout_customer,
    get_current_customer, customer_by_email,
)
from auth_supplier import login_supplier, get_current_supplier_id, supplier_authorized
from stripe_checkout import create_checkout_session, stripe_enabled, stripe_plan_enabled, verify_webhook, STRIPE_WEBHOOK_SECRET, STRIPE_SECRET_KEY
import supplier_store
from beta_access import (
    beta_gate_before_request,
    verify_beta_password,
    beta_gate_enabled,
    default_beta_invite,
    invite_href,
)
from analytics import track_event, beta_metrics_summary
from demo_data import load_demo_recommendation
from ev_profile import apply_ev_fields_to_input, estimate_ev_annual_kwh
from heat_pump_profile import apply_hp_fields_to_input, heat_goals_active
from quick_estimate import quick_estimate_range
from ev_marketplace import match_vehicles, home_energy_check, vehicles_for_api, vehicle_by_slug, clear_vehicle_cache
from ev_dealer_store import (
    create_dealer_intake,
    register_dealer,
    list_dealers,
    set_dealer_status,
    list_dealer_vehicles,
    create_vehicle,
    update_vehicle,
    delete_vehicle,
    list_dealer_leads,
    update_lead_status,
    create_buyer_lead_by_slug,
    dealer_by_email,
)
from auth_ev_dealer import (
    login_ev_dealer,
    logout_ev_dealer,
    get_current_ev_dealer,
    get_current_ev_dealer_id,
    ev_dealer_authorized,
    verify_password,
)
from logging_config import setup_logging

REGION_FOCUS = os.environ.get("REGION_FOCUS", "Bayern")
IS_PRODUCTION = os.environ.get("FLASK_ENV") == "production"
FLASK_DEBUG = os.environ.get("FLASK_DEBUG", "0" if IS_PRODUCTION else "1") == "1"

setup_logging(production=IS_PRODUCTION)
log = logging.getLogger("solarpath")

from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-solar-key-change-in-production")
app.config["PERMANENT_SESSION_LIFETIME"] = 86400 * 30
if IS_PRODUCTION:
    app.config["SESSION_COOKIE_SECURE"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
if IS_PRODUCTION and app.config["SECRET_KEY"] == "dev-solar-key-change-in-production":
    log.warning("SECRET_KEY is still the dev default — set a strong SECRET_KEY in production.")
if IS_PRODUCTION and os.environ.get("ADMIN_TOKEN", "dev-admin") == "dev-admin":
    log.warning("ADMIN_TOKEN is still the dev default — set ADMIN_TOKEN in production.")

init_db()
SUPPORTED_LANGUAGES = ("en", "de")
_GEOCODE_CACHE: dict[str, dict] = {}


@app.errorhandler(404)
def api_not_found(e):
    if request.path.startswith("/api/"):
        return jsonify({"error": "Not found"}), 404
    return e


@app.errorhandler(500)
def api_server_error(e):
    log.exception("Unhandled error on %s %s", request.method, request.path)
    if request.path.startswith("/api/"):
        return jsonify({"error": "Internal server error. Please try again."}), 500
    return e

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
SUPPLIERS_FILE = os.path.join(DATA_DIR, "suppliers.json")  # legacy import source only
CITY_COORDS_FILE = os.path.join(DATA_DIR, "city_coords.json")
_CITY_COORDS = None
_CITY_COORDS_MTIME = None
QUOTES_FILE = os.path.join(DATA_DIR, "quotes.json")
SURVEYS_FILE = os.path.join(DATA_DIR, "surveys.json")
CUSTOMERS_FILE = os.path.join(DATA_DIR, "customers.json")
ASSESSMENTS_FILE = os.path.join(DATA_DIR, "assessments.json")
DOCUMENTS_FILE = os.path.join(DATA_DIR, "documents.json")
SUBSCRIPTIONS_FILE = os.path.join(DATA_DIR, "subscriptions.json")
INTAKE_ANALYTICS_FILE = os.path.join(DATA_DIR, "intake_analytics.json")
ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "dev-admin")
SUPPORT_EMAIL = os.environ.get("SUPPORT_EMAIL", "support@solarpath.example")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

SUPPLIER_PLANS = {
    "basic": {
        "id": "basic",
        "name": "Basic",
        "tier": "Starter",
        "price_eur": 9,
        "trial_days": 30,
        "lead_note": "2 free enquiries included · then pay per extra lead",
        "features": [
            "1-month free trial — full listing access",
            "Visible profile & service area",
            "Contact form on your listing",
            "Basic directory placement",
            "Email lead notifications",
        ],
        "cta": "Start free trial",
    },
    "verified": {
        "id": "verified",
        "name": "Verified",
        "tier": "Growth",
        "price_eur": 29,
        "trial_days": 0,
        "lead_note": "5 qualified leads included · then €12 per extra lead",
        "features": [
            "Verified badge & higher ranking",
            "Quote tools & document access",
            "5 included leads per month",
            "Regional performance analytics",
        ],
        "cta": "Get Verified",
        "featured": True,
    },
    "premium": {
        "id": "premium",
        "name": "Premium",
        "tier": "Scale",
        "price_eur": 79,
        "trial_days": 0,
        "lead_note": "15 qualified leads included · then €9 per extra lead",
        "features": [
            "Priority & featured listing",
            "15 included leads per month",
            "CRM tools & lead pipeline",
            "Regional exclusivity options",
        ],
        "cta": "Go Premium",
    },
}


def load_json(path):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            raw = f.read().strip()
            if raw:
                return json.loads(raw)
    return []


def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def track_intake_view(slug: str) -> None:
    stats = load_json(INTAKE_ANALYTICS_FILE)
    if not isinstance(stats, dict):
        stats = {}
    entry = stats.get(slug, {"views": 0, "last_view": None})
    entry["views"] = int(entry.get("views", 0)) + 1
    entry["last_view"] = utc_now_iso()
    stats[slug] = entry
    save_json(INTAKE_ANALYTICS_FILE, stats)


def admin_authorized() -> bool:
    if session.get("admin_authenticated"):
        return True
    token = (
        request.headers.get("X-Admin-Token")
        or request.args.get("admin_token")
        or request.form.get("admin_token")
        or ""
    )
    if token and secrets.compare_digest(token, ADMIN_TOKEN):
        return True
    return FLASK_DEBUG and not IS_PRODUCTION


def get_suppliers():
    return supplier_store.get_all()


def _save_supplier(supplier: dict) -> dict:
    return supplier_store.upsert(supplier)


def _save_suppliers_batch(suppliers: list) -> None:
    supplier_store.replace_all(suppliers)


def filter_region_suppliers(suppliers: list, region: str = REGION_FOCUS) -> list:
    if not region:
        return suppliers
    return [s for s in suppliers if supplier_matches_state(s, region)]


def find_supplier_by_slug(slug: str) -> dict | None:
    return supplier_store.get_by_slug(slug)


def get_city_coords():
    global _CITY_COORDS, _CITY_COORDS_MTIME
    mtime = os.path.getmtime(CITY_COORDS_FILE) if os.path.isfile(CITY_COORDS_FILE) else None
    if _CITY_COORDS is None or mtime != _CITY_COORDS_MTIME:
        if os.path.isfile(CITY_COORDS_FILE):
            with open(CITY_COORDS_FILE, encoding="utf-8") as f:
                _CITY_COORDS = json.load(f)
        else:
            _CITY_COORDS = {}
        _CITY_COORDS_MTIME = mtime
    return _CITY_COORDS


def resolve_supplier_coords(supplier: dict):
    lat = supplier.get("latitude")
    lon = supplier.get("longitude")
    if lat is not None and lon is not None:
        return float(lat), float(lon)
    regions = supplier.get("regions") or []
    if len(regions) >= 2:
        cache = get_city_coords()
        city, state = regions[0], regions[-1]
        for key in (f"{city}|{state}", f"{city.split(',')[0].strip()}|{state}"):
            geo = cache.get(key)
            if geo and geo.get("latitude") is not None:
                return float(geo["latitude"]), float(geo["longitude"])
    return None, None


def get_lang() -> str:
    requested = request.args.get("lang")
    if requested in SUPPORTED_LANGUAGES:
        session["lang"] = requested
        return requested
    saved = session.get("lang")
    if saved in SUPPORTED_LANGUAGES:
        return saved
    header = request.headers.get("Accept-Language", "").lower()
    if header.startswith("de"):
        return "de"
    return "en"


@app.before_request
def set_request_language():
    g.lang = get_lang()


@app.before_request
def enforce_beta_access():
    if app.config.get("TESTING"):
        return None
    return beta_gate_before_request()


@app.context_processor
def inject_i18n():
    def t(key, default=None):
        text = translate(getattr(g, "lang", "en"), key, default)
        return text.replace("{support_email}", SUPPORT_EMAIL)

    def lang_url(code: str) -> str:
        args = request.args.to_dict(flat=True)
        args["lang"] = code
        if "invite" not in args and "token" not in args:
            inv = default_beta_invite()
            if inv:
                args["invite"] = inv
        if not request.path:
            from urllib.parse import urlencode
            return f"/?{urlencode(args)}" if args else "/"
        if args:
            from urllib.parse import urlencode
            return f"{request.path}?{urlencode(args)}"
        return request.path

    return {
        "t": t,
        "lang": getattr(g, "lang", "en"),
        "lang_url": lang_url,
        "invite_href": invite_href,
        "beta_invite_default": default_beta_invite(),
        "beta_gate_active": beta_gate_enabled(),
        "js_translations": TRANSLATIONS.get(getattr(g, "lang", "en"), {}),
        "support_email": SUPPORT_EMAIL,
    }


def geocode_cached(query: str):
    key = query.strip().lower()
    if not key:
        return None
    if key not in _GEOCODE_CACHE:
        _GEOCODE_CACHE[key] = geocode_location(query) or {}
    return _GEOCODE_CACHE[key] or None


def postcode_geocode_cached(postcode: str, city: str = ""):
    plz = postcode.strip()
    if not plz:
        return None
    city_key = city.strip().lower()
    key = f"plz:{plz}:{city_key}" if city_key else f"plz:{plz}"
    if key not in _GEOCODE_CACHE:
        _GEOCODE_CACHE[key] = geocode_postcode(plz, city=city) or {}
    return _GEOCODE_CACHE[key] or None


def city_geocode_cached(city: str, state: str = ""):
    city = city.strip()
    if not city:
        return None
    state_key = state.strip().lower()
    key = f"city:{city.lower()}|{state_key}"
    if key not in _GEOCODE_CACHE:
        query = f"{city}, {state}, Deutschland" if state else f"{city}, Deutschland"
        _GEOCODE_CACHE[key] = geocode_location(query) or {}
    return _GEOCODE_CACHE[key] or None


def haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


GERMAN_STATES = {
    "baden-württemberg", "bayern", "berlin", "brandenburg", "bremen", "hamburg",
    "hessen", "mecklenburg-vorpommern", "niedersachsen", "nordrhein-westfalen",
    "rheinland-pfalz", "saarland", "sachsen", "sachsen-anhalt", "schleswig-holstein", "thüringen",
}

BUNDESLAENDER = [
    "Baden-Württemberg",
    "Bayern",
    "Berlin",
    "Brandenburg",
    "Bremen",
    "Hamburg",
    "Hessen",
    "Mecklenburg-Vorpommern",
    "Niedersachsen",
    "Nordrhein-Westfalen",
    "Rheinland-Pfalz",
    "Saarland",
    "Sachsen",
    "Sachsen-Anhalt",
    "Schleswig-Holstein",
    "Thüringen",
]


def infer_state_from_geocode(geo: dict) -> str:
    parts = [p.strip() for p in geo.get("display_name", "").split(",") if p.strip()]
    for part in reversed(parts):
        if part.lower() == "deutschland":
            continue
        if part.lower() in GERMAN_STATES or part in {
            "Baden-Württemberg", "Bayern", "Berlin", "Brandenburg", "Bremen", "Hamburg",
            "Hessen", "Mecklenburg-Vorpommern", "Niedersachsen", "Nordrhein-Westfalen",
            "Rheinland-Pfalz", "Saarland", "Sachsen", "Sachsen-Anhalt", "Schleswig-Holstein", "Thüringen",
        }:
            return part
    return ""


BAYERN_BBOX = (47.27, 8.98, 50.56, 13.84)


def supplier_in_bavaria(supplier: dict) -> bool:
    lat, lon = resolve_supplier_coords(supplier)
    if lat is None or lon is None:
        return False
    south, west, north, east = BAYERN_BBOX
    return south <= lat <= north and west <= lon <= east


def supplier_in_rough_radius(supplier: dict, origin: dict, margin_km: float = 60) -> bool:
    lat, lon = resolve_supplier_coords(supplier)
    if lat is None or lon is None:
        return False
    return haversine_km(origin["latitude"], origin["longitude"], lat, lon) <= margin_km


def supplier_matches_state(supplier: dict, state_hint: str) -> bool:
    if not state_hint:
        return True
    hint = state_hint.lower()
    if hint in ("bayern", "bavaria") and supplier_in_bavaria(supplier):
        return True
    return any(hint in r.lower() or r.lower() in hint for r in supplier.get("regions", []))


def search_suppliers_by_location(
    suppliers: list,
    *,
    postcode: str = "",
    region: str = "",
    state: str = "",
    city: str = "",
    radius_km: float = 25,
):
    """Filter suppliers nationwide by Bundesland, city radius, or postcode radius."""
    origin = None
    state_hint = (state or region).strip()

    if postcode:
        origin = postcode_geocode_cached(postcode, city=region or city)
        if not origin:
            return None, []
        state_hint = infer_state_from_geocode(origin) or state_hint
    elif city:
        origin = city_geocode_cached(city, state=state_hint)
        if not origin:
            return None, []

    if origin:
        use_state_filter = radius_km < 100 and bool(state_hint) and not state
        candidates = suppliers
        if use_state_filter:
            candidates = [s for s in suppliers if supplier_matches_state(s, state_hint)]
        elif state:
            candidates = [s for s in suppliers if supplier_matches_state(s, state)]
        margin = max(radius_km + 100, 150)
        candidates = [s for s in candidates if supplier_in_rough_radius(s, origin, margin_km=margin)]
        nearby = []
        search_plz = postcode or (origin.get("postal_code") or "")
        for supplier in candidates:
            nearest = supplier_nearest_distance_km(supplier, origin, search_postcode=search_plz)
            if nearest and nearest["distance_km"] <= radius_km:
                supplier_copy = dict(supplier)
                supplier_copy["distance_km"] = nearest["distance_km"]
                supplier_copy["nearest_postcode"] = nearest["postcode"]
                nearby.append(supplier_copy)
        return origin, sorted(nearby, key=lambda s: s.get("distance_km", 9999))

    filtered = suppliers
    if state:
        filtered = [s for s in filtered if supplier_matches_state(s, state)]
    elif region:
        q = region.lower()
        filtered = [
            s for s in filtered
            if any(q in r.lower() or r.lower() in q for r in s.get("regions", []))
        ]
    filtered = sorted(filtered, key=lambda s: (s.get("company_name") or "").lower())
    return None, filtered


def supplier_nearest_distance_km(supplier: dict, origin: dict, search_postcode: str = ""):
    search_plz = search_postcode.strip()
    if search_plz and search_plz in supplier.get("locations_served", []):
        return {"distance_km": 0.0, "postcode": search_plz}

    best = None

    lat, lon = resolve_supplier_coords(supplier)
    if lat is not None and lon is not None:
        distance = haversine_km(origin["latitude"], origin["longitude"], lat, lon)
        nearest_postcode = supplier.get("locations_served", [None])[0] if supplier.get("locations_served") else search_plz or "—"
        return {"distance_km": round(distance, 1), "postcode": nearest_postcode or "—"}

    for postcode in supplier.get("locations_served", []):
        geo = postcode_geocode_cached(postcode)
        if not geo:
            continue
        distance = haversine_km(origin["latitude"], origin["longitude"], geo["latitude"], geo["longitude"])
        if best is None or distance < best["distance_km"]:
            best = {
                "distance_km": round(distance, 1),
                "postcode": postcode,
            }

    if best:
        return best

    return best


# ── Pages ──────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html", plans=SUPPLIER_PLANS)


@app.route("/calculator")
def calculator():
    ref = request.args.get("ref", "").strip()
    invite = (request.args.get("invite") or request.args.get("token") or "").strip()
    if not invite:
        invite = default_beta_invite()
    return render_template("calculator.html", intake_ref=ref, beta_invite=invite)


@app.route("/estimate")
def quick_estimate():
    """60-second entry — pre-fills the full calculator."""
    return render_template("estimate.html")


@app.route("/results")
def results():
    return render_template("results.html")


@app.route("/demo")
def demo():
    """Public demo — fixed München sample recommendation (no calculator required)."""
    return render_template("demo.html", demo_data=load_demo_recommendation())


@app.route("/i/<slug>")
def installer_intake(slug):
    track_intake_view(slug)
    supplier = find_supplier_by_slug(slug)
    if not supplier:
        return render_template("installer_intake.html", supplier=None, intake_slug=slug), 404
    brand = public_installer_brand(supplier, request.url_root)
    return render_template("installer_intake.html", supplier=brand, intake_slug=slug)


@app.route("/compare-quotes")
def compare_quotes_page():
    return render_template("compare_quotes.html")


@app.route("/project")
def project_dashboard_page():
    return render_template("project_dashboard.html")


@app.route("/compatibility")
def compatibility_page():
    return render_template("compatibility.html", catalog=catalog_for_ui())


@app.route("/suppliers")
def suppliers_page():
    return render_template("suppliers.html")


@app.route("/suppliers/register")
def supplier_register():
    return render_template("supplier_register.html")


def get_translated_plans(lang: str) -> dict:
    plans = {}
    for pid, plan in SUPPLIER_PLANS.items():
        features = [
            translate(lang, f"plans.{pid}.feature{i}", feat)
            for i, feat in enumerate(plan.get("features", []))
        ]
        plans[pid] = {
            **plan,
            "name": translate(lang, f"plans.{pid}.name", plan["name"]),
            "tier": translate(lang, f"plans.{pid}.tier", plan["tier"]),
            "lead_note": translate(lang, f"plans.{pid}.lead_note", plan["lead_note"]),
            "trial_note": translate(lang, f"plans.{pid}.trial_note", plan.get("trial_note", "")),
            "features": features,
            "cta": translate(lang, f"plans.{pid}.cta", plan.get("cta", "")),
        }
    return plans


@app.route("/suppliers/checkout/success")
def supplier_checkout_success():
    session_id = request.args.get("session_id", "")
    return render_template("checkout_success.html", session_id=session_id)


@app.route("/suppliers/checkout")
def supplier_checkout():
    plan_id = request.args.get("plan", "verified")
    if plan_id not in SUPPLIER_PLANS:
        plan_id = "verified"
    plans = get_translated_plans(get_lang())
    return render_template(
        "supplier_checkout.html",
        plan=plans[plan_id],
        plans=plans,
        stripe_enabled=stripe_plan_enabled(plan_id),
    )


@app.route("/register")
def customer_register():
    if get_current_customer():
        return redirect("/account")
    return render_template("customer_register.html")


@app.route("/login")
def customer_login_page():
    if get_current_customer():
        return redirect("/account")
    return render_template("login.html")


@app.route("/account")
def account_page():
    return render_template("account.html")


@app.route("/admin", methods=["GET", "POST"])
def admin_page():
    if request.method == "POST":
        token = (request.form.get("admin_token") or "").strip()
        if token and secrets.compare_digest(token, ADMIN_TOKEN):
            session["admin_authenticated"] = True
            return redirect("/admin")
        return render_template("admin_login.html", error=True)
    if not admin_authorized():
        return render_template("admin_login.html")
    return render_template("admin.html")


@app.route("/api/admin/logout", methods=["POST"])
def admin_logout():
    session.pop("admin_authenticated", None)
    return jsonify({"ok": True})


@app.route("/robots.txt")
def robots_txt():
    return """User-agent: *
Allow: /
Disallow: /admin
Disallow: /api/admin/
Sitemap: /sitemap.xml
""", 200, {"Content-Type": "text/plain; charset=utf-8"}


@app.route("/sitemap.xml")
def sitemap_xml():
    pages = ["/", "/calculator", "/suppliers", "/compare-quotes", "/compatibility",
             "/energy-advisor", "/ev", "/ev/find", "/ev/listings", "/ev/dealer/register", "/survey", "/register", "/privacy", "/terms"]
    base = request.url_root.rstrip("/")
    urls = "\n".join(f"  <url><loc>{base}{p}</loc></url>" for p in pages)
    return f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>', 200, {"Content-Type": "application/xml; charset=utf-8"}


@app.route("/privacy")
def privacy_page():
    return render_template("privacy.html")


@app.route("/terms")
def terms_page():
    return render_template("terms.html")


@app.route("/suppliers/dashboard")
def supplier_dashboard():
    return render_template("supplier_dashboard.html")


@app.route("/survey")
def survey():
    return render_template("survey_index.html")


@app.route("/survey/homeowners")
def survey_homeowners():
    return render_template("survey_homeowners.html")


@app.route("/survey/companies")
def survey_companies():
    return render_template("survey_companies.html")


@app.route("/energy-advisor")
def energy_advisor():
    return render_template("energy_advisor.html")


# ── Solar Path EV (Phase 1 advisor) ─────────────────────────────────────────

@app.route("/ev")
def ev_hub():
    return render_template("ev_hub.html")


@app.route("/ev/find")
def ev_find():
    return render_template("ev_find.html")


@app.route("/ev/listings")
def ev_listings():
    return render_template("ev_listings.html")


@app.route("/ev/home-energy")
def ev_home_energy():
    return render_template("ev_home_energy.html")


@app.route("/ev/sell")
def ev_sell():
    return render_template("ev_sell.html")


@app.route("/ev/dealer/register")
def ev_dealer_register():
    return render_template("ev_dealer_register.html")


@app.route("/ev/dealer/login")
def ev_dealer_login_page():
    return render_template("ev_dealer_login.html")


@app.route("/ev/dealer/dashboard")
def ev_dealer_dashboard():
    dealer = get_current_ev_dealer()
    if not dealer:
        return redirect(url_for("ev_dealer_login_page", next="/ev/dealer/dashboard"))
    return render_template("ev_dealer_dashboard.html", dealer=dealer.to_dict())


@app.route("/api/ev-vehicles", methods=["GET"])
def api_ev_vehicles():
    args = request.args
    filters = {
        "budget_max": args.get("budget_max"),
        "range_min": args.get("range_min"),
        "battery_health_min": args.get("battery_health_min"),
        "body_type": args.get("body_type"),
        "family_fit": args.get("family_fit"),
        "certificate_only": args.get("certificate_only") in ("1", "true", "yes"),
        "fast_charge_min": args.get("fast_charge_min"),
        "weekly_km": args.get("weekly_km"),
        "annual_km": args.get("annual_km"),
        "has_pv": args.get("has_pv") in ("1", "true", "yes"),
        "system_kwp": args.get("system_kwp"),
    }
    return jsonify({"vehicles": vehicles_for_api(filters), "count": len(vehicles_for_api(filters))})


@app.route("/api/ev-vehicles/<slug>", methods=["GET"])
def api_ev_vehicle_detail(slug):
    v = vehicle_by_slug(slug)
    if not v:
        return jsonify({"error": "Vehicle not found"}), 404
    profile = request.args.to_dict()
    from ev_marketplace import build_vehicle_fit, parse_buyer_profile
    return jsonify({**v, "solar_path_fit": build_vehicle_fit(v, parse_buyer_profile(profile))})


@app.route("/api/ev-match", methods=["POST"])
def api_ev_match():
    data = request.get_json() or {}
    if not data.get("budget_eur") and not data.get("weekly_km") and not data.get("annual_km"):
        return jsonify({"error": "Budget or driving distance required"}), 400
    result = match_vehicles(data, limit=5)
    try:
        track_event("ev_match", {"budget": data.get("budget_eur"), "priority": data.get("priority")})
    except Exception:
        log.debug("ev_match analytics failed", exc_info=True)
    return jsonify(result)


@app.route("/api/ev-home-energy", methods=["POST"])
def api_ev_home_energy():
    data = request.get_json() or {}
    slug = (data.get("vehicle_slug") or "").strip()
    return jsonify(home_energy_check(data, vehicle_slug=slug))


@app.route("/api/ev-dealer-intake", methods=["POST"])
def api_ev_dealer_intake():
    data = request.get_json() or {}
    name = (data.get("company_name") or "").strip()
    email = (data.get("email") or "").strip()
    if not name or not email:
        return jsonify({"error": "Company name and email required"}), 400
    dealer = create_dealer_intake(name, email, data.get("phone", ""), data.get("location", ""))
    try:
        track_event("ev_dealer_intake", {"company": name, "location": data.get("location"), "dealer_id": dealer.id})
    except Exception:
        pass
    return jsonify({
        "ok": True,
        "dealer_id": dealer.id,
        "status": dealer.status,
        "message": "Dealer intake received — register with the same email to set a password, then await approval.",
    })


@app.route("/api/ev-dealer/register", methods=["POST"])
def api_ev_dealer_register():
    data = request.get_json() or {}
    name = (data.get("company_name") or "").strip()
    email = (data.get("email") or "").strip()
    password = (data.get("password") or "").strip()
    if not name or not email or len(password) < 8:
        return jsonify({"error": "Company name, email and password (8+ chars) required"}), 400
    dealer = register_dealer(name, email, password, data.get("phone", ""), data.get("location", ""))
    if os.environ.get("EV_DEALER_AUTO_APPROVE", "").lower() in ("1", "true", "yes"):
        set_dealer_status(dealer.id, "approved")
        dealer = dealer_by_email(email) or dealer
    return jsonify({"ok": True, "dealer": dealer.to_dict(), "status": dealer.status})


@app.route("/api/ev-dealer/login", methods=["POST"])
def api_ev_dealer_login():
    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()
    password = (data.get("password") or "").strip()
    dealer = dealer_by_email(email)
    if not dealer or not verify_password(dealer, password):
        return jsonify({"error": "Invalid email or password"}), 401
    if dealer.status == "suspended":
        return jsonify({"error": "Account suspended"}), 403
    login_ev_dealer(dealer.id)
    return jsonify({"ok": True, "dealer": dealer.to_dict()})


@app.route("/api/ev-dealer/logout", methods=["POST"])
def api_ev_dealer_logout():
    logout_ev_dealer()
    return jsonify({"ok": True})


@app.route("/api/ev-dealer/me", methods=["GET"])
def api_ev_dealer_me():
    dealer = get_current_ev_dealer()
    if not dealer:
        return jsonify({"error": "Not logged in"}), 401
    vehicles = list_dealer_vehicles(dealer.id) if dealer.status == "approved" else []
    return jsonify({"dealer": dealer.to_dict(), "vehicles": vehicles})


@app.route("/api/ev-dealer/vehicles", methods=["GET", "POST"])
def api_ev_dealer_vehicles():
    dealer = get_current_ev_dealer()
    if not dealer:
        return jsonify({"error": "Not logged in"}), 401
    if dealer.status != "approved":
        return jsonify({"error": "Dealer account pending approval"}), 403
    if request.method == "GET":
        return jsonify({"vehicles": list_dealer_vehicles(dealer.id)})
    data = request.get_json() or {}
    try:
        vehicle = create_vehicle(dealer.id, data)
        clear_vehicle_cache()
        return jsonify(vehicle), 201
    except PermissionError as exc:
        return jsonify({"error": str(exc)}), 403
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/api/ev-dealer/vehicles/<vehicle_id>", methods=["PUT", "DELETE"])
def api_ev_dealer_vehicle(vehicle_id):
    dealer = get_current_ev_dealer()
    if not dealer:
        return jsonify({"error": "Not logged in"}), 401
    if dealer.status != "approved":
        return jsonify({"error": "Dealer account pending approval"}), 403
    if request.method == "DELETE":
        if delete_vehicle(dealer.id, vehicle_id):
            clear_vehicle_cache()
            return jsonify({"ok": True})
        return jsonify({"error": "Not found"}), 404
    data = request.get_json() or {}
    vehicle = update_vehicle(dealer.id, vehicle_id, data)
    if not vehicle:
        return jsonify({"error": "Not found"}), 404
    clear_vehicle_cache()
    return jsonify(vehicle)


@app.route("/api/ev-dealer/leads", methods=["GET"])
def api_ev_dealer_leads():
    dealer = get_current_ev_dealer()
    if not dealer:
        return jsonify({"error": "Not logged in"}), 401
    if dealer.status != "approved":
        return jsonify({"error": "Dealer account pending approval"}), 403
    return jsonify({"leads": list_dealer_leads(dealer.id)})


@app.route("/api/ev-dealer/leads/<lead_id>", methods=["PATCH"])
def api_ev_dealer_lead_update(lead_id):
    dealer = get_current_ev_dealer()
    if not dealer:
        return jsonify({"error": "Not logged in"}), 401
    data = request.get_json() or {}
    status = (data.get("status") or "").strip()
    if status not in ("new", "contacted", "closed"):
        return jsonify({"error": "Invalid status"}), 400
    if update_lead_status(dealer.id, lead_id, status):
        return jsonify({"ok": True})
    return jsonify({"error": "Not found"}), 404


@app.route("/api/ev-buyer-lead", methods=["POST"])
def api_ev_buyer_lead():
    data = request.get_json() or {}
    slug = (data.get("vehicle_slug") or "").strip()
    name = (data.get("buyer_name") or data.get("name") or "").strip()
    email = (data.get("buyer_email") or data.get("email") or "").strip()
    if not slug or not name or not email:
        return jsonify({"error": "Vehicle, name and email required"}), 400
    result = create_buyer_lead_by_slug(
        slug,
        buyer_name=name,
        buyer_email=email,
        buyer_phone=data.get("buyer_phone") or data.get("phone", ""),
        buyer_postcode=data.get("buyer_postcode") or data.get("postcode", ""),
        buyer_profile=data.get("buyer_profile") or data.get("profile"),
        message=data.get("message", ""),
    )
    try:
        track_event("ev_buyer_lead", {"vehicle_slug": slug, "qualified": result.get("qualified"), "demo": result.get("demo")})
    except Exception:
        pass
    if not result.get("ok"):
        return jsonify(result), 404
    return jsonify(result)


@app.route("/api/admin/ev-dealers", methods=["GET"])
def api_admin_ev_dealers():
    if not admin_authorized():
        return jsonify({"error": "Unauthorized"}), 401
    status = request.args.get("status")
    return jsonify({"dealers": list_dealers(status=status or None)})


@app.route("/api/admin/ev-dealers/<dealer_id>", methods=["PATCH"])
def api_admin_ev_dealer_patch(dealer_id):
    if not admin_authorized():
        return jsonify({"error": "Unauthorized"}), 401
    data = request.get_json() or {}
    status = (data.get("status") or "").strip()
    if status not in ("pending", "approved", "suspended"):
        return jsonify({"error": "Invalid status"}), 400
    dealer = set_dealer_status(dealer_id, status)
    if not dealer:
        return jsonify({"error": "Not found"}), 404
    clear_vehicle_cache()
    return jsonify({"ok": True, "dealer": dealer.to_dict()})


@app.route("/beta-login", methods=["GET", "POST"])
def beta_login():
    error = None
    if request.method == "POST":
        password = request.form.get("password", "")
        if verify_beta_password(password):
            session["beta_authenticated"] = True
            session.permanent = True
            nxt = request.args.get("next") or "/"
            return redirect(nxt)
        error = "Invalid beta password"
    return render_template("beta_login.html", error=error, beta_gate=beta_gate_enabled())


@app.route("/health")
def health():
    """Load-balancer / Azure health probe."""
    db = db_health()
    return jsonify({
        "status": "ok" if db.get("ok") else "degraded",
        "service": "solar-path",
        "region_focus": REGION_FOCUS,
        "database": db,
        "stripe": stripe_enabled(),
        "beta_gate": beta_gate_enabled(),
        "demo_mode": os.environ.get("BETA_DEMO_MODE", "0").strip().lower() in ("1", "true", "yes", "on"),
        "beta_gate_env": os.environ.get("BETA_GATE_ENABLED", "1"),
        "suppliers_db": supplier_store.count(),
    })


# ── API: Calculator ─────────────────────────────────────────────────────────

@app.route("/api/quick-estimate", methods=["POST"])
def api_quick_estimate():
    data = request.get_json() or {}
    postcode = (data.get("postcode") or "").strip()
    goals = data.get("goals") or []
    if isinstance(goals, str):
        goals = [goals]
    goal = data.get("goal") or (goals[0] if goals else "lower_bill")
    if not goals:
        goals = [goal]

    specific_yield = None
    if postcode:
        geo = geocode_postcode(postcode)
        if geo:
            try:
                roof_type = data.get("roof_type", "pitched_south")
                angle, aspect = roof_type_to_pvgis_params(roof_type)
                pvgis = get_pv_estimate(float(geo["latitude"]), float(geo["longitude"]), peakpower=1.0, angle=angle, aspect=aspect)
                if pvgis and pvgis.get("specific_yield_kwh_kwp"):
                    specific_yield = float(pvgis["specific_yield_kwh_kwp"])
            except Exception:
                log.debug("quick-estimate PVGIS skipped", exc_info=True)

    result = quick_estimate_range(
        monthly_kwh=float(data.get("monthly_kwh", 0)),
        monthly_bill_eur=float(data.get("monthly_bill_eur", 0)),
        electricity_price_ct=float(data.get("electricity_price_ct", 32.0)),
        roof_area_m2=float(data.get("roof_area_m2", 0)),
        roof_type=data.get("roof_type", "pitched_south"),
        goals=goals,
        specific_yield=specific_yield,
    )
    if postcode:
        result["postcode"] = postcode
    lang = getattr(g, "lang", "en") or "en"
    result["message"] = result.get("message_de" if lang == "de" else "message_en", result["message_en"])
    return jsonify(result)


@app.route("/api/calculate", methods=["POST"])
def api_calculate():
    data = request.get_json() or {}

    lat = data.get("latitude")
    lon = data.get("longitude")
    location_name = data.get("location_name", "")
    postcode = (data.get("postcode") or "").strip()

    if lat is None or lon is None:
        if postcode:
            geo = geocode_postcode(postcode)
            if geo:
                lat = geo["latitude"]
                lon = geo["longitude"]
                location_name = geo.get("display_name") or location_name or postcode
        if (lat is None or lon is None) and location_name:
            geo = geocode_location(location_name)
            if geo:
                lat = geo["latitude"]
                lon = geo["longitude"]
                location_name = geo["display_name"]
            elif lat is None or lon is None:
                return jsonify({"error": "Could not geocode location. Please try coordinates or a different address."}), 400
        if lat is None or lon is None:
            return jsonify({"error": "Location is required."}), 400

    roof_type = data.get("roof_type", "pitched_south")
    angle, aspect = roof_type_to_pvgis_params(roof_type)

    pvgis = get_pv_estimate(float(lat), float(lon), peakpower=1.0, angle=angle, aspect=aspect)
    pvgis_fallback = pvgis is None

    inp = CalculatorInput(
        latitude=float(lat),
        longitude=float(lon),
        location_name=location_name,
        postcode=postcode,
        monthly_bill_eur=float(data.get("monthly_bill_eur", 0)),
        monthly_kwh=float(data.get("monthly_kwh", 0)),
        roof_type=roof_type,
        roof_area_m2=float(data.get("roof_area_m2", 0)),
        budget_eur=float(data.get("budget_eur", 0)),
        goals=data.get("goals", ["lower_bill"]),
        electricity_price_ct=float(data.get("electricity_price_ct", 32.0)),
        feed_in_type=data.get("feed_in_type", "partial"),
        housing_type=data.get("housing_type", "detached"),
        owner_status=data.get("owner_status", "owner"),
        shading=data.get("shading", "unknown"),
        has_heat_pump=bool(data.get("has_heat_pump")),
        has_ev=bool(data.get("has_ev")),
        has_electric_water_heater=bool(data.get("has_electric_water_heater")),
        has_pool=bool(data.get("has_pool")),
        has_roof_photos=bool(data.get("has_roof_photos")),
        has_home_office=bool(data.get("has_home_office")),
        has_ac=bool(data.get("has_ac")),
        planned_ev=bool(data.get("planned_ev")),
        high_daytime_use=bool(data.get("high_daytime_use")),
        planned_extension=bool(data.get("planned_extension")),
        budget_first_mode=bool(data.get("budget_first_mode")),
        installation_timeframe=data.get("installation_timeframe", "not_sure"),
        selected_package=data.get("selected_package", ""),
        connect_meter=bool(data.get("connect_meter")),
        battery_interest=data.get("battery_interest", "unsure"),
        financing_interest=data.get("financing_interest", "no"),
        user_situation=data.get("user_situation", ""),
        has_existing_pv=bool(data.get("has_existing_pv")),
    )
    if "ev_charging" in (inp.goals or []):
        apply_ev_fields_to_input(inp, data)
    if heat_goals_active(inp.goals):
        apply_hp_fields_to_input(inp, data)

    recommendation = generate_recommendation(inp, pvgis)
    gsa = get_gsa_yield_estimate(float(lat), float(lon))
    if pvgis and gsa:
        recommendation["yield_validation"] = validate_yield(
            pvgis.get("specific_yield_kwh_kwp", 0),
            gsa.get("specific_yield_kwh_kwp", 0),
        )
        recommendation["gsa_yield"] = {k: v for k, v in gsa.items() if k != "raw"}
    source_slug = data.get("source_installer_slug", "").strip()
    if source_slug:
        recommendation["source_installer_slug"] = source_slug
        src = find_supplier_by_slug(source_slug)
        if src:
            recommendation["source_installer"] = public_installer_brand(src, request.url_root)
    recommendation["location"] = {
        "latitude": float(lat),
        "longitude": float(lon),
        "name": location_name,
    }
    recommendation["pvgis"] = (
        {k: pvgis.get(k) for k in ("specific_yield_kwh_kwp", "annual_kwh_per_kwp", "cached", "monthly") if pvgis.get(k) is not None}
        if pvgis else None
    )
    recommendation["pvgis_fallback"] = pvgis_fallback
    if pvgis_fallback:
        recommendation["pvgis_notice"] = (
            "PVGIS solar data temporarily unavailable — results use a regional estimate (950 kWh/kWp)."
        )

    suppliers = filter_region_suppliers(get_suppliers())
    recommendation["matched_suppliers"] = [
        prepare_supplier_for_public_listing(s, quality_score=_supplier_quality_score(s))
        for s in match_suppliers(suppliers, inp, recommendation, limit=5)
    ]

    try:
        track_event("calculator_complete", {
            "postcode": postcode,
            "system_kwp": recommendation.get("system_kwp"),
            "housing_type": data.get("housing_type"),
        })
    except Exception:
        log.debug("analytics track failed", exc_info=True)

    return jsonify(recommendation)


@app.route("/api/survey", methods=["POST"])
def api_survey_submit():
    data = request.get_json() or {}
    survey_type = data.get("survey_type", "homeowner")

    if survey_type == "company":
        required = [
            "s1_monthly_inquiries",
            "s1_weekly_qual_time",
            "s1_loss_stage",
            "s2_time_reduction",
            "s2_quote_ready_value",
            "s2_quote_ready_definition",
            "s3_spend_model",
            "s3_monthly_spend",
            "s3_commercial_preference",
            "s3_followup",
        ]
        checkbox_groups = {
            "s1_loss_reasons": (1, 3),
            "s1_info_needed": (1, None),
            "s2_useful_parts": (1, 3),
            "s2_trust_requirements": (1, None),
            "s3_worth_paying": (1, 3),
            "s3_stop_using": (1, None),
        }
        for name, (min_count, max_count) in checkbox_groups.items():
            values = data.get(name)
            count = len(values) if isinstance(values, list) else (1 if values else 0)
            other = (data.get(f"{name}_other") or "").strip()
            if count < min_count and not other:
                return jsonify({"error": f"Please complete the selection for {name}."}), 400
            if max_count and count > max_count:
                return jsonify({"error": f"Too many selections for {name}."}), 400
        if data.get("s3_followup") == "yes":
            if not (data.get("s3_followup_company") or "").strip():
                return jsonify({"error": "Company name required for follow-up."}), 400
            if not (data.get("s3_followup_email") or "").strip():
                return jsonify({"error": "Email required for follow-up."}), 400
        error_msg = "Please answer all required solar company questions."
    else:
        required = [
            "h1_use_tool",
            "h1_biggest_concern",
            "h1_bill_understanding",
            "h1_share_info",
            "h2_property_type",
            "h2_ownership",
            "h2_install_timeline",
            "h2_monthly_bill",
            "h3_outcome_priority",
            "h3_solar_option",
            "h3_compare_quotes",
            "h4_personal_estimate",
            "h4_followup_interview",
        ]
        checkbox_groups = {
            "h2_loads": (1, None),
            "h3_trust_supplier": (1, None),
        }
        for name, (min_count, max_count) in checkbox_groups.items():
            values = data.get(name)
            count = len(values) if isinstance(values, list) else (1 if values else 0)
            other = (data.get(f"{name}_other") or "").strip()
            if count < min_count and not other:
                return jsonify({"error": f"Please complete the selection for {name}."}), 400
            if max_count and count > max_count:
                return jsonify({"error": f"Too many selections for {name}."}), 400
        if data.get("h1_biggest_concern") == "other" and not (data.get("h1_biggest_concern_other") or "").strip():
            return jsonify({"error": "Please specify your biggest concern."}), 400
        if data.get("h2_property_type") == "other" and not (data.get("h2_property_type_other") or "").strip():
            return jsonify({"error": "Please specify your property type."}), 400
        error_msg = "Please answer all required homeowner questions."

    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({"error": error_msg}), 400

    surveys = load_json(SURVEYS_FILE)
    entry = {
        "id": f"survey-{uuid.uuid4().hex[:8]}",
        "survey_type": survey_type,
        "responses": data,
        "created_at": utc_now_iso(),
    }
    surveys.append(entry)
    save_json(SURVEYS_FILE, surveys)
    return jsonify({"success": True, "id": entry["id"]}), 201


@app.route("/api/geocode")
def api_geocode():
    q = request.args.get("q", "")
    if not q:
        return jsonify({"error": "Query required"}), 400
    result = geocode_location(q)
    if result:
        return jsonify(result)
    return jsonify({"error": "Location not found"}), 404


# ── API: Suppliers ──────────────────────────────────────────────────────────

@app.route("/api/suppliers/stats", methods=["GET"])
def api_suppliers_stats():
    all_suppliers = get_suppliers()
    suppliers = filter_region_suppliers(all_suppliers)
    by_city = {}
    for s in suppliers:
        regions = s.get("regions") or []
        city = regions[0] if regions else "Unknown"
        by_city[city] = by_city.get(city, 0) + 1
    top_cities = sorted(by_city.items(), key=lambda x: -x[1])[:12]
    return jsonify({
        "total": len(suppliers),
        "region": REGION_FOCUS,
        "top_cities": [{"city": c, "count": n} for c, n in top_cities],
    })


@app.route("/api/suppliers", methods=["GET"])
def api_suppliers_list():
    all_suppliers = get_suppliers()
    postcode = request.args.get("postcode", "").strip()
    region = request.args.get("region", "").strip()
    state = request.args.get("state", REGION_FOCUS).strip() or REGION_FOCUS
    city = request.args.get("city", "").strip()
    radius_km = float(request.args.get("radius_km", 25) or 25)
    limit_raw = request.args.get("limit", "")
    offset = max(int(request.args.get("offset", 0) or 0), 0)
    paged = bool(limit_raw)

    pool = filter_region_suppliers(all_suppliers, state)
    origin, filtered = search_suppliers_by_location(
        pool,
        postcode=postcode,
        region=region,
        state=state,
        city=city,
        radius_km=radius_km,
    )
    if origin is None and (postcode or city) and not filtered:
        return jsonify({"error": "Location not found"}), 404

    filtered.sort(key=_supplier_list_rank)

    filtered = [
        prepare_supplier_for_public_listing(s, quality_score=_supplier_quality_score(s))
        for s in filtered
    ]

    total = len(filtered)
    if paged:
        limit = min(max(int(limit_raw), 1), 200)
        page = filtered[offset: offset + limit]
        meta = {
            "items": page,
            "total": total,
            "limit": limit,
            "offset": offset,
            "region_total": len(pool),
            "region": state,
        }
        if state:
            meta["state"] = state
        if city:
            meta["city"] = city
        if postcode:
            meta["postcode"] = postcode
        if origin:
            meta["search_center"] = origin.get("display_name", "")
        return jsonify(meta)

    return jsonify(filtered)


def _supplier_list_rank(s: dict) -> tuple:
    """Registered/verified first; demo seed listings last."""
    demo = 1 if s.get("listing_status") == "demo" else 0
    directory = is_directory_listing(s)
    has_contact = 0 if directory else 1
    verified = 1 if s.get("verified") and not demo else 0
    dist = float(s.get("distance_km") if s.get("distance_km") is not None else 9999)
    quality = _supplier_quality_score(s) or 0
    return (demo, -verified, -has_contact, dist, -quality)


def _supplier_quality_score(s: dict) -> int | None:
    """Transparent ranking – not just who pays the most. None for unverified directory rows."""
    if is_directory_listing(s):
        return None
    score = 40
    if s.get("verified"):
        score += 15
    certs = s.get("certifications", [])
    score += min(15, len(certs) * 5)
    reviews = s.get("reviews_count", 0)
    if reviews > 0:
        rating = s.get("rating", 0)
        score += min(15, int(float(rating) * 3))
        score += min(10, reviews // 10)
    if s.get("products"):
        score += 5
    if s.get("financing_options"):
        score += 5
    plan = s.get("plan", "basic")
    if plan == "premium":
        score += 3
    elif plan == "verified":
        score += 2
    return min(100, score)


SUPPLIER_WRITABLE_FIELDS = {
    "company_name", "phone", "website", "description", "regions", "locations_served",
    "certifications", "financing_options", "installation_availability",
    "earliest_survey_date", "earliest_install_weeks", "residential_available",
    "commercial_available", "battery_capable", "ev_charger_capable",
    "heat_pump_capable", "agricultural_available", "products",
}


def _verify_supplier_checkout(checkout_id: str, email: str) -> tuple[dict | None, str | None]:
    """Return subscription dict if checkout is valid for registration."""
    if not checkout_id:
        return None, "Complete checkout at /suppliers/checkout before registering."
    email = email.strip().lower()
    with db_session() as db:
        sub = db.get(Subscription, checkout_id)
        if not sub:
            return None, "Invalid checkout reference."
        if sub.status not in ("active", "paid_demo"):
            return None, "Payment not confirmed yet. Wait a moment and try again."
        if sub.email.lower() != email:
            return None, "Registration email must match checkout email."
        sub_dict = sub.to_dict()
    if any(s.get("checkout_id") == checkout_id for s in get_suppliers()):
        return None, "This checkout was already used for registration."
    return sub_dict, None


@app.route("/api/suppliers", methods=["POST"])
def api_suppliers_create():
    data = request.get_json() or {}
    required = ["company_name", "email", "phone"]
    if not all(data.get(f) for f in required):
        return jsonify({"error": "company_name, email, and phone are required"}), 400

    checkout_id = (data.get("checkout_id") or "").strip()
    sub, checkout_err = _verify_supplier_checkout(checkout_id, data["email"])
    if checkout_err:
        return jsonify({"error": checkout_err}), 402

    plan = sub["plan"] if sub else data.get("plan", "basic")
    verified = plan in ("verified", "premium")

    suppliers = get_suppliers()
    new_supplier = {
        "id": f"sup-{uuid.uuid4().hex[:8]}",
        "company_name": data["company_name"],
        "email": data["email"].strip().lower(),
        "phone": data["phone"],
        "website": data.get("website", ""),
        "plan": plan,
        "verified": verified,
        "checkout_id": checkout_id,
        "locations_served": data.get("locations_served", []),
        "regions": data.get("regions", []),
        "products": data.get("products", []),
        "certifications": data.get("certifications", []),
        "installation_availability": data.get("installation_availability", ""),
        "financing_options": data.get("financing_options", []),
        "rating": 0,
        "reviews_count": 0,
        "description": data.get("description", ""),
        "earliest_survey_date": data.get("earliest_survey_date", ""),
        "earliest_install_weeks": data.get("earliest_install_weeks"),
        "residential_available": data.get("residential_available", True),
        "commercial_available": data.get("commercial_available", False),
        "battery_capable": data.get("battery_capable", True),
        "ev_charger_capable": data.get("ev_charger_capable", False),
        "heat_pump_capable": data.get("heat_pump_capable", False),
        "agricultural_available": data.get("agricultural_available", False),
        "created_at": utc_now_iso(),
    }
    new_supplier["listing_status"] = "verified" if verified else "unverified"
    new_supplier["source"] = "registered"
    new_supplier["contact_verified"] = False
    new_supplier["service_area"] = new_supplier.get("regions") or []
    taken = {s.get("intake_slug") for s in suppliers if s.get("intake_slug")}
    new_supplier["intake_slug"] = ensure_intake_slug(new_supplier, taken)
    saved = _save_supplier(new_supplier)
    login_supplier(saved["id"])
    return jsonify(saved), 201


@app.route("/api/checkout", methods=["POST"])
def api_checkout():
    data = request.get_json() or {}
    plan_id = data.get("plan", "verified")
    if plan_id not in SUPPLIER_PLANS:
        return jsonify({"error": "Invalid plan"}), 400

    email = (data.get("email") or "").strip().lower()
    if not email:
        return jsonify({"error": "Email is required"}), 400

    plan = SUPPLIER_PLANS[plan_id]
    checkout_id = f"chk-{uuid.uuid4().hex[:10]}"
    base = request.url_root.rstrip("/")
    success_url = f"{base}/suppliers/checkout/success?session_id={{CHECKOUT_SESSION_ID}}&checkout={checkout_id}"
    cancel_url = f"{base}/suppliers/checkout?plan={plan_id}"

    try:
        stripe_session = create_checkout_session(
            plan_id=plan_id,
            email=email,
            checkout_id=checkout_id,
            amount_eur=plan["price_eur"],
            success_url=success_url,
            cancel_url=cancel_url,
        )
    except RuntimeError as exc:
        return jsonify({"error": f"Payment provider error: {exc}"}), 502

    if stripe_session:
        status = "pending"
        disclaimer = "Secure payment via Stripe."
        redirect_url = stripe_session["url"]
        stripe_session_id = stripe_session["id"]
    else:
        status = "paid_demo"
        disclaimer = "Demo checkout — no charge. Set STRIPE_SECRET_KEY + STRIPE_PRICE_* for live payments."
        stripe_session_id = None
        redirect_url = f"/suppliers/register?plan={plan_id}&checkout={checkout_id}"

    with db_session() as db:
        db.add(Subscription(
            id=checkout_id,
            plan=plan_id,
            email=email,
            amount_eur=plan["price_eur"],
            status=status,
            stripe_session_id=stripe_session_id,
            disclaimer=disclaimer,
        ))

    return jsonify({
        "success": True,
        "checkout_id": checkout_id,
        "plan": plan_id,
        "redirect": redirect_url,
        "stripe": bool(stripe_session),
    }), 201


@app.route("/api/stripe/webhook", methods=["POST"])
def stripe_webhook():
    if not STRIPE_WEBHOOK_SECRET:
        return jsonify({"error": "Webhook not configured"}), 400
    payload = request.get_data()
    sig = request.headers.get("Stripe-Signature", "")
    try:
        event = verify_webhook(payload, sig)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400

    if event["type"] == "checkout.session.completed":
        sess = event["data"]["object"]
        checkout_id = (sess.get("metadata") or {}).get("checkout_id")
        if checkout_id:
            with db_session() as db:
                sub = db.get(Subscription, checkout_id)
                if sub:
                    sub.status = "active"
                    sub.stripe_session_id = sess.get("id")
    return jsonify({"received": True})


@app.route("/api/checkout/verify/<checkout_id>", methods=["GET"])
def api_checkout_verify(checkout_id):
    session_id = request.args.get("session_id", "")
    with db_session() as db:
        sub = db.get(Subscription, checkout_id)
        if not sub:
            return jsonify({"error": "Checkout not found"}), 404
        if sub.status == "pending" and session_id and STRIPE_SECRET_KEY:
            try:
                import stripe
                stripe.api_key = STRIPE_SECRET_KEY
                sess = stripe.checkout.Session.retrieve(session_id)
                if sess.get("payment_status") == "paid" or sess.get("status") == "complete":
                    sub.status = "active"
                    sub.stripe_session_id = session_id
            except Exception:
                pass
        ok = sub.status in ("active", "paid_demo")
        return jsonify({"ok": ok, "subscription": sub.to_dict()})


@app.route("/api/customers", methods=["POST"])
def api_customers_create():
    data = request.get_json() or {}
    required = ["name", "email", "phone", "postcode", "password"]
    if not all(str(data.get(f, "")).strip() for f in required):
        return jsonify({"error": "name, email, phone, postcode, and password are required"}), 400

    password = data["password"]
    if len(password) < 8:
        return jsonify({"error": "Password must be at least 8 characters."}), 400

    email = data["email"].strip().lower()
    if customer_by_email(email):
        return jsonify({"error": "An account with this email already exists."}), 409

    new_id = f"cust-{uuid.uuid4().hex[:8]}"
    customer = Customer(
        id=new_id,
        name=data["name"].strip(),
        email=email,
        password_hash=hash_password(password),
        phone=data["phone"].strip(),
        postcode=data["postcode"].strip(),
        housing_type=data.get("housing_type", ""),
        interests=data.get("interests") or [],
    )
    with db_session() as db:
        db.add(customer)
        payload = customer.to_dict()
    login_customer(new_id)
    return jsonify(payload), 201


@app.route("/api/login", methods=["POST"])
def api_login():
    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    if not email or not password:
        return jsonify({"error": "Email and password are required."}), 400

    customer = customer_by_email(email)
    if not customer or not verify_password(customer, password):
        return jsonify({"error": "Invalid email or password."}), 401

    login_customer(customer.id)
    return jsonify({"ok": True, "customer": customer.to_dict()})


@app.route("/api/logout", methods=["POST"])
def api_logout():
    logout_customer()
    return jsonify({"ok": True})


@app.route("/api/me", methods=["GET"])
def api_me():
    customer = get_current_customer()
    if not customer:
        return jsonify({"authenticated": False})
    return jsonify({"authenticated": True, "customer": customer.to_dict()})


@app.route("/api/suppliers/<supplier_id>", methods=["PUT"])
def api_suppliers_update(supplier_id):
    if not supplier_authorized(supplier_id, admin_ok=True):
        return jsonify({"error": "Authentication required"}), 401
    data = request.get_json() or {}
    updates = {k: v for k, v in data.items() if k in SUPPLIER_WRITABLE_FIELDS}
    if not updates:
        return jsonify({"error": "No valid fields to update"}), 400
    existing = supplier_store.get_by_id(supplier_id)
    if not existing:
        return jsonify({"error": "Supplier not found"}), 404
    existing.update(updates)
    saved = _save_supplier(existing)
    return jsonify(saved)


@app.route("/api/installers/<slug>", methods=["GET"])
def api_installer_by_slug(slug):
    supplier = find_supplier_by_slug(slug)
    if not supplier:
        return jsonify({"error": "Installer not found"}), 404
    return jsonify(public_installer_brand(supplier, request.url_root))


@app.route("/api/suppliers/<supplier_id>/intake-link", methods=["GET"])
def api_supplier_intake_link(supplier_id):
    suppliers = get_suppliers()
    for s in suppliers:
        if s["id"] == supplier_id:
            brand = public_installer_brand(s, request.url_root)
            return jsonify(brand)
    return jsonify({"error": "Supplier not found"}), 404


@app.route("/api/catalog", methods=["GET"])
def api_catalog_list():
    return jsonify(catalog_for_ui())


@app.route("/api/catalog/compatibility-check", methods=["POST"])
def api_catalog_compatibility():
    data = request.get_json() or {}
    panel_id = data.get("panel_id")
    inverter_id = data.get("inverter_id")
    system_kwp = float(data.get("system_kwp") or 5)
    if not panel_id or not inverter_id:
        return jsonify({"error": "panel_id and inverter_id required"}), 400
    result = check_component_compatibility(
        panel_id, inverter_id, system_kwp,
        battery_id=data.get("battery_id"),
        goals=data.get("goals") or [],
    )
    return jsonify(result)


@app.route("/api/catalog/alternatives", methods=["POST"])
def api_catalog_alternatives():
    data = request.get_json() or {}
    result = find_alternatives(
        data.get("panel_id", ""),
        data.get("inverter_id", ""),
        float(data.get("system_kwp") or 5),
        battery_id=data.get("battery_id"),
        goals=data.get("goals") or [],
    )
    return jsonify(result)


@app.route("/api/quotes/parse-text", methods=["POST"])
def api_parse_quote_text():
    data = request.get_json() or {}
    text = data.get("text", "")
    if not text.strip():
        return jsonify({"error": "text required"}), 400
    return jsonify(parse_quote_text(text))


@app.route("/api/suppliers/<supplier_id>/analytics", methods=["GET"])
def api_supplier_analytics(supplier_id):
    if not supplier_authorized(supplier_id, admin_ok=True):
        return jsonify({"error": "Authentication required"}), 401
    supplier = next((s for s in get_suppliers() if s["id"] == supplier_id), None)
    if not supplier:
        return jsonify({"error": "Supplier not found"}), 404
    with db_session() as db:
        all_quotes = [q.to_dict() for q in db.query(Quote).all()]
    quotes = [q for q in all_quotes if supplier_id in (q.get("supplier_ids") or [])]
    slug = supplier.get("intake_slug", "")
    intake_stats = load_json(INTAKE_ANALYTICS_FILE)
    views = 0
    if isinstance(intake_stats, dict) and slug:
        views = int(intake_stats.get(slug, {}).get("views", 0))
    total = len(quotes)
    pending = sum(1 for q in quotes if q.get("status") in ("matched", "received", "pending"))
    conversion = round(total / views * 100, 1) if views > 0 else 0
    return jsonify({
        "total_leads": total,
        "pending_leads": pending,
        "profile_views": views,
        "conversion_rate_pct": conversion,
        "intake_slug": slug,
    })


@app.route("/api/suppliers/<supplier_id>/products/<product_id>", methods=["DELETE"])
def api_supplier_product_delete(supplier_id, product_id):
    if not supplier_authorized(supplier_id, admin_ok=True):
        return jsonify({"error": "Authentication required"}), 401
    existing = supplier_store.get_by_id(supplier_id)
    if not existing:
        return jsonify({"error": "Supplier not found"}), 404
    products = [p for p in (existing.get("products") or []) if p.get("id") != product_id and p.get("name") != product_id]
    existing["products"] = products
    return jsonify(_save_supplier(existing))


@app.route("/api/suppliers/<supplier_id>/price-list/upload", methods=["POST"])
def api_supplier_price_list_upload(supplier_id):
    if not supplier_authorized(supplier_id, admin_ok=True):
        return jsonify({"error": "Authentication required"}), 401
    suppliers = get_suppliers()
    idx = next((i for i, s in enumerate(suppliers) if s["id"] == supplier_id), None)
    if idx is None:
        return jsonify({"error": "Supplier not found"}), 404
    replace = request.args.get("replace") == "1"
    text = ""
    if request.files.get("file"):
        raw = request.files["file"].read()
        text = raw.decode("utf-8-sig", errors="replace")
    elif request.is_json:
        text = (request.get_json() or {}).get("csv_text", "")
    if not text.strip():
        return jsonify({"error": "CSV file or csv_text required"}), 400
    imported, errors = parse_csv_text(text)
    if not imported and errors:
        return jsonify({"error": "Parse failed", "details": errors}), 400
    existing_row = supplier_store.get_by_id(supplier_id)
    if not existing_row:
        return jsonify({"error": "Supplier not found"}), 404
    existing_products = existing_row.get("products") or []
    merged = merge_products(existing_products, imported, replace=replace)
    existing_row["products"] = merged
    saved = _save_supplier(existing_row)
    return jsonify({"ok": True, "imported": len(imported), "total_products": len(merged), "errors": errors, "supplier": saved})


# ── API stubs (Phase 4) ─────────────────────────────────────────────────────

@app.route("/api/stubs/bill-upload", methods=["POST"])
def api_stub_bill_upload():
    return jsonify(stub_bill_upload(request.get_json() or {}))


@app.route("/api/stubs/roof-analysis", methods=["POST"])
def api_stub_roof_analysis():
    return jsonify(stub_roof_analysis(request.get_json() or {}))


@app.route("/api/stubs/financing-offers", methods=["GET"])
def api_stub_financing():
    amount = float(request.args.get("amount") or 0)
    term = int(request.args.get("term_years") or 10)
    return jsonify(stub_financing_offers(amount, term))


@app.route("/api/stubs/incentives", methods=["GET"])
def api_stub_incentives():
    return jsonify(stub_incentives(request.args.get("postcode", "")))


@app.route("/api/stubs/gsa-validate", methods=["GET"])
def api_stub_gsa_validate():
    lat = float(request.args.get("lat", 48.13))
    lon = float(request.args.get("lon", 11.58))
    pvgis_yield = float(request.args.get("pvgis_yield") or 950)
    gsa = get_gsa_yield_estimate(lat, lon)
    return jsonify({"gsa": gsa, "validation": validate_yield(pvgis_yield, gsa.get("specific_yield_kwh_kwp", 0))})


# ── API: Quote Requests ─────────────────────────────────────────────────────

@app.route("/api/quotes", methods=["POST"])
def api_quotes_create():
    data = request.get_json() or {}
    required = ["customer_name", "customer_email", "customer_phone", "customer_postcode"]
    if not all(data.get(f) for f in required):
        return jsonify({"error": "Name, email, phone, and postcode are required", "error_key": "api.error.missing_fields"}), 400

    if not data.get("consent_contact") or not data.get("consent_share_installers"):
        return jsonify({
            "error": "You must consent to be contacted and to share your details with selected installers.",
            "error_key": "api.error.consent_required",
            "code": "consent_required",
        }), 400

    rec = data.get("recommendation", {})
    ci = rec.get("calculator_inputs") or {}
    timeframe = data.get("installation_timeframe") or ci.get("installation_timeframe", "not_sure")
    if timeframe == "not_sure" and not data.get("confirm_serious"):
        return jsonify({
            "error": "Please confirm you are seriously planning PV, or choose an installation timeframe in the calculator.",
            "error_key": "api.error.timeframe_required",
            "code": "timeframe_required",
        }), 400

    lead_inp = build_lead_inp(rec, data)
    suppliers = get_suppliers()
    source_slug = data.get("source_installer_slug") or rec.get("source_installer_slug")
    source_installer = find_supplier_by_slug(source_slug) if source_slug else None
    if source_installer:
        matched = [{**source_installer, "fit_score": 100, "fit_label": "Branded intake", "fit_reasons": ["Direct enquiry via installer form"]}]
        supplier_ids = [source_installer["id"]]
    else:
        matched = match_suppliers(suppliers, lead_inp, rec, limit=8)
        supplier_ids = data.get("supplier_ids") or [s["id"] for s in matched[:5]]

    qualification = evaluate_qualified_lead(rec, data, matched, supplier_ids)
    if not qualification["qualified"]:
        return jsonify({
            "error": "This request does not meet our qualified-lead criteria yet.",
            "error_key": "api.error.not_qualified",
            "code": "not_qualified",
            "qualification": qualification,
            "hint": "Complete your energy use, confirm you can decide for the property, choose a timeframe, and select installers in your area.",
        }), 422

    lead_profile = build_lead_profile(rec, data, matched)
    lead_tier = qualification["tier"]

    quote = {
        "id": f"quote-{uuid.uuid4().hex[:8]}",
        "customer_id": data.get("customer_id", ""),
        "customer_first_name": data.get("customer_first_name", ""),
        "customer_name": data["customer_name"],
        "customer_email": data["customer_email"],
        "customer_phone": data["customer_phone"],
        "customer_postcode": data.get("customer_postcode", ""),
        "customer_town": data.get("customer_town", ""),
        "full_address": data.get("full_address", ""),
        "preferred_contact_time": data.get("preferred_contact_time", ""),
        "owner_status": data.get("owner_status") or ci.get("owner_status", ""),
        "installation_timeframe": timeframe,
        "battery_interest": data.get("battery_interest") or ci.get("battery_interest", "unsure"),
        "financing_interest": data.get("financing_interest") or ci.get("financing_interest", "no"),
        "consent_contact": True,
        "consent_share_installers": True,
        "message": data.get("message", ""),
        "recommendation": rec,
        "lead_profile": lead_profile,
        "qualification": qualification,
        "supplier_ids": supplier_ids,
        "matched_suppliers": [{"id": s["id"], "company_name": s.get("company_name"), "fit_score": s.get("fit_score")} for s in matched if s["id"] in supplier_ids],
        "lead_tier": lead_tier,
        "intake_type": "branded" if source_installer else "marketplace",
        "source_installer_id": source_installer["id"] if source_installer else "",
        "source_installer_slug": source_slug or "",
        "source_installer_name": source_installer.get("company_name") if source_installer else "",
        "status": "matched",
        "status_history": [
            {"status": "received", "at": utc_now_iso()},
            {"status": "matched", "at": utc_now_iso()},
        ],
        "created_at": utc_now_iso(),
    }
    with db_session() as db:
        db.add(Quote(
            id=quote["id"],
            customer_id=quote.get("customer_id", ""),
            customer_email=quote["customer_email"].lower(),
            payload=quote,
            status=quote["status"],
        ))

    supplier_emails = [s.get("email") for s in suppliers if s.get("id") in supplier_ids]
    try:
        notify_quote_request(quote, supplier_emails)
    except Exception:
        pass

    try:
        track_event("quote_request", {
            "quote_id": quote["id"],
            "lead_tier": lead_tier,
            "supplier_count": len(supplier_ids),
            "package_id": rec.get("selected_package_id"),
        })
    except Exception:
        log.debug("analytics track failed", exc_info=True)

    quote["status_timeline"] = build_quote_status(quote)
    return jsonify({"success": True, "quote_id": quote["id"], "quote": quote, "message": "Quote request sent to matched suppliers."}), 201


@app.route("/api/quotes", methods=["GET"])
def api_quotes_list():
    supplier_id = request.args.get("supplier_id")
    customer = get_current_customer()

    if supplier_id:
        if not supplier_authorized(supplier_id, admin_ok=True):
            return jsonify({"error": "Authentication required"}), 401
        with db_session() as db:
            quotes = [row.to_dict() for row in db.query(Quote).all()]
        quotes = [q for q in quotes if supplier_id in q.get("supplier_ids", [])]
    elif customer:
        with db_session() as db:
            q = db.query(Quote).filter(
                (Quote.customer_id == customer.id)
                | (Quote.customer_email == customer.email.lower())
            )
            quotes = [row.to_dict() for row in q.all()]
    else:
        return jsonify({"error": "Authentication required"}), 401

    for q in quotes:
        q["status_timeline"] = build_quote_status(q)
    return jsonify(quotes)


@app.route("/api/quotes/<quote_id>/status", methods=["PUT"])
def api_quote_status(quote_id):
    data = request.get_json() or {}
    new_status = data.get("status")
    if not new_status:
        return jsonify({"error": "status required"}), 400
    supplier_id = get_current_supplier_id()
    if not supplier_id and not admin_authorized():
        return jsonify({"error": "Authentication required"}), 401
    with db_session() as db:
        row = db.get(Quote, quote_id)
        if not row:
            return jsonify({"error": "Quote not found"}), 404
        payload = dict(row.payload or {})
        if supplier_id and supplier_id not in (payload.get("supplier_ids") or []):
            return jsonify({"error": "Not authorized for this quote"}), 403
        payload["status"] = new_status
        payload.setdefault("status_history", []).append({
            "status": new_status,
            "at": utc_now_iso(),
        })
        row.payload = payload
        row.status = new_status
        quote = row.to_dict()
    quote["status_timeline"] = build_quote_status(quote)
    return jsonify(quote)


@app.route("/api/assessments", methods=["POST"])
def api_save_assessment():
    data = request.get_json() or {}
    if not data.get("recommendation"):
        return jsonify({"error": "recommendation required"}), 400
    customer = get_current_customer()
    entry_id = f"assess-{uuid.uuid4().hex[:8]}"
    with db_session() as db:
        row = Assessment(
            id=entry_id,
            customer_id=(customer.id if customer else ""),
            customer_email=(customer.email if customer else (data.get("customer_email") or "")).lower(),
            recommendation=data["recommendation"],
        )
        db.add(row)
        entry = row.to_dict()
    return jsonify(entry), 201


@app.route("/api/assessments", methods=["GET"])
def api_list_assessments():
    customer = get_current_customer()
    if not customer:
        return jsonify({"error": "Authentication required"}), 401

    with db_session() as db:
        q = db.query(Assessment).filter(
            (Assessment.customer_id == customer.id)
            | (Assessment.customer_email == customer.email.lower())
        )
        return jsonify([a.to_dict() for a in q.all()])


@app.route("/api/documents", methods=["GET", "POST"])
def api_documents():
    customer = get_current_customer()
    if request.method == "GET":
        if not customer:
            return jsonify({"error": "Authentication required"}), 401
        with db_session() as db:
            docs = db.query(Document).filter(Document.customer_id == customer.id).all()
            return jsonify([d.to_dict() for d in docs])

    data = request.get_json() or {}
    if not customer:
        return jsonify({"error": "Authentication required"}), 401
    if not data.get("title"):
        return jsonify({"error": "title required"}), 400

    doc_id = f"doc-{uuid.uuid4().hex[:8]}"
    with db_session() as db:
        doc = Document(
            id=doc_id,
            customer_id=customer.id,
            title=data["title"],
            doc_type=data.get("doc_type", "other"),
            notes=data.get("notes", ""),
        )
        db.add(doc)
        return jsonify(doc.to_dict()), 201


@app.route("/api/admin/summary", methods=["GET"])
def api_admin_summary():
    if not admin_authorized():
        return jsonify({"error": "Unauthorized"}), 401
    catalog = load_catalog()
    with db_session() as db:
        return jsonify({
            "customers": db.query(Customer).count(),
            "suppliers": supplier_store.count(),
            "quotes": db.query(Quote).count(),
            "surveys": len(load_json(SURVEYS_FILE)),
            "assessments": db.query(Assessment).count(),
            "subscriptions": db.query(Subscription).count(),
            "ev_dealers": db.query(EvDealer).count(),
            "ev_dealers_pending": db.query(EvDealer).filter(EvDealer.status == "pending").count(),
            "ev_vehicles_published": db.query(EvVehicle).filter(EvVehicle.status == "published").count(),
            "ev_buyer_leads": db.query(EvBuyerLead).count(),
            "products": {
                "panels": len(catalog.get("panels", [])),
                "inverters": len(catalog.get("inverters", [])),
                "batteries": len(catalog.get("batteries", [])),
                "mounting": len(catalog.get("mounting", [])),
            },
        })


@app.route("/api/admin/products", methods=["GET", "PUT"])
def api_admin_products():
    if not admin_authorized():
        return jsonify({"error": "Unauthorized"}), 401
    if request.method == "GET":
        return jsonify(load_catalog())
    data = request.get_json()
    if not isinstance(data, dict) or not any(k in data for k in ("panels", "inverters", "batteries", "mounting")):
        return jsonify({"error": "Invalid catalog payload"}), 400
    save_catalog(data)
    return jsonify({"ok": True, "products": load_catalog()})


# ── Beta analytics & structured installer quotes ────────────────────────────

@app.route("/api/beta/events", methods=["POST"])
def api_beta_events():
    data = request.get_json() or {}
    event_type = (data.get("event_type") or "").strip()
    if not event_type or len(event_type) > 64:
        return jsonify({"error": "event_type required"}), 400
    allowed = {
        "calculator_start", "calculator_complete", "pdf_download", "quote_request",
        "package_select", "page_view",
    }
    if event_type not in allowed:
        return jsonify({"error": "invalid event_type"}), 400
    eid = track_event(event_type, data.get("payload") or {})
    return jsonify({"ok": True, "id": eid})


@app.route("/api/admin/beta-metrics", methods=["GET"])
def api_admin_beta_metrics():
    if not admin_authorized():
        return jsonify({"error": "Unauthorized"}), 401
    return jsonify(beta_metrics_summary())


@app.route("/api/suppliers/<supplier_id>/structured-quotes", methods=["GET", "POST"])
def api_supplier_structured_quotes(supplier_id):
    if request.method == "GET":
        if not supplier_authorized(supplier_id, admin_ok=True):
            return jsonify({"error": "Authentication required"}), 401
        with db_session() as db:
            rows = db.query(InstallerQuote).filter(InstallerQuote.supplier_id == supplier_id).all()
        return jsonify({"items": [r.to_dict() for r in rows]})

    if not supplier_authorized(supplier_id, admin_ok=True):
        return jsonify({"error": "Authentication required"}), 401
    data = request.get_json() or {}
    required = ["system_kwp", "total_eur", "panel_model", "inverter_model"]
    if not all(data.get(f) for f in required):
        return jsonify({"error": "system_kwp, total_eur, panel_model, and inverter_model are required"}), 400
    row = InstallerQuote(
        id=f"iq-{uuid.uuid4().hex[:8]}",
        supplier_id=supplier_id,
        quote_request_id=(data.get("quote_request_id") or "").strip(),
        system_kwp=float(data["system_kwp"]),
        panel_model=data.get("panel_model", ""),
        inverter_model=data.get("inverter_model", ""),
        battery_model=data.get("battery_model", ""),
        warranty_years=int(data["warranty_years"]) if data.get("warranty_years") else None,
        install_weeks=int(data["install_weeks"]) if data.get("install_weeks") else None,
        exclusions=data.get("exclusions", ""),
        total_eur=int(data["total_eur"]),
        notes=data.get("notes", ""),
    )
    with db_session() as db:
        db.add(row)
    return jsonify(row.to_dict()), 201


# ── API: PDF Report ─────────────────────────────────────────────────────────

@app.route("/api/report/pdf", methods=["POST"])
def api_report_pdf():
    data = request.get_json() or {}
    rec = data.get("recommendation", {})
    customer = data.get("customer", {})
    selected = data.get("selected_package") or {}
    buffer = generate_decision_report_pdf(rec, customer, selected, lang=getattr(g, "lang", "en"))
    filename = "solar-entscheidungsbericht.pdf" if getattr(g, "lang", "en") == "de" else "solar-decision-report.pdf"
    return send_file(buffer, mimetype="application/pdf", as_attachment=True, download_name=filename)


@app.route("/api/report/email", methods=["POST"])
def api_report_email():
    data = request.get_json() or {}
    to = (data.get("to") or "").strip()
    if not to or "@" not in to or len(to) > 254:
        return jsonify({"error": "invalid_email"}), 400
    rec = data.get("recommendation", {})
    customer = data.get("customer", {})
    selected = data.get("selected_package") or {}
    lang = getattr(g, "lang", "en")
    buffer = generate_decision_report_pdf(rec, customer, selected, lang=lang)
    buffer.seek(0)
    pdf_bytes = buffer.read()
    filename = "solar-entscheidungsbericht.pdf" if lang == "de" else "solar-decision-report.pdf"
    if lang == "de":
        subject = "Solar Path – Solar-Entscheidungsbericht"
        body = (
            "Anbei der Solar-Vorab-Bewertungsbericht.\n\n"
            "Dies ist nur eine informative Schätzung — endgültige Preise erfordern eine Vor-Ort-Besichtigung."
        )
    else:
        subject = "Solar Path – Solar Decision Report"
        body = (
            "Please find the attached solar pre-assessment report.\n\n"
            "This is an informational estimate only — final pricing requires a site survey."
        )
    result = send_email_with_attachment(to, subject, body, pdf_bytes, filename)
    if not result.get("ok"):
        return jsonify(result), 400
    try:
        track_event("pdf_download", {"to": to, "mode": result.get("mode")})
    except Exception:
        pass
    return jsonify(result)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=FLASK_DEBUG, host="0.0.0.0", port=port)
