"""
Adres -> koordinat çevirme (geocoding) modülü.
Nominatim (OpenStreetMap) ücretsiz servisini kullanır.
"""

import math
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
import re

_geocoder = Nominatim(user_agent="gayrimenkul_degerleme_projesi")

_KOORDINAT_DESENI = re.compile(
    r"^\s*(-?\d{1,3}\.\d+)\s*[,\s]\s*(-?\d{1,3}\.\d+)\s*$"
)


def koordinat_mi(metin: str):
    if not metin:
        return None
    eslesme = _KOORDINAT_DESENI.match(metin.strip())
    if eslesme:
        lat, lon = float(eslesme.group(1)), float(eslesme.group(2))
        if -90 <= lat <= 90 and -180 <= lon <= 180:
            return lat, lon
    return None


def adresi_koordinata_cevir(adres: str):
    if not adres or not adres.strip():
        return None

    koordinat = koordinat_mi(adres)
    if koordinat:
        lat, lon = koordinat
        return {"lat": lat, "lon": lon, "tam_adres": f"Koordinat: {lat:.5f}, {lon:.5f}"}

    try:
        sonuc = _geocoder.geocode(f"{adres}, Türkiye", timeout=10)
        if sonuc:
            return {"lat": sonuc.latitude, "lon": sonuc.longitude, "tam_adres": sonuc.address}
        return None
    except (GeocoderTimedOut, GeocoderServiceError):
        return None


def haversine_mesafe_km(lat1, lon1, lat2, lon2):
    R = 6371
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def en_yakin_ilceyi_bul(lat, lon, ilce_ozet_df):
    mesafeler = ilce_ozet_df.apply(
        lambda row: haversine_mesafe_km(lat, lon, row["lat"], row["lon"]), axis=1
    )
    en_yakin_index = mesafeler.idxmin()
    return ilce_ozet_df.loc[en_yakin_index], mesafeler.loc[en_yakin_index]
