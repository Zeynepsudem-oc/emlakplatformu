"""
TÜİK İl Gösterge Kartı verisini (data/tuik_kayseri/il_gosterge_kartlari.csv/json)
kategoriye uygun grafiklere (pasta, sütun, tarihsel çizgi/sütun) ve Kayseri'yi
vurgulayan bir Türkiye il haritasına dönüştüren yardımcı fonksiyonlar.

Bu modül ham veriyi HİÇ yeniden çekmez (scraping yapmaz) -- sadece
tuik_scraper.py'nin daha önce diske kaydettiği veriyi okuyup görselleştirir.
"""

import os
import json
import requests
import pandas as pd
import plotly.express as px
import folium

DATA_DIR = os.path.join("data", "tuik_kayseri")
CSV_YOLU = os.path.join(DATA_DIR, "il_gosterge_kartlari.csv")
JSON_YOLU = os.path.join(DATA_DIR, "il_gosterge_kartlari.json")

TURKIYE_GEOJSON_URL = "https://raw.githubusercontent.com/cihadturhan/tr-geojson/master/geo/tr-cities-utf8.json"




def _normalize_il_adi(ad) -> str:
    """
    Her türlü veri tipine (None, int, float, str) karşı korumalı 
    Türkçe karakter normalizasyonu.
    """
    if ad is None:
        return ""
    
    s = str(ad).strip()
    if not s:
        return ""
    
    # Türkçe küçük 'i' harfini düzgün dönüştürmek için:
    s = s.replace("i", "I").replace("İ", "I").upper()
    
    # Türkçe özel karakterleri İngilizce karşılıklarına çevir
    s = (
        s.replace("Ç", "C")
         .replace("Ğ", "G")
         .replace("Ö", "O")
         .replace("Ş", "S")
         .replace("Ü", "U")
    )
    return s


def turkce_sayi_parse(deger_str):
    """'728.836' -> 728836.0, '34,9' -> 34.9, sayı değilse None döner."""
    if deger_str is None:
        return None
    s = str(deger_str).strip()
    s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def veri_var_mi() -> bool:
    return os.path.exists(CSV_YOLU) and os.path.exists(JSON_YOLU)


def flat_veri_yukle():
    """il_gosterge_kartlari.csv ve .json dosyalarını okur. Yoksa (None, None) döner."""
    if not veri_var_mi():
        return None, None
    df = pd.read_csv(CSV_YOLU)
    with open(JSON_YOLU, "r", encoding="utf-8") as f:
        json_veri = json.load(f)
    return df, json_veri


# =========================================================================
# KATEGORİ BAZLI GRAFİK ÜRETİCİLERİ
# Her biri bir plotly.graph_objects Figure (ya da None, veri yoksa) döner.
# =========================================================================

def nufus_simdiki_grafik(df_il: pd.DataFrame):
    """Erkek/Kadın güncel nüfusu pasta grafiği olarak döner."""
    alt = df_il[(df_il["Kategori"] == "NÜFUS") & (df_il["Gösterge"].isin(["Erkek", "Kadın"]))]
    if alt.empty:
        return None
    alt = alt.copy()
    alt["Değer_sayi"] = alt["Değer"].apply(turkce_sayi_parse)
    fig = px.pie(
        alt, names="Gösterge", values="Değer_sayi", hole=0.5,
        color="Gösterge", color_discrete_map={"Erkek": "#5BB6FF", "Kadın": "#ED4E81"},
        title="Cinsiyete Göre Nüfus",
    )
    fig.update_layout(template="plotly_white", margin=dict(t=40, l=10, r=10, b=10))
    return fig


