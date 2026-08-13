"""
TCMB Konut Fiyat Endeksi (KFE) verisini temizler.
Ham Excel'deki boş satırları (bölüm ayraçları, henüz açıklanmamış aylar) çıkarır.
"""

import pandas as pd


def kfe_yukle_ve_temizle(excel_yolu: str) -> pd.DataFrame:
    df = pd.read_excel(excel_yolu)

    # Sütun isimlerini normalize et (orijinali 'Tarih\nDate' şeklinde geliyor)
    df = df.rename(columns={df.columns[0]: "tarih", df.columns[1]: "kfe"})

    # Tarih veya KFE değeri boş olan satırları at (bölüm ayraçları / henüz açıklanmamış aylar)
    df = df.dropna(subset=["tarih", "kfe"])

    df["tarih"] = pd.to_datetime(df["tarih"])
    df = df.sort_values("tarih").reset_index(drop=True)

    return df


if __name__ == "__main__":
    df = kfe_yukle_ve_temizle("data/kfe.xlsx")
    print("Toplam temiz satır:", len(df))
    print("Tarih aralığı:", df["tarih"].min().strftime("%Y-%m"), "->", df["tarih"].max().strftime("%Y-%m"))
    print()
    print(df.head())
    print("...")
    print(df.tail())

    df.to_csv("data/kfe_temiz.csv", index=False, encoding="utf-8-sig")
    print("\nKaydedildi: data/kfe_temiz.csv")
