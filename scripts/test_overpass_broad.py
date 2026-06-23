import requests

# Broader OSM query: solar installers + electricians with solar in name
query = """[out:json][timeout:45];
(
  node["craft"="solar_installer"](47.2,5.8,55.2,15.2);
  way["craft"="solar_installer"](47.2,5.8,55.2,15.2);
  node["shop"="solar"](47.2,5.8,55.2,15.2);
  way["shop"="solar"](47.2,5.8,55.2,15.2);
  node["craft"="electrician"]["name"~"Solar|Photovoltaik|photovoltaik|Solartechnik",i](47.2,5.8,55.2,15.2);
  way["craft"="electrician"]["name"~"Solar|Photovoltaik|photovoltaik|Solartechnik",i](47.2,5.8,55.2,15.2);
);
out center tags;"""

r = requests.post(
    "https://overpass-api.de/api/interpreter",
    data=query.encode(),
    headers={"Content-Type": "text/plain", "User-Agent": "SolarPath/1.0"},
    timeout=120,
)
print("status", r.status_code)
els = r.json().get("elements", [])
print("count", len(els))
for e in els[:15]:
    t = e.get("tags", {})
    print(t.get("name"), t.get("craft") or t.get("shop"), t.get("addr:postcode"))
