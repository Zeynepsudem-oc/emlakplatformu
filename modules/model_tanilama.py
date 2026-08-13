"""
modules/model_tanilama.py
-------------------------------------------------------------------
1) Mevcut RandomForest modelinin İLÇE BAZINDA hata payını gösterir
   (hangi ilçelerde model kötü tahmin yapıyor, veri azlığı mı sorun).
2) Aynı veriyle HistGradientBoostingRegressor (scikit-learn içinde
   hazır gelir, ekstra kurulum gerekmez) eğitip RandomForest ile
   karşılaştırır. Genelde tablo verisinde RF'den daha iyi genelleme
   yapar, özellikle küçük alt gruplarda (az veri olan ilçeler).

Çalıştırmak için: python -m modules.model_tanilama
"""

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_absolute_percentage_error
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from modules.model_egit import (
    HEDEF_SUTUN,
    KATEGORIK_OZNITELIKLER,
    SAYISAL_OZNITELIKLER,
    veri_hazirla,
    zaman_bazli_ayir,
)


def ilce_bazli_hata_raporu(egitim: pd.DataFrame, test: pd.DataFrame, tahminler: np.ndarray):
    test = test.copy()
    test["tahmin"] = tahminler
    test["mutlak_hata_yuzde"] = (
        (test["tahmin"] - test[HEDEF_SUTUN]).abs() / test[HEDEF_SUTUN] * 100
    )

    egitim_sayilari = egitim["ilce"].value_counts()

    rapor = (
        test.groupby("ilce")
        .agg(
            test_satir=("tahmin", "count"),
            ortalama_mape=("mutlak_hata_yuzde", "mean"),
        )
        .assign(egitim_satir=lambda d: d.index.map(egitim_sayilari).fillna(0).astype(int))
        .sort_values("ortalama_mape", ascending=False)
    )
    return rapor


def model_karsilastir(
    veri_yolu: str = "data/temiz_veri_gercek.csv",
    kfe_yolu: str = "data/kfe_temiz.csv",
):
    df = veri_hazirla(veri_yolu, kfe_yolu)
    egitim, test = zaman_bazli_ayir(df)

    ozellik_sutunlari = SAYISAL_OZNITELIKLER + KATEGORIK_OZNITELIKLER
    X_egitim, y_egitim = egitim[ozellik_sutunlari], egitim[HEDEF_SUTUN]
    X_test, y_test = test[ozellik_sutunlari], test[HEDEF_SUTUN]

    on_isleme = ColumnTransformer(transformers=[
        ("sayisal", "passthrough", SAYISAL_OZNITELIKLER),
        ("kategorik", OneHotEncoder(handle_unknown="ignore"), KATEGORIK_OZNITELIKLER),
    ])

    modeller = {
        "RandomForest (mevcut)": RandomForestRegressor(
            n_estimators=400, min_samples_leaf=3, random_state=42, n_jobs=-1,
        ),
        "HistGradientBoosting (aday)": HistGradientBoostingRegressor(
            max_iter=400, random_state=42,
        ),
    }

    print("=" * 70)
    print("GENEL KARŞILAŞTIRMA")
    print("=" * 70)

    sonuclar = {}
    for isim, model in modeller.items():
        pipeline = Pipeline(steps=[("on_isleme", on_isleme), ("model", model)])
        pipeline.fit(X_egitim, y_egitim)
        tahminler = pipeline.predict(X_test)

        mae = mean_absolute_error(y_test, tahminler)
        mape = mean_absolute_percentage_error(y_test, tahminler) * 100

        print(f"\n{isim}")
        print(f"  MAE : {mae:,.0f} ₺/m²")
        print(f"  MAPE: %{mape:.1f}")

        sonuclar[isim] = tahminler

    print("\n" + "=" * 70)
    print("İLÇE BAZINDA HATA RAPORU (RandomForest — mevcut model)")
    print("=" * 70)
    rapor_rf = ilce_bazli_hata_raporu(egitim, test, sonuclar["RandomForest (mevcut)"])
    print(rapor_rf.to_string())

    print("\n" + "=" * 70)
    print("İLÇE BAZINDA HATA RAPORU (HistGradientBoosting — aday)")
    print("=" * 70)
    rapor_hgb = ilce_bazli_hata_raporu(egitim, test, sonuclar["HistGradientBoosting (aday)"])
    print(rapor_hgb.to_string())

    print(
        "\nNot: 'egitim_satir' sayısı düşük olan ilçelerde (örn. <150) "
        "hem MAPE yüksek çıkar hem de bu ilçeler için tahminler genel "
        "olarak daha az güvenilirdir — bu veri azlığından kaynaklanır, "
        "model hatasından değil."
    )


if __name__ == "__main__":
    model_karsilastir()
