"""
Bu scripti kendi bilgisayarınızda terminalde çalıştırın:
    python overpass_test.py

Hangi Overpass sunucusuna erişebildiğinizi gösterir.
"""
import requests

urls = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.openstreetmap.ru/api/interpreter",
    "https://lz4.overpass-api.de/api/interpreter",
]

test_sorgu = "[out:json][timeout:15];node(around:500,38.4,35.5)[amenity=school];out count;"

for url in urls:
    print(f"\n--- Test ediliyor: {url} ---")
    try:
        r = requests.post(url, data={"data": test_sorgu}, timeout=15)
        print("Durum kodu:", r.status_code)
        print("Yanıt (ilk 200 karakter):", r.text[:200])
    except Exception as e:
        print("HATA:", type(e).__name__, "-", e)
