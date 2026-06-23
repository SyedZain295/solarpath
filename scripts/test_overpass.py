import requests

query = """
[out:json][timeout:120];
area["ISO3166-1"="DE"]["admin_level"=2]->.de;
(
  node["craft"="solar_installer"](area.de);
  way["craft"="solar_installer"](area.de);
  node["shop"="solar"](area.de);
  way["shop"="solar"](area.de);
);
out center;
"""
r = requests.post("https://overpass-api.de/api/interpreter", data={"data": query}, timeout=180)
data = r.json()
elements = data.get("elements", [])
print("total", len(elements))
for e in elements[:5]:
    tags = e.get("tags", {})
    lat = e.get("lat") or e.get("center", {}).get("lat")
    lon = e.get("lon") or e.get("center", {}).get("lon")
    print(tags.get("name"), tags.get("addr:postcode"), lat, lon)
