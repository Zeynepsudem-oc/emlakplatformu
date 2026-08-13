"""
Fiyatları (veya m² fiyatlarını) TCMB Konut Fiyat Endeksi (KFE) kullanarak
'bugünün TL'sine' taşıyan modül. Zaman içinde farklı tarihlerde toplanmış
kayıtları aynı ölçekte, karşılaştırılabilir hale getirir.

Neden gerekli: temiz_veri_gercek.csv içindeki kayıtlar 2019'dan bugüne kadar
farklı tarihlerde toplanmış. Ham fiyatları doğrudan ortalamak ya da bir
modele öğretmek, enflasyon farkını "gerçek fiyat farkı" gibi gösterir ve
hem emsal ortalamasını hem de bir ML modelini sistematik olarak yanıltır.
"""

import pandas as pd


def kfe_carpanlarini_hesapla(tarihler: pd.Series, kfe_df: pd.DataFrame) -> pd.Series:
    """
    Her tarih için 'o tarihten bugüne' çarpanını (guncel_kfe / o_tarihteki_kfe)
    vektörel olarak hesaplar. apply()/iterrows() yerine merge_asof kullanır,
    binlerce satırda çok daha hızlıdır (projenin geri kalanındaki vektörel
    yaklaşımla aynı mantık — bkz. appy.py'deki haversine hesabı).
    """
    kfe_df = kfe_df.copy()
    kfe_df["tarih"] = pd.to_datetime(kfe_df["tarih"])
    kfe_df = kfe_df.sort_values("tarih").reset_index(drop=True)

    gecici = pd.DataFrame({"tarih": pd.to_datetime(tarihler)}).reset_index()

    # merge_asof boş (NaT) tarihlerle çalışamıyor; bu satırları ayrı tutup
    # sona NaN çarpan olarak geri ekliyoruz (satır silinmiyor, sadece
    # o satırın çarpanı hesaplanamıyor).
    tarihi_bos = gecici["tarih"].isna()
    if tarihi_bos.any():
        print(f"Uyarı: {tarihi_bos.sum()} kayıtta tarih boş, bu kayıtlar için zaman düzeltmesi yapılamıyor.")

    gecici_dolu = gecici[~tarihi_bos].sort_values("tarih")
    gecici_bos = gecici[tarihi_bos].copy()
    gecici_bos["kfe"] = pd.NA

    eslesme = pd.merge_asof(gecici_dolu, kfe_df, on="tarih", direction="backward")

    eslesmeyen = eslesme["kfe"].isna().sum()
    if eslesmeyen > 0:
        print(
            f"Uyarı: {eslesmeyen} kayıt için KFE tarihinden önceki veri "
            f"bulunamadı, en eski KFE değeriyle dolduruluyor."
        )
        eslesme["kfe"] = eslesme["kfe"].fillna(kfe_df["kfe"].iloc[0])

    guncel_kfe = kfe_df["kfe"].iloc[-1]
    eslesme["carpan"] = guncel_kfe / eslesme["kfe"]
    gecici_bos["carpan"] = pd.NA

    birlesik = pd.concat([eslesme[["index", "carpan"]], gecici_bos[["index", "carpan"]]])
    birlesik = birlesik.set_index("index").sort_index()
    return birlesik["carpan"]


def dataframeyi_bugune_tasi(
    df: pd.DataFrame,
    kfe_df: pd.DataFrame,
    tarih_sutunu: str = "tarih",
    deger_sutunlari: list = None,
) -> pd.DataFrame:
    """
    df içindeki belirtilen sütunları (varsayılan: fiyat, m2_fiyat) her satırın
    kendi tarihine göre bugünün KFE endeksine taşır. Sonuçlar '<sutun>_guncel'
    adıyla yeni sütunlar olarak eklenir; orijinal sütunlar değiştirilmez.
    """
    if deger_sutunlari is None:
        deger_sutunlari = [s for s in ["fiyat", "m2_fiyat"] if s in df.columns]

    df = df.copy()
    df["_kfe_carpani"] = kfe_carpanlarini_hesapla(df[tarih_sutunu], kfe_df)

    for sutun in deger_sutunlari:
        df[f"{sutun}_guncel"] = df[sutun] * df["_kfe_carpani"]

    return df


if __name__ == "__main__":
    df = pd.read_csv("data/temiz_veri_gercek.csv")
    kfe_df = pd.read_csv("data/kfe_temiz.csv")

    df_guncel = dataframeyi_bugune_tasi(df, kfe_df)

    print("Örnek karşılaştırma (ham vs. bugüne taşınmış m² fiyatı):")
    print(df_guncel[["tarih", "m2_fiyat", "m2_fiyat_guncel"]].sample(10))

    df_guncel.to_csv("data/temiz_veri_gercek_guncel.csv", index=False, encoding="utf-8-sig")
    print("\nKaydedildi: data/temiz_veri_gercek_guncel.csv")
