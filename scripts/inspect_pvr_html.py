import re
import requests

r = requests.get(
    "https://www.photovoltaik-vergleichsrechner.de/landkreis-rottal-inn",
    headers={"User-Agent": "SolarPath/1.0"},
    timeout=30,
)
html = r.text
idx = html.find("Elektro Niedermeier")
print(html[idx - 300 : idx + 400])
print("---")
for m in re.finditer(r'<a[^>]+href="([^"]+)"[^>]*>([^<]{5,80})</a>', html):
    href, text = m.groups()
    if "pfarrkirchen" in href or "niedermeier" in href.lower():
        print(href, "|", text.strip())
