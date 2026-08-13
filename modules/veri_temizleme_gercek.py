"""
Gerçek ekspertiz veri seti ('Başvurular(Detaylı).xlsx') için temizleme modülü.
Ham Excel'i haritada gösterilebilir, model eğitilebilir bir DataFrame'e çevirir.
"""

import pandas as pd
import re

# ---------------- KAT SÜTUNU TEMİZLEME ----------------
# Türkçe yazılı kat isimlerini sayıya çeviren sözlük
KAT_SOZLUGU = {
    "zemin": 0, "zemın": 0, "z": 0,
    "bodrum": -1, "bd": -1,
    "birinci": 1, "bir": 1, "ı": 1,
    "ikinci": 2, "iki": 2,
    "üçüncü": 3, "üç": 3,
    "dördüncü": 4, "dort": 4,
    "beşinci": 5, "beş": 5,
    "altıncı": 6, "altı": 6,
    "yedinci": 7, "yedi": 7,
    "sekizinci": 8, "sekiz": 8,
    "dokuzuncu": 9, "dokuz": 9,
    "onuncu": 10, "on": 10,
}


def kat_temizle(kat_degeri):
    """Karışık formattaki kat bilgisini sayıya çevirir. Çözemezse None döner."""
    if pd.isna(kat_degeri):
        return None
    if isinstance(kat_degeri, (int, float)):
        return float(kat_degeri)

    metin = str(kat_degeri).strip().lower()
    metin = metin.replace("i̇", "i")  # Türkçe büyük İ sorunlu karakter düzeltmesi

    # Önce sözlükte tam eşleşme dene
    if metin in KAT_SOZLUGU:
        return float(KAT_SOZLUGU[metin])

    # Metinde saf sayı var mı (örn. '5 KAT' -> 5, ' 1 ' -> 1)
    sayi_eslesme = re.search(r"-?\d+", metin)
    if sayi_eslesme:
        return float(sayi_eslesme.group())

    # Sözlükteki kelimelerden biri metinde geçiyor mu (örn. 'zemin kat')
    for kelime, deger in KAT_SOZLUGU.items():
        if kelime in metin:
            return float(deger)

    return None  # çözülemeyen karışık ifadeler (örn. 'BD. ZM. NOR. ÇATI KT')


def veri_yukle_ve_temizle(excel_yolu: str) -> pd.DataFrame:
    df = pd.read_excel(excel_yolu)

    # Sadece geçerli (iptal edilmemiş) başvuruları al
    df = df[df["Durumu"] == "Etkin"].copy()

    # Sadece Kayseri'ye ait kayıtları al — veride yanlışlıkla karışmış
    # birkaç başka il kaydı (örn. İstanbul, Samsun) var, bunları at.
    df = df[df["İl"].astype(str).str.strip().str.upper().isin(["KAYSERI", "KAYSERİ"])].copy()

    # Sadece KONUT (apartman, villa, gecekondu, mesken) kayıtlarını al.
    # Arsa, tarla, bağ/bahçe, dükkan, sanayi tesisi gibi konut-dışı taşınmazlar
    # farklı bir değerleme mantığı gerektirir, bu prototipin kapsamı dışında.
    df = df[df["Fiili Kullanım Niteliği"].astype(str).str.contains("KONUT", na=False)].copy()

    # Konut tipini (Apartman/Mesken vs Villa) BB Niteliği sütunundan türet.
    # NOT: "Gecekondu" veri setinde hiçbir kayıtta ayrı etiketlenmemiş,
    # bu yüzden ayrıştırılamıyor; hepsi "Apartman/Mesken" içinde kalıyor.
    villa_mi = df["BB Niteliği"].astype(str).str.contains("VİLLA|VILLA", case=False, na=False, regex=True)
    df["konut_tipi"] = villa_mi.map({True: "Villa", False: "Apartman/Mesken"})

    # İhtiyacımız olan sütunları seç
    df = df[[
        "İl", "İlçe", "Mahalle", "Enlem", "Boylam", "Kat",
        "Mevcut Alanı", "Konutun Yapım Yılı", "Konutun Yapı Tarzı",
        "Konutun Yapı Kalitesi", "Adil Piyasa Değeri (Mevcut Durum)",
        "Rapor Tanzim Tarihi", "konut_tipi",
    ]].copy()

    df = df.rename(columns={
        "İl": "il", "İlçe": "ilce", "Mahalle": "mahalle",
        "Enlem": "lat", "Boylam": "lon",
        "Mevcut Alanı": "m2", "Konutun Yapım Yılı": "yapim_yili",
        "Konutun Yapı Tarzı": "yapi_tarzi_kod", "Konutun Yapı Kalitesi": "yapi_kalitesi_kod",
        "Adil Piyasa Değeri (Mevcut Durum)": "fiyat", "Rapor Tanzim Tarihi": "tarih",
    })

    # Kat sütununu normalize et
    df["kat"] = df["Kat"].apply(kat_temizle)
    df = df.drop(columns=["Kat"])

    # Koordinat, m², fiyat eksikse satırı at
    df = df.dropna(subset=["lat", "lon", "m2", "fiyat"])

    # Aykırı değerleri filtrele
    df = df[(df["m2"] > 15) & (df["m2"] < 1000)]
    df = df[(df["fiyat"] > 10_000) & (df["fiyat"] < df["fiyat"].quantile(0.995))]

    # Bina yaşını hesapla (yapım yılı varsa, rapor tarihinin yılına göre)
    df["rapor_yili"] = pd.to_datetime(df["tarih"]).dt.year
    df["bina_yasi"] = df["rapor_yili"] - df["yapim_yili"]
    df.loc[(df["bina_yasi"] < 0) | (df["bina_yasi"] > 150), "bina_yasi"] = None

    # m² başına fiyat
    df["m2_fiyat"] = df["fiyat"] / df["m2"]

    return df.reset_index(drop=True)


if __name__ == "__main__":
    df = veri_yukle_ve_temizle("data/Başvurular(Detaylı) (1).xlsx")
    print("Toplam temiz satır:", len(df))
    print()
    print("İl bazında dağılım:")
    print(df["il"].value_counts())
    print()
    print("Kat doluluk oranı:", round(df["kat"].notna().mean() * 100, 1), "%")
    print("Bina yaşı doluluk oranı:", round(df["bina_yasi"].notna().mean() * 100, 1), "%")
    print()
    print(df[["il", "ilce", "m2", "kat", "bina_yasi", "fiyat", "m2_fiyat", "lat", "lon"]].head(10))

    df.to_csv("data/temiz_veri_gercek.csv", index=False, encoding="utf-8-sig")
    print("\nKaydedildi: data/temiz_veri_gercek.csv")
