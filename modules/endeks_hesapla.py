"""
TCMB Konut Fiyat Endeksi (KFE) ile geçmiş bir değeri güncel değere taşır.
data/kfe_temiz.csv formatı: tarih (YYYY-MM-01), kfe (endeks değeri)
"""

import pandas as pd


def kfe_ile_guncelle(eski_deger: float, eski_tarih: str, kfe_df: pd.DataFrame) -> float:
    """
    eski_deger: güncellenecek tutar (₺)
    eski_tarih: 'YYYY-MM' veya 'YYYY-MM-DD' formatında string
    kfe_df: kfe_temiz.csv'den okunmuş DataFrame (tarih, kfe sütunlu)
    """
    hedef_tarih = pd.to_datetime(eski_tarih).replace(day=1)

    kfe_df = kfe_df.copy()
    kfe_df["tarih"] = pd.to_datetime(kfe_df["tarih"])

    # Tam ayı bulamazsak en yakın (önceki) aya bak
    uygun_satirlar = kfe_df[kfe_df["tarih"] <= hedef_tarih]
    if uygun_satirlar.empty:
        raise ValueError(f"{eski_tarih} için KFE verisi bulunamadı (veri {kfe_df['tarih'].min()} sonrasını kapsıyor).")
    eski_endeks = uygun_satirlar.iloc[-1]["kfe"]

    guncel_endeks = kfe_df.iloc[-1]["kfe"]
    guncel_tarih = kfe_df.iloc[-1]["tarih"]

    guncel_deger = eski_deger * (guncel_endeks / eski_endeks)
    return {
        "guncel_deger": guncel_deger,
        "eski_endeks": eski_endeks,
        "guncel_endeks": guncel_endeks,
        "guncel_endeks_tarihi": guncel_tarih.strftime("%Y-%m"),
        "artis_orani_yuzde": (guncel_endeks / eski_endeks - 1) * 100,
    }


if __name__ == "__main__":
    kfe_df = pd.read_csv("data/kfe_temiz.csv")
    sonuc = kfe_ile_guncelle(1_000_000, "2019-01", kfe_df)
    print(sonuc)
