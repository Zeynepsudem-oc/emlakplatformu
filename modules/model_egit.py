"""
Bugüne taşınmış (KFE düzeltmeli) veriyle m² fiyatı tahmin eden model eğitir.
Konum (lat/lon), m², kat, bina yaşı ve yapı özelliklerini kullanır.

piyasa_modeli.py'nin yerini alır: buradaki sütun isimleri projenin geri
kalanıyla (lat, lon, m2, kat, bina_yasi, ilce...) tutarlı ve eğitim +
gerçek kullanımda (appy.py) aynı isimler kullanılır.

Çalıştırmak için: python -m modules.model_egit
Gereksinim: pip install scikit-learn joblib
"""

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_absolute_percentage_error
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from modules.zaman_normalizasyon import dataframeyi_bugune_tasi

SAYISAL_OZNITELIKLER = [
    "lat", "lon", "m2", "kat", "bina_yasi",
    "kat_bilinmiyor", "bina_yasi_bilinmiyor",
]
KATEGORIK_OZNITELIKLER = ["ilce", "yapi_tarzi_kod", "yapi_kalitesi_kod"]
HEDEF_SUTUN = "m2_fiyat_guncel"

_CEKIRDEK_ZORUNLU_SUTUNLAR = ["lat", "lon", "m2", "ilce"]


def veri_hazirla(veri_yolu: str, kfe_yolu: str) -> pd.DataFrame:
    df = pd.read_csv(veri_yolu)
    kfe_df = pd.read_csv(kfe_yolu)

    df["tarih"] = pd.to_datetime(df["tarih"])
    df = dataframeyi_bugune_tasi(df, kfe_df)

    # 1) Çekirdek sütunlar + hedef sütun + tarih boşsa satır gerçekten
    #    kullanılamaz -- bunlar için dropna makul.
    df = df.dropna(subset=_CEKIRDEK_ZORUNLU_SUTUNLAR + [HEDEF_SUTUN, "tarih"])

    # 2) Sayısal ama sık boş olan sütunlar: medyanla doldur + "bilinmiyor"
    #    bayrağı ekle (silme, doldur).
    for sutun in ["bina_yasi", "kat"]:
        bayrak_sutun = f"{sutun}_bilinmiyor"
        df[bayrak_sutun] = df[sutun].isna().astype(int)
        medyan = df[sutun].median()
        df[sutun] = df[sutun].fillna(medyan)

    # 3) Kategorik ama sık boş olan sütunlar: "Bilinmiyor" adında yeni
    #    bir kategori olarak işaretle (silme, doldur).
    for sutun in ["yapi_tarzi_kod", "yapi_kalitesi_kod"]:
        df[sutun] = df[sutun].fillna("Bilinmiyor").astype(str)

    return df.sort_values("tarih").reset_index(drop=True)


def zaman_bazli_ayir(df: pd.DataFrame, test_orani: float = 0.2):
    """
    ÖNEMLİ: Rastgele train/test ayırma YAPMIYORUZ. Veri tarihe göre sıralı
    geldiği için son %test_orani'yi test seti yapıyoruz. Böylece model
    "geleceği görerek" değerlendirilmiş olmuyor — gerçek kullanım senaryosunu
    (geçmiş veriyle eğitip yeni bir talebi tahmin etmek) simüle ediyoruz.
    Rastgele split kullansaydık, model dolaylı olarak gelecekteki fiyat
    seviyesini "görmüş" olur ve test skoru olduğundan iyi çıkar.
    """
    kesme_index = int(len(df) * (1 - test_orani))
    egitim = df.iloc[:kesme_index]
    test = df.iloc[kesme_index:]
    return egitim, test


def pipeline_olustur() -> Pipeline:
    on_isleme = ColumnTransformer(transformers=[
        ("sayisal", "passthrough", SAYISAL_OZNITELIKLER),
        ("kategorik", OneHotEncoder(handle_unknown="ignore"), KATEGORIK_OZNITELIKLER),
    ])

    model = RandomForestRegressor(
        n_estimators=400,
        max_depth=None,
        min_samples_leaf=3,
        random_state=42,
        n_jobs=-1,
    )

    return Pipeline(steps=[("on_isleme", on_isleme), ("model", model)])


def model_egit_ve_degerlendir(
    veri_yolu: str = "data/temiz_veri_gercek.csv",
    kfe_yolu: str = "data/kfe_temiz.csv",
    model_cikti_yolu: str = "data/m2_fiyat_modeli.joblib",
):
    df = veri_hazirla(veri_yolu, kfe_yolu)
    egitim, test = zaman_bazli_ayir(df)

    ozellik_sutunlari = SAYISAL_OZNITELIKLER + KATEGORIK_OZNITELIKLER
    X_egitim, y_egitim = egitim[ozellik_sutunlari], egitim[HEDEF_SUTUN]
    X_test, y_test = test[ozellik_sutunlari], test[HEDEF_SUTUN]

    pipeline = pipeline_olustur()
    pipeline.fit(X_egitim, y_egitim)

    tahminler = pipeline.predict(X_test)
    mae = mean_absolute_error(y_test, tahminler)
    mape = mean_absolute_percentage_error(y_test, tahminler) * 100

    print(f"Eğitim satır sayısı: {len(egitim)} | Test satır sayısı: {len(test)}")
    print(f"Test tarih aralığı: {test['tarih'].min().date()} -> {test['tarih'].max().date()}")
    print(f"MAE  (ortalama mutlak hata): {mae:,.0f} ₺/m²")
    print(f"MAPE (ortalama yüzde hata): %{mape:.1f}")

    # Referans karşılaştırma: "her yerde sabit ortalama m² fiyatı tahmin et"
    # modeline göre ne kadar iyiyiz? Model bunun belirgin altında kalmalı,
    # yoksa lat/lon/kat gibi özellikler gerçekte bir şey öğretmiyor demektir.
    naive_tahmin = np.full_like(y_test, y_egitim.mean(), dtype=float)
    naive_mape = mean_absolute_percentage_error(y_test, naive_tahmin) * 100
    print(f"Kıyasla naive (sabit ortalama) MAPE: %{naive_mape:.1f}")

    joblib.dump(pipeline, model_cikti_yolu)
    print(f"\nModel kaydedildi: {model_cikti_yolu}")

    return pipeline


if __name__ == "__main__":
    model_egit_ve_degerlendir()
