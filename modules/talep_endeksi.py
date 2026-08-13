"""
modules/talep_endeksi.py
-------------------------------------------------------------------
TÜİK demografik göstergelerinden yola çıkarak açıklanabilir, kural
tabanlı bir "Konut Talep Endeksi" hesaplar. Bileşenler:

  1) Hanehalkı Oluşum Puanı  -> Evlenme Sayısı / (Evlenme + Boşanma)
  2) Net Göç Puanı           -> Net Göç Hızı (‰)
  3) Nüfus Artış Puanı       -> Yıllık Nüfus Artış Hızı (‰)
"""

import re
import pandas as pd


# =========================================================================
# YARDIMCI FONKSİYONLAR
# =========================================================================

def sayiya_cevir(metin):
    """'9.763' veya '1,46' gibi TÜİK formatındaki metni float'a çevirir."""
    if metin is None or pd.isna(metin):
        return None
    metin = str(metin).strip()
    if metin == "" or metin.lower() in ("nan", "none", "-", "...", "null"):
        return None
    temiz = metin.replace(".", "").replace(",", ".")
    temiz = re.sub(r"[^0-9\.\-]", "", temiz)
    if temiz in ("", "-", "."):
        return None
    try:
        return float(temiz)
    except ValueError:
        return None


def olcekle(deger, alt_sinir, ust_sinir):
    """Bir değeri [alt_sinir, ust_sinir] aralığından 0-100 skalasına taşır."""
    if deger is None:
        return None
    deger = max(alt_sinir, min(ust_sinir, deger))
    if ust_sinir == alt_sinir:
        return 50.0
    return (deger - alt_sinir) / (ust_sinir - alt_sinir) * 100


def birlesik_tuik_verisi(tuik_veri_sozlugu) -> pd.DataFrame:
    """
    Eski import bağımlılıklarını kırmamak için korunan yardımcı fonksiyon.
    Eğer gelen veri DataFrame sözlüğü ise bunları tek DataFrame yapar,
    JSON/dict yapısı ise boş veya dönüştürülmüş DataFrame döndürür.
    """
    if isinstance(tuik_veri_sozlugu, pd.DataFrame):
        return tuik_veri_sozlugu
    if not isinstance(tuik_veri_sozlugu, dict):
        return pd.DataFrame()

    parcalar = []
    for anahtar, df_parca in tuik_veri_sozlugu.items():
        if isinstance(df_parca, pd.DataFrame) and not df_parca.empty:
            gecici = df_parca.copy()
            gecici["_kaynak_tablo"] = anahtar
            parcalar.append(gecici)
    if not parcalar:
        return pd.DataFrame()
    return pd.concat(parcalar, ignore_index=True, sort=False)


def gosterge_degeri_bul(veri_objesi, anahtar_kelimeler: list):
    """
    Gerek il_gosterge_kartlari.json (dict) yapısından gerekse DataFrame 
    yapısından esnek anahtar kelimelerle sayısal veriyi çeker.
    """
    if veri_objesi is None:
        return None

    # 1. DURUM: Veri dict / JSON formatında geldiyse (il_gosterge_kartlari.json gibi)
    if isinstance(veri_objesi, dict):
        hedef_dict = veri_objesi.get("kartlar", veri_objesi)
        
        for k, v in hedef_dict.items():
            if isinstance(v, dict):
                for alt_k, alt_v in v.items():
                    alt_k_clean = str(alt_k).lower().strip()
                    for kelime in anahtar_kelimeler:
                        if kelime.lower().strip() in alt_k_clean:
                            val = sayiya_cevir(alt_v)
                            if val is not None:
                                return val
            else:
                k_clean = str(k).lower().strip()
                for kelime in anahtar_kelimeler:
                    if kelime.lower().strip() in k_clean:
                        val = sayiya_cevir(v)
                        if val is not None:
                            return val

    # 2. DURUM: Veri DataFrame olarak geldiyse
    elif isinstance(veri_objesi, pd.DataFrame):
        if veri_objesi.empty:
            return None

        # Sütun isimlerinde ara
        for kelime in anahtar_kelimeler:
            kelime_temiz = kelime.lower().strip()
            for col in veri_objesi.columns:
                if kelime_temiz in str(col).lower():
                    for val_raw in veri_objesi[col]:
                        val = sayiya_cevir(val_raw)
                        if val is not None:
                            return val

        # Hücre içeriklerinde ara
        for col in veri_objesi.columns:
            for idx, val_raw in enumerate(veri_objesi[col]):
                val_str = str(val_raw).lower()
                for kelime in anahtar_kelimeler:
                    if kelime.lower().strip() in val_str:
                        for diger_col in veri_objesi.columns:
                            if diger_col != col:
                                val = sayiya_cevir(veri_objesi.iloc[idx][diger_col])
                                if val is not None:
                                    return val

    return None


