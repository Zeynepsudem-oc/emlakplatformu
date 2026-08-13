"""
Tanı scripti: temiz_veri_gercek.csv içinde kaç farklı il var, Kayseri
dışındaki kayıtlar hangi ilçe isimleriyle görünüyor - bunları raporlar.
Hiçbir dosyayı değiştirmez, sadece okuyup ekrana basar.

Çalıştırmak için (proje kök klasöründen):
    py -m modules.il_kontrol
"""

import pandas as pd


def il_kontrol(veri_yolu: str = "data/temiz_veri_gercek.csv"):
    df = pd.read_csv(veri_yolu)

    print(f"Toplam kayıt: {len(df)}")
    print()

    if "il" not in df.columns:
        print("UYARI: 'il' sütunu bu CSV'de yok. veri_temizleme_gercek.py'nin "
              "ürettiği dosyayı mı kullanıyorsunuz?")
        return

    print("İl bazında kayıt sayısı:")
    print(df["il"].value_counts(dropna=False))
    print()

    kayseri_disi = df[df["il"].astype(str).str.strip().str.upper() != "KAYSERI"]
    # Türkçe İ/I karakter sorununa karşı ikinci bir kontrol
    kayseri_disi = kayseri_disi[
        kayseri_disi["il"].astype(str).str.strip().str.upper() != "KAYSERİ"
    ]

    print(f"Kayseri dışı görünen kayıt sayısı: {len(kayseri_disi)}")
    if len(kayseri_disi) > 0:
        print()
        print("Kayseri dışı kayıtların il / ilçe dağılımı:")
        print(
            kayseri_disi.groupby(["il", "ilce"]).size()
            .sort_values(ascending=False)
            .head(30)
        )

    print()
    print("Tüm veri setindeki benzersiz ilçe isimleri (alfabetik):")
    print(sorted(df["ilce"].dropna().unique().tolist()))


if __name__ == "__main__":
    il_kontrol()
