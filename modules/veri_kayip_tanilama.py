"""
modules/veri_kayip_tanilama.py
-------------------------------------------------------------------
model_egit.py'deki veri_hazirla() fonksiyonu, gerekli sütunlardan
herhangi biri boş (NaN) olan satırları TAMAMEN atıyor. Bu script,
hangi sütunun ne kadar veri kaybına yol açtığını gösterir; böylece
"impute mi edelim, yoksa gerçekten silinmeli mi" kararını verebiliriz.

Çalıştırmak için: python -m modules.veri_kayip_tanilama
"""

import pandas as pd

from modules.model_egit import HEDEF_SUTUN, KATEGORIK_OZNITELIKLER, SAYISAL_OZNITELIKLER


def veri_kayip_raporu(veri_yolu: str = "data/temiz_veri_gercek.csv"):
    df = pd.read_csv(veri_yolu)
    toplam = len(df)
    print(f"Toplam ham satır sayısı: {toplam}\n")

    gerekli_sutunlar = SAYISAL_OZNITELIKLER + KATEGORIK_OZNITELIKLER + [HEDEF_SUTUN]

    print("Sütun bazında boş (NaN) değer sayısı ve oranı:")
    print("-" * 60)
    for sutun in gerekli_sutunlar:
        if sutun not in df.columns:
            print(f"  {sutun:20s} -> SÜTUN VERİDE YOK!")
            continue
        bos_sayisi = df[sutun].isna().sum()
        oran = bos_sayisi / toplam * 100
        print(f"  {sutun:20s} -> {bos_sayisi:6d} boş  (%{oran:.1f})")

    print("\n" + "-" * 60)
    kalan = df.dropna(subset=[s for s in gerekli_sutunlar if s in df.columns])
    print(f"dropna sonrası kalan satır: {len(kalan)} / {toplam}  (%{len(kalan)/toplam*100:.1f} korunuyor)")

    print("\nİlçe bazında ham vs. dropna-sonrası satır sayısı:")
    print("-" * 60)
    if "ilce" in df.columns:
        ham_ilce = df["ilce"].value_counts()
        kalan_ilce = kalan["ilce"].value_counts()
        karsilastirma = pd.DataFrame({"ham": ham_ilce, "dropna_sonrasi": kalan_ilce}).fillna(0).astype(int)
        karsilastirma["kayip_yuzde"] = (
            (karsilastirma["ham"] - karsilastirma["dropna_sonrasi"]) / karsilastirma["ham"] * 100
        ).round(1)
        print(karsilastirma.sort_values("kayip_yuzde", ascending=False).to_string())


if __name__ == "__main__":
    veri_kayip_raporu()