# =========================================================================
# TALEP ENDEKSİ
# =========================================================================

def talep_bilesenlerini_cikar(tuik_veri_sozlugu) -> dict:
    """
    TÜİK verisinden (il_gosterge_kartlari.json yapısı) konut talebini
    etkileyen ham göstergeleri, bilinen kesin kategori/gösterge isimleriyle çıkarır.
    tuik_veri_sozlugu: {"KAYSERİ": {"kartlar": {...}, "nufus_grafigi": {...}}} formatında.
    """
    kartlar = {}
    if isinstance(tuik_veri_sozlugu, dict) and len(tuik_veri_sozlugu) > 0:
        ilk_anahtar = list(tuik_veri_sozlugu.keys())[0]
        ilk_veri = tuik_veri_sozlugu[ilk_anahtar]
        if isinstance(ilk_veri, dict):
            kartlar = ilk_veri.get("kartlar", {})

    def kesin_deger(kategori, gosterge):
        return sayiya_cevir(kartlar.get(kategori, {}).get(gosterge))

    ic_aldigi = kesin_deger("İÇ GÖÇ / ULUSLARARASI GÖÇ", "Diğer İllerden Aldığı Göç")
    ic_verdigi = kesin_deger("İÇ GÖÇ / ULUSLARARASI GÖÇ", "Diğer İllere Verdiği Göç")
    toplam_nufus = kesin_deger("NÜFUS", "Toplam")
    evlenme = kesin_deger("HAYATİ İSTATİSTİKLER", "Evlenme Sayısı")
    bosanma = kesin_deger("HAYATİ İSTATİSTİKLER", "Boşanma Sayısı")
    nufus_artis = kesin_deger("NÜFUS", "Nüfus Artış Hızı(Binde)")
    net_goc_sayisi = None
    if ic_aldigi is not None and ic_verdigi is not None:
        net_goc_sayisi = ic_aldigi - ic_verdigi

    net_goc_hizi = None
    if net_goc_sayisi is None:
        net_goc_hizi = gosterge_degeri_bul(veri_kaynagi, ["net göç hızı"])
    
    if net_goc_hizi is None and net_goc_sayisi is not None and toplam_nufus and toplam_nufus > 0:
        net_goc_hizi = (net_goc_sayisi / toplam_nufus) * 1000

    return {
        "evlenme_sayisi": evlenme,
        "bosanma_sayisi": bosanma,
        "net_goc_sayisi": net_goc_sayisi,
        "net_goc_hizi": net_goc_hizi,
        "nufus_artis_hizi": nufus_artis,
        "toplam_nufus": toplam_nufus,
    }


