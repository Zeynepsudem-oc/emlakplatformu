"""
Resmi Gazete (2.12.1982, Sayı 17886) 'Aşınma Paylarına İlişkin Oranları
Gösteren Cetvel' — bina yaşı ve yapı tipine göre standart yıpranma/aşınma
oranını verir. Gayrimenkul ekspertizinde değerden düşülecek oranı belirler.
"""


YAS_ARALIKLARI = [
    (0, 3), (4, 5), (6, 10), (11, 15), (16, 20),
    (21, 30), (31, 40), (41, 50), (51, 75), (76, None),
]


ASINMA_TABLOSU = {
    "celik_betonarme_karkas": {
        "ad": "Çelik Karkas - Betonarme Karkas Binalar",
        "oranlar": [4, 6, 10, 15, 20, 25, 32, 40, 50, 60],
    },
    "yigma_kagir": {
        "ad": "Yığma Kagir, Yığma Yarı Kagir Binalar",
        "oranlar": [6, 8, 12, 18, 25, 32, 40, 50, 60, 70],
    },
    "ahsap_tas_gecekondu": {
        "ad": "Ahşap, Taş Duvarlı (Çamur Harçlı) Gecekondu Tarz ve Vasfında Binalar",
        "oranlar": [8, 12, 18, 25, 32, 40, 50, 60, 70, 80],
    },
    "kerpic_basit": {
        "ad": "Kerpiç ve Diğer Basit Binalar",
        "oranlar": [10, 17, 25, 35, 45, 55, 65, 75, 85, 95],
    },
}


def yas_araligi_bul(bina_yasi: int) -> int:
    """Bina yaşına göre YAS_ARALIKLARI listesindeki index'i döner."""
    for i, (alt, ust) in enumerate(YAS_ARALIKLARI):
        if ust is None:
            if bina_yasi >= alt:
                return i
        elif alt <= bina_yasi <= ust:
            return i
    return len(YAS_ARALIKLARI) - 1 


def asinma_payi_hesapla(bina_yasi: int, yapi_tipi: str = "celik_betonarme_karkas") -> float:
    """
    Bina yaşı ve yapı tipine göre aşınma yüzdesini (0-100) döner.
    yapi_tipi seçenekleri: 'celik_betonarme_karkas', 'yigma_kagir',
                           'ahsap_tas_gecekondu', 'kerpic_basit'
    """
    if yapi_tipi not in ASINMA_TABLOSU:
        raise ValueError(
            f"Geçersiz yapı tipi: {yapi_tipi}. Seçenekler: {list(ASINMA_TABLOSU.keys())}"
        )
    if bina_yasi < 0:
        bina_yasi = 0

    index = yas_araligi_bul(bina_yasi)
    return float(ASINMA_TABLOSU[yapi_tipi]["oranlar"][index])


def asinma_uygula(deger: float, bina_yasi: int, yapi_tipi: str = "celik_betonarme_karkas") -> dict:
    """
    Bir değere aşınma payını uygular, hem oranı hem de sonucu döner.
    """
    oran = asinma_payi_hesapla(bina_yasi, yapi_tipi)
    asinma_sonrasi = deger * (1 - oran / 100)
    return {
        "asinma_orani_yuzde": oran,
        "asinma_oncesi_deger": deger,
        "asinma_sonrasi_deger": asinma_sonrasi,
        "yapi_tipi_adi": ASINMA_TABLOSU[yapi_tipi]["ad"],
    }


if __name__ == "__main__":
    
    print(asinma_uygula(5_000_000, bina_yasi=40, yapi_tipi="celik_betonarme_karkas"))
    print(asinma_uygula(5_000_000, bina_yasi=5, yapi_tipi="yigma_kagir"))
    print(asinma_uygula(5_000_000, bina_yasi=80, yapi_tipi="kerpic_basit"))
