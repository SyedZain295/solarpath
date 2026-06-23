import requests

query = """[out:json][timeout:25];
(
  node["craft"="solar_installer"](48.0,11.0,49.0,13.0);
  way["craft"="solar_installer"](48.0,11.0,49.0,13.0);
  node["shop"="solar"](48.0,11.0,49.0,13.0);
);
out center tags;"""

for url in [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]:
    try:
        r = requests.post(
            url,
            data=query.encode(),
            headers={"Content-Type": "text/plain", "User-Agent": "SolarPath/1.0"},
            timeout=60,
        )
        print(url, r.status_code, len(r.json().get("elements", [])))
    except Exception as e:
        print(url, "FAIL", e)