def talep_endeksi_hesapla(
    tuik_veri_sozlugu,
    agirlik_evlilik: float = 0.4,
    agirlik_goc: float = 0.3,
    agirlik_nufus: float = 0.3,
) -> dict:
    """Konut Talep Endeksi Skor Kartı Hesaplar."""
    ham = talep_bilesenlerini_cikar(tuik_veri_sozlugu)

    # 1) Hanehalkı oluşum puanı
    evlilik_puani = None
    if ham["evlenme_sayisi"] is not None and ham["bosanma_sayisi"] is not None:
        toplam = ham["evlenme_sayisi"] + ham["bosanma_sayisi"]
        if toplam > 0:
            oran = ham["evlenme_sayisi"] / toplam
            evlilik_puani = olcekle(oran, 0.5, 0.9)

    # 2) Net göç puanı
    goc_puani = None
    if ham["net_goc_hizi"] is not None:
        goc_puani = olcekle(ham["net_goc_hizi"], -30, 30)
    elif ham["net_goc_sayisi"] is not None:
        goc_puani = olcekle(ham["net_goc_sayisi"], -15000, 15000)

    # 3) Nüfus artış puanı
    nufus_puani = None
    if ham["nufus_artis_hizi"] is not None:
        nufus_puani = olcekle(ham["nufus_artis_hizi"], -20, 40)

    bilesen_puanlari = {
        "Hanehalkı Oluşum Puanı": evlilik_puani,
        "Net Göç Puanı": goc_puani,
        "Nüfus Artış Puanı": nufus_puani,
    }
    agirliklar = {
        "Hanehalkı Oluşum Puanı": agirlik_evlilik,
        "Net Göç Puanı": agirlik_goc,
        "Nüfus Artış Puanı": agirlik_nufus,
    }

    gecerli = {k: v for k, v in bilesen_puanlari.items() if v is not None}
    if not gecerli:
        return {
            "endeks": None,
            "ham_veri": ham,
            "bilesen_puanlari": bilesen_puanlari,
            "kullanilan_agirliklar": {},
            "eksik_veri_uyarisi": "TÜİK verisinde gerekli göstergeler bulunamadı.",
        }

    toplam_agirlik = sum(agirliklar[k] for k in gecerli)
    endeks = sum(gecerli[k] * agirliklar[k] for k in gecerli) / toplam_agirlik

    eksik_sayisi = len(bilesen_puanlari) - len(gecerli)
    uyari = (
        f"{eksik_sayisi} bileşen için veri bulunamadı; endeks kalan {len(gecerli)} bileşenle hesaplandı."
        if eksik_sayisi > 0 else None
    )

    return {
        "endeks": round(endeks, 1),
        "ham_veri": ham,
        "bilesen_puanlari": bilesen_puanlari,
        "kullanilan_agirliklar": agirliklar,
        "eksik_veri_uyarisi": uyari,
    }


# =========================================================================
# İLÇE YATIRIM SKORU
# =========================================================================

def ilce_yatirim_skoru_hesapla(filtreli_df: pd.DataFrame, talep_endeksi_sonucu: dict, min_kayit: int = 5) -> pd.DataFrame:
    if filtreli_df is None or filtreli_df.empty or "ilce" not in filtreli_df.columns:
        return pd.DataFrame()

    il_talep_puani = talep_endeksi_sonucu.get("endeks")
    if il_talep_puani is None:
        il_talep_puani = 50.0

    gruplu = (
        filtreli_df.groupby("ilce")
        .agg(
            ortalama_m2_fiyat=("m2_fiyat_guncel", "mean"),
            kayit_sayisi=("m2_fiyat_guncel", "count"),
        )
        .reset_index()
    )
    gruplu = gruplu[gruplu["kayit_sayisi"] >= min_kayit].copy()
    if gruplu.empty:
        return pd.DataFrame()

    momentum_sozlugu = {}
    if "rapor_yili" in filtreli_df.columns:
        for ilce_adi, alt_df in filtreli_df.dropna(subset=["rapor_yili"]).groupby("ilce"):
            yillik = alt_df.groupby("rapor_yili")["m2_fiyat_guncel"].mean().sort_index()
            if len(yillik) >= 2 and yillik.iloc[0] > 0:
                momentum_sozlugu[ilce_adi] = (yillik.iloc[-1] - yillik.iloc[0]) / yillik.iloc[0] * 100

    gruplu["fiyat_momentumu_yuzde"] = gruplu["ilce"].map(momentum_sozlugu)
    gruplu["momentum_puani"] = gruplu["fiyat_momentumu_yuzde"].apply(lambda v: olcekle(v, -20, 40))
    gruplu["momentum_puani"] = gruplu["momentum_puani"].fillna(50.0)

    maks_kayit = gruplu["kayit_sayisi"].max()
    gruplu["likidite_puani"] = (gruplu["kayit_sayisi"] / maks_kayit * 100) if maks_kayit else 0.0

    gruplu["yatirim_skoru"] = (
        il_talep_puani * 0.50
        + gruplu["momentum_puani"] * 0.35
        + gruplu["likidite_puani"] * 0.15
    ).round(1)

    return gruplu.sort_values("yatirim_skoru", ascending=False).reset_index(drop=True)