def nufus_tarihsel_grafik(json_il: dict):
    """1927-2025 arası Erkek/Kadın nüfus gelişimini sütun grafiği olarak döner."""
    grafik = json_il.get("nufus_grafigi", {})
    yillar = grafik.get("yillar")
    seriler = grafik.get("seriler")
    if not yillar or not seriler:
        return None

    satirlar = []
    for seri in seriler:
        for yil, deger in zip(yillar, seri["veri"]):
            satirlar.append({"Yıl": yil, "Cinsiyet": seri["ad"], "Nüfus": deger})
    df_uzun = pd.DataFrame(satirlar)

    fig = px.bar(
        df_uzun, x="Yıl", y="Nüfus", color="Cinsiyet", barmode="group",
        color_discrete_map={"Erkek": "#5BB6FF", "Kadın": "#ED4E81"},
        title="Yıllara Göre Nüfus Gelişimi",
    )
    fig.update_layout(template="plotly_white", margin=dict(t=40, l=10, r=10, b=10))
    fig.update_yaxes(tickformat=",.0f")
    return fig


def goc_grafik(df_il: pd.DataFrame):
    """İç/uluslararası göç (aldığı/verdiği) sütun grafiği."""
    alt = df_il[df_il["Kategori"] == "İÇ GÖÇ / ULUSLARARASI GÖÇ"]
    if alt.empty:
        return None
    alt = alt.copy()
    alt["Değer_sayi"] = alt["Değer"].apply(turkce_sayi_parse)
    fig = px.bar(
        alt, x="Gösterge", y="Değer_sayi", color="Gösterge",
        title="İç ve Uluslararası Göç",
        color_discrete_sequence=px.colors.qualitative.Set2,
    )
    fig.update_layout(template="plotly_white", margin=dict(t=40, l=10, r=10, b=10), showlegend=False)
    fig.update_yaxes(title="Kişi Sayısı", tickformat=",.0f")
    fig.update_xaxes(title=None)
    return fig


def hanehalki_kompozisyon_grafik(df_il: pd.DataFrame):
    """Hanehalkı tiplerinin (tek kişilik, çekirdek, geniş vb.) pasta grafiği."""
    hedef_gostergeler = ["Tek Kişilik", "Tek Çekirdek Aileden Oluşan", "Geniş Aileden Oluşan", "Çekirdek Aile Bulunmayan"]
    alt = df_il[(df_il["Kategori"] == "HANEHALKI NİTELİKLERİ") & (df_il["Gösterge"].isin(hedef_gostergeler))]
    if alt.empty:
        return None
    alt = alt.copy()
    alt["Değer_sayi"] = alt["Değer"].apply(turkce_sayi_parse)
    fig = px.pie(
        alt, names="Gösterge", values="Değer_sayi", hole=0.5,
        title="Hanehalkı Kompozisyonu",
        color_discrete_sequence=px.colors.qualitative.Pastel,
    )
    fig.update_layout(template="plotly_white", margin=dict(t=40, l=10, r=10, b=10))
    return fig


def medeni_durum_grafik(df_il: pd.DataFrame):
    """Medeni durum dağılımı pasta grafiği."""
    alt = df_il[df_il["Kategori"] == "MEDENİ DURUM"]
    if alt.empty:
        return None
    alt = alt.copy()
    alt["Değer_sayi"] = alt["Değer"].apply(turkce_sayi_parse)
    fig = px.pie(
        alt, names="Gösterge", values="Değer_sayi", hole=0.5,
        title="Medeni Durum Dağılımı",
        color_discrete_sequence=px.colors.qualitative.Set3,
    )
    fig.update_layout(template="plotly_white", margin=dict(t=40, l=10, r=10, b=10))
    return fig


