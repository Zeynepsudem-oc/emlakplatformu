"""
modules/ek_ozellikler.py
-------------------------------------------------------------------
Değerleme sonucunu tamamlayan dört ek özellik:
  1) Kredi/Mortgage Hesaplayıcı
  2) Deprem Yönetmeliği Uyarısı (yapım yılına göre)
  3) Kira Getirisi Tahmini (kullanıcı tanımlı varsayımsal orana göre)
  4) Yakın Çevre Puanı (OpenStreetMap Overpass API - okul/hastane/durak/market)
"""

import requests


# =========================================================================
# 1) KREDİ / MORTGAGE HESAPLAYICI
# =========================================================================

def kredi_hesapla(deger: float, pesinat_orani: float, yillik_faiz_orani: float, vade_ay: int) -> dict:
    """
    Standart eşit taksitli (annüite) kredi hesaplaması yapar.
    pesinat_orani: 0-100 arası yüzde (örn. 20 -> %20 peşinat)
    yillik_faiz_orani: 0-100 arası yüzde (örn. 3.5 -> yıllık %3.5, aylık bileşik uygulanır)
    vade_ay: kredi vadesi (ay)
    """
    pesinat_tutari = deger * (pesinat_orani / 100)
    kredi_tutari = deger - pesinat_tutari

    aylik_faiz = (yillik_faiz_orani / 100) / 12

    if vade_ay <= 0:
        return {
            "pesinat_tutari": pesinat_tutari, "kredi_tutari": kredi_tutari,
            "aylik_taksit": 0.0, "toplam_odeme": 0.0, "toplam_faiz": 0.0,
        }

    if aylik_faiz == 0:
        aylik_taksit = kredi_tutari / vade_ay
    else:
        aylik_taksit = kredi_tutari * aylik_faiz * (1 + aylik_faiz) ** vade_ay / (
            (1 + aylik_faiz) ** vade_ay - 1
        )

    toplam_odeme = aylik_taksit * vade_ay
    toplam_faiz = toplam_odeme - kredi_tutari

    return {
        "pesinat_tutari": pesinat_tutari,
        "kredi_tutari": kredi_tutari,
        "aylik_taksit": aylik_taksit,
        "toplam_odeme": toplam_odeme,
        "toplam_faiz": toplam_faiz,
    }


# =========================================================================
# 2) DEPREM YÖNETMELİĞİ UYARISI
# =========================================================================

def deprem_yonetmeligi_kontrol(yapim_yili) -> dict:
    """
    Yapım yılına göre binanın hangi deprem yönetmeliği döneminde inşa
    edildiğini kaba olarak sınıflandırır. Bu bir mühendislik değerlendirmesi
    DEĞİLDİR, sadece yapım yılına dayalı genel bir bilgilendirmedir.
    """
    if yapim_yili is None or (isinstance(yapim_yili, float) and yapim_yili != yapim_yili):  # NaN kontrolü
        return {
            "seviye": "bilinmiyor",
            "baslik": "Yapım Yılı Bilinmiyor",
            "mesaj": "Bina yapım yılı verisi olmadığı için deprem yönetmeliği dönemi belirlenemiyor.",
            "renk": "gray",
        }

    yil = int(yapim_yili)

    if yil < 1998:
        return {
            "seviye": "yuksek_risk",
            "baslik": f"⚠️ {yil} — Eski Yönetmelik Dönemi",
            "mesaj": (
                "Bu bina, 1998 Deprem Yönetmeliği'nden ÖNCE inşa edilmiş görünüyor. "
                "Bu dönemdeki yapılar güncel deprem standartlarını karşılamayabilir. "
                "Kesin bilgi için bir inşaat mühendisinden deprem güvenliği raporu (risk analizi) almanızı öneririz."
            ),
            "renk": "red",
        }
    elif yil < 2019:
        return {
            "seviye": "orta_risk",
            "baslik": f"🟡 {yil} — 1998/2007 Yönetmeliği Dönemi",
            "mesaj": (
                "Bu bina, 1998 veya 2007 Deprem Yönetmeliği döneminde inşa edilmiş. "
                "2019'da yürürlüğe giren güncel Türkiye Bina Deprem Yönetmeliği'nden önceki "
                "standartlara tabi olabilir. Detaylı bilgi için yapı denetim kayıtlarını kontrol edin."
            ),
            "renk": "orange",
        }
    else:
        return {
            "seviye": "guncel",
            "baslik": f"✅ {yil} — Güncel Yönetmelik Dönemi",
            "mesaj": (
                "Bu bina, 2019'da yürürlüğe giren güncel Türkiye Bina Deprem Yönetmeliği "
                "döneminde inşa edilmiş görünüyor."
            ),
            "renk": "green",
        }


# =========================================================================
# 3) KİRA GETİRİSİ TAHMİNİ
# =========================================================================

def kira_getirisi_hesapla(deger: float, yillik_brut_getiri_orani: float) -> dict:
    """
    Kullanıcının belirlediği varsayımsal yıllık brüt kira getiri oranına göre
    (örn. %4) aylık kira tahmini ve geri ödeme (amortisman) süresini hesaplar.

    NOT: Veri setinde gerçek kira verisi YOK, bu yüzden gerçek piyasa kira
    verisine dayanmıyor -- kullanıcının kendi varsayımına dayalı bir hesaplama
    aracıdır, kesin bir piyasa tahmini değildir.
    """
    if deger is None or deger <= 0 or yillik_brut_getiri_orani <= 0:
        return {"aylik_kira_tahmini": 0.0, "yillik_kira_geliri": 0.0, "geri_odeme_suresi_yil": None}

    yillik_kira_geliri = deger * (yillik_brut_getiri_orani / 100)
    aylik_kira_tahmini = yillik_kira_geliri / 12
    geri_odeme_suresi_yil = deger / yillik_kira_geliri if yillik_kira_geliri > 0 else None

    return {
        "aylik_kira_tahmini": aylik_kira_tahmini,
        "yillik_kira_geliri": yillik_kira_geliri,
        "geri_odeme_suresi_yil": geri_odeme_suresi_yil,
    }


# =========================================================================
# 4) YAKIN ÇEVRE PUANI (OpenStreetMap Overpass API)
# =========================================================================

OVERPASS_URLS = [
    "https://overpass.kumi.systems/api/interpreter",   # testte çalıştı (sadece User-Agent istiyordu)
    "https://overpass-api.de/api/interpreter",          # yedek (bazen yavaş/yoğun)
    "https://overpass.openstreetmap.ru/api/interpreter",  # yedek
]

_HEADERS = {
    # Bazı Overpass mirror'ları anlamlı bir User-Agent olmadan isteği reddediyor (429/406).
    "User-Agent": "GayrimenkulDegerlemeApp/1.0 (kisisel proje; iletisim: zeynep@example.com)",
}

_POI_KATEGORILERI = {
    "okul": '["amenity"~"school|kindergarten|university|college"]',
    "saglik": '["amenity"~"hospital|clinic|pharmacy|doctors"]',
    "toplu_tasima": '["highway"="bus_stop"]',
    "market": '["shop"~"supermarket|convenience"]',
    "park": '["leisure"="park"]',
}

_AGIRLIKLAR = {"okul": 25, "saglik": 25, "toplu_tasima": 25, "market": 15, "park": 10}
_DOYMA_SAYISI = {"okul": 3, "saglik": 2, "toplu_tasima": 5, "market": 3, "park": 2}


def yakin_cevre_puani_hesapla(lat: float, lon: float, yaricap_m: int = 1000) -> dict:
    """
    Verilen konumun yaricap_m metre çevresindeki okul, sağlık tesisi,
    toplu taşıma durağı, market ve park sayısını OpenStreetMap Overpass API
    üzerinden çeker, bunlardan 0-100 arası bir "yaşanabilirlik puanı" üretir.

    Birden fazla Overpass sunucusu (mirror) sırayla denenir; biri
    reddederse/zaman aşımına uğrarsa diğeri denenir. İsteklere anlamlı
    bir User-Agent başlığı eklenir (bazı sunucular bunu zorunlu tutuyor).

    Tüm sunuculara erişilemezse None döner, hata detayını konsola yazar.
    """
    import requests

    sayimlar = {kategori: 0 for kategori in _POI_KATEGORILERI}
    son_hata = None

    for base_url in OVERPASS_URLS:
        try:
            for kategori, filtre in _POI_KATEGORILERI.items():
                tek_sorgu = (
                    f"[out:json][timeout:25];"
                    f"node(around:{yaricap_m},{lat},{lon}){filtre};"
                    f"out count;"
                )
                yanit = requests.post(
                    base_url,
                    data={"data": tek_sorgu},
                    headers=_HEADERS,
                    timeout=30,
                )
                yanit.raise_for_status()
                veri = yanit.json()
                elemanlar = veri.get("elements", [])
                adet = int(elemanlar[0].get("tags", {}).get("total", 0)) if elemanlar else 0
                sayimlar[kategori] = adet

            son_hata = None
            break  # bu mirror ile tüm kategoriler başarıyla çekildi

        except Exception as e:
            son_hata = e
            print(f"[yakin_cevre_puani_hesapla] '{base_url}' başarısız: {e}")
            continue

    if son_hata is not None:
        import traceback
        print("YAKIN ÇEVRE HATASI (tüm mirror'lar başarısız):", son_hata)
        traceback.print_exc()
        return None

    toplam_puan = 0.0
    for kategori, adet in sayimlar.items():
        doyma = _DOYMA_SAYISI[kategori]
        oran = min(adet / doyma, 1.0) if doyma > 0 else 0.0
        toplam_puan += oran * _AGIRLIKLAR[kategori]

    return {
        "puan": round(toplam_puan, 1),
        "detaylar": sayimlar,
        "yaricap_m": yaricap_m,
    }
