"""
İstanbul ilçe/ada merkez koordinatlarını temizlenmiş veriye ekler.
Harita gösterimi için her satıra enlem (lat) / boylam (lon) kazandırır.
"""

import pandas as pd
from modules.veri_temizleme import veri_yukle_ve_temizle

# İlçe merkezlerinin yaklaşık enlem/boylam değerleri
ILCE_KOORDINAT = {
    "Adalar":        (40.8733, 29.1244),
    "Arnavutköy":    (41.1918, 28.7402),
    "Ataşehir":      (40.9833, 29.1167),
    "Avcılar":       (40.9797, 28.7215),
    "Bağcılar":      (41.0389, 28.8564),
    "Bahçelievler":  (40.9989, 28.8592),
    "Bakırköy":      (40.9819, 28.8772),
    "Başakşehir":    (41.0947, 28.8017),
    "Bayrampaşa":    (41.0450, 28.9114),
    "Beşiktaş":      (41.0422, 29.0067),
    "Beykoz":        (41.1367, 29.0950),
    "Beylikdüzü":    (41.0019, 28.6414),
    "Beyoğlu":       (41.0369, 28.9772),
    "Büyükçekmece":  (41.0192, 28.5850),
    "Çatalca":       (41.1436, 28.4614),
    "Çekmeköy":      (41.0367, 29.2000),
    "Esenler":       (41.0450, 28.8794),
    "Esenyurt":      (41.0342, 28.6786),
    "Eyüpsultan":    (41.0481, 28.9339),
    "Fatih":         (41.0186, 28.9497),
    "Gaziosmanpaşa": (41.0644, 28.9153),
    "Güngören":      (41.0161, 28.8722),
    "Kadıköy":       (40.9928, 29.0269),
    "Kağıthane":     (41.0819, 28.9711),
    "Kartal":        (40.9061, 29.1897),
    "Küçükçekmece":  (41.0025, 28.7742),
    "Maltepe":       (40.9350, 29.1550),
    "Pendik":        (40.8781, 29.2339),
    "Sancaktepe":    (41.0028, 29.2331),
    "Sarıyer":       (41.1667, 29.0500),
    "Silivri":       (41.0736, 28.2469),
    "Sultanbeyli":   (40.9622, 29.2708),
    "Sultangazi":    (41.1067, 28.8672),
    "Şile":          (41.1758, 29.6122),
    "Şişli":         (41.0603, 28.9878),
    "Tuzla":         (40.8172, 29.3081),
    "Ümraniye":      (41.0161, 29.1244),
    "Üsküdar":       (41.0225, 29.0225),
    "Zeytinburnu":   (40.9950, 28.9019),
    # Adalar'a bağlı ada isimleri veri setinde ayrı "ilçe" gibi geçtiği için
    # kendi koordinatlarıyla ekleniyor
    "Kınalıada":     (40.9139, 29.0494),
    "Büyükada":      (40.8733, 29.1244),
    "Burgazada":     (40.8817, 29.0661),
    "Heybeliada":    (40.8778, 29.0917),
}


def koordinat_ekle(df: pd.DataFrame) -> pd.DataFrame:
    """Temizlenmiş DataFrame'e 'lat' ve 'lon' sütunlarını ekler.
    Koordinat tablosunda olmayan ilçeler için satır atılır."""
    df = df.copy()
    df["lat"] = df["ilce"].map(lambda x: ILCE_KOORDINAT.get(x, (None, None))[0])
    df["lon"] = df["ilce"].map(lambda x: ILCE_KOORDINAT.get(x, (None, None))[1])

    eslesmeyen = df[df["lat"].isna()]["ilce"].unique()
    if len(eslesmeyen) > 0:
        print(f"Uyarı: Koordinatı olmayan {len(eslesmeyen)} ilçe atlandı: {list(eslesmeyen)}")

    df = df.dropna(subset=["lat", "lon"]).reset_index(drop=True)
    return df


def hazir_veri_getir(csv_yolu: str) -> pd.DataFrame:
    """Tüm pipeline: ham CSV -> temiz + koordinatlı DataFrame."""
    df = veri_yukle_ve_temizle(csv_yolu)
    df = koordinat_ekle(df)
    return df


if __name__ == "__main__":
    df = hazir_veri_getir("data/22_5_2022_sahibinden_ev.csv")
    print("Koordinatlı toplam satır:", len(df))
    print(df[["ilce", "m2", "fiyat", "m2_fiyat", "lat", "lon"]].head(10))

    # Temiz veriyi diske kaydet, böylece her seferinde yeniden işlemeye gerek kalmaz
    cikti_yolu = "data/temiz_veri.csv"
    df.to_csv(cikti_yolu, index=False, encoding="utf-8-sig")
    print(f"\nTemiz veri kaydedildi: {cikti_yolu}")