def egitim_durumu_grafik(df_il: pd.DataFrame):
    """Eğitim durumu dağılımı sütun grafiği (eğitim seviyesine göre sıralı)."""
    sira = [
        "Okuma Yazma Bilmeyen", "Okuma Yazma Bilen Bir Okul Bitirmeyen", "İlkokul", "İlköğretim",
        "Ortaokul/ Dengi Meslek Okulu", "Lise/ Dengi Meslek Okulu", "Yüksekokul/ Fakülte", "Yüksek Lisans Ve Üzeri",
    ]
    alt = df_il[df_il["Kategori"] == "EĞİTİM DURUMU"]
    if alt.empty:
        return None
    alt = alt.copy()
    alt["Değer_sayi"] = alt["Değer"].apply(turkce_sayi_parse)
    alt["Gösterge"] = pd.Categorical(alt["Gösterge"], categories=sira, ordered=True)
    alt = alt.sort_values("Gösterge")
    fig = px.bar(
        alt, x="Gösterge", y="Değer_sayi",
        title="Eğitim Durumu Dağılımı",
        color_discrete_sequence=["#2563EB"],
    )
    fig.update_layout(template="plotly_white", margin=dict(t=40, l=10, r=10, b=10))
    fig.update_yaxes(title="Kişi Sayısı", tickformat=",.0f")
    fig.update_xaxes(title=None, tickangle=-30)
    return fig


def kategori_kartlari(df_il: pd.DataFrame, kategori: str):
    """
    Sayısal olmayan / birbirleriyle kıyaslanamayan (farklı birim) göstergeler
    için (Hayati İstatistikler, İsim İstatistikleri gibi) grafik yerine
    etiket-değer çiftleri listesi döner -- app.py bunları st.metric ile gösterir.
    """
    alt = df_il[df_il["Kategori"] == kategori]
    return list(zip(alt["Gösterge"], alt["Değer"]))


# =========================================================================
# TÜRKİYE HARİTASI (KAYSERİ VURGULU)
# =========================================================================

def turkiye_geojson_getir():
    """GeoJSON'u indirir (internet gerektirir). Hata olursa None döner."""
    try:
        resp = requests.get(TURKIYE_GEOJSON_URL, timeout=15)
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return None


import folium

def _normalize_il_adi(ad) -> str:
    """
    Her türlü veri tipine (None, int, float, str) karşı korumalı 
    Türkçe karakter normalizasyonu.
    """
    if ad is None:
        return ""
    
    s = str(ad).strip()
    if not s:
        return ""
    
    # Türkçe küçük 'i' harfini düzgün dönüştürmek için:
    s = s.replace("i", "I").replace("İ", "I").upper()
    
    # Türkçe özel karakterleri İngilizce karşılıklarına çevir
    s = (
        s.replace("Ç", "C")
         .replace("Ğ", "G")
         .replace("Ö", "O")
         .replace("Ş", "S")
         .replace("Ü", "U")
    )
    return s


def turkiye_haritasi_olustur(geojson_veri, vurgulanan_il="KAYSERİ"):
    if not geojson_veri:
        return None

    hedef_normalized = _normalize_il_adi(vurgulanan_il)

    # Harita merkez noktası
    m = folium.Map(location=[39.0, 35.2], zoom_start=6, tiles="CartoDB positron")

    def stil(feature):
        # Feature veya properties None gelebilir, korumaya alıyoruz
        if not feature or not isinstance(feature, dict):
            return {"fillColor": "#94A3B8", "color": "#64748B", "weight": 0.5, "fillOpacity": 0.15}
        
        props = feature.get("properties") or {}
        
        # 'name', 'NAME', 'il_adi' vb. olası tüm key'leri dener
        il_adi = props.get("name") or props.get("NAME") or props.get("il_adi") or ""
        
        if _normalize_il_adi(il_adi) == hedef_normalized:
            return {
                "fillColor": "#E11D48", 
                "color": "#B91C1C", 
                "weight": 2, 
                "fillOpacity": 0.75
            }
        return {
            "fillColor": "#94A3B8", 
            "color": "#64748B", 
            "weight": 0.5, 
            "fillOpacity": 0.15
        }

    folium.GeoJson(
        geojson_veri,
        style_function=stil,
        tooltip=folium.GeoJsonTooltip(fields=["name"], aliases=["İl:"]),
    ).add_to(m)

    return m