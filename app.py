
"""
Kayseri Gayrimenkul Değerleme Platformu - Streamlit Arayüzü
Gerçek ekspertiz verisi (temiz_veri_gercek.csv) + KFE endeksi + aşınma payı + TÜİK Demografi Analizi.
"""
 
import io
import os
import streamlit as st
import pandas as pd
import numpy as np
import folium
from folium.plugins import FastMarkerCluster, HeatMap
from streamlit_folium import st_folium
import plotly.express as px
import datetime
 
from modules.adres_ara import adresi_koordinata_cevir, en_yakin_ilceyi_bul, haversine_mesafe_km
from modules.asinma_payi import asinma_uygula, ASINMA_TABLOSU
from modules.endeks_hesapla import kfe_ile_guncelle
from modules.zaman_normalizasyon import dataframeyi_bugune_tasi
from modules.deger_tahmin import model_ile_deger_tahmini, emsal_ve_model_birlestir
from modules.tuik_scraper import il_gosterge_karti_tam_cek
from modules.talep_endeksi import talep_endeksi_hesapla, ilce_yatirim_skoru_hesapla
from modules.tuik_gorsellestir import (flat_veri_yukle, nufus_simdiki_grafik, nufus_tarihsel_grafik,goc_grafik, hanehalki_kompozisyon_grafik, medeni_durum_grafik,egitim_durumu_grafik, kategori_kartlari, turkiye_geojson_getir,turkiye_haritasi_olustur,)
from modules.ek_ozellikler import (kredi_hesapla, deprem_yonetmeligi_kontrol,kira_getirisi_hesapla, yakin_cevre_puani_hesapla,)
 
st.set_page_config(page_title="Kayseri Gayrimenkul Değerleme", layout="wide")
st.title("🏠 Kayseri Gayrimenkul Değerleme Platformu")
st.caption("Veri kaynağı: Gerçek ekspertiz raporları (5.749 kayıt) & TÜİK Nüfus Portalı — deneme/prototip amaçlıdır")
 
 
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
 
@st.cache_data
def veri_yukle():
    csv_path = os.path.join(BASE_DIR, "data", "temiz_veri_gercek.csv")
    return pd.read_csv(csv_path)
 
@st.cache_data
def kfe_yukle():
    csv_path = os.path.join(BASE_DIR, "data", "kfe_temiz.csv")
    return pd.read_csv(csv_path)
 
@st.cache_data
def ana_veri_hazirla():
    df_raw = veri_yukle()
    kfe_df = kfe_yukle()
    return dataframeyi_bugune_tasi(df_raw, kfe_df), kfe_df
 
 
@st.cache_data(ttl=3600)
def tuik_flat_veri_yukle():
    return flat_veri_yukle()
 
 
@st.cache_data
def turkiye_geojson_yukle():
    return turkiye_geojson_getir()
 
 
# Veri Yükleme ve Ön İşleme
df, kfe_df = ana_veri_hazirla()
df_flat, json_veri = tuik_flat_veri_yukle()
 
 
# =========================================================================
# YARDIMCI FONKSİYONLAR
# =========================================================================
 
def aykiri_degerleri_temizle(emsal_df, sutun="m2_fiyat_guncel"):
    if len(emsal_df) < 4:
        return emsal_df, 0
    q1 = emsal_df[sutun].quantile(0.25)
    q3 = emsal_df[sutun].quantile(0.75)
    iqr = q3 - q1
    alt_sinir, ust_sinir = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    temiz = emsal_df[(emsal_df[sutun] >= alt_sinir) & (emsal_df[sutun] <= ust_sinir)]
    if len(temiz) == 0:
        return emsal_df, 0
    return temiz, len(emsal_df) - len(temiz)
 
 
def emsal_kalite_skoru_hesapla(emsal_df, hedef_m2, hedef_bina_yasi, yaricap_km):
    if len(emsal_df) == 0:
        return 0.0
    m2_fark = ((emsal_df["m2"] - hedef_m2).abs() / max(hedef_m2, 1)).clip(0, 1)
    yas_fark = ((emsal_df["bina_yasi"].fillna(hedef_bina_yasi) - hedef_bina_yasi).abs() / 30.0).clip(0, 1)
    mesafe_orani = (emsal_df["mesafe_km"] / max(yaricap_km, 0.1)).clip(0, 1)
    skor = (1 - m2_fark) * 40 + (1 - yas_fark) * 30 + (1 - mesafe_orani) * 30
    return float(skor.mean())
 
 
def rapor_excel_olustur(ozet_dict, emsal_df):
    buffer = io.BytesIO()
    ozet_df = pd.DataFrame(list(ozet_dict.items()), columns=["Alan", "Değer"])
    emsal_export = emsal_df[[
        "mahalle", "ilce", "m2", "bina_yasi", "kat", "fiyat", "m2_fiyat_guncel", "mesafe_km"
    ]].rename(columns={
        "mahalle": "Mahalle", "ilce": "İlçe", "m2": "m²", "bina_yasi": "Bina Yaşı",
        "kat": "Kat", "fiyat": "Fiyat (₺)", "m2_fiyat_guncel": "m² Fiyatı - Güncel (₺)",
        "mesafe_km": "Mesafe (km)",
    })
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        ozet_df.to_excel(writer, index=False, sheet_name="Değer Tespiti")
        emsal_export.to_excel(writer, index=False, sheet_name="Kullanılan Emsaller")
    return buffer.getvalue()
 
 
def rapor_pdf_olustur(baslik, ozet_dict):
    try:
        from fpdf import FPDF
    except ImportError:
        return None
 
    pdf = FPDF()
    pdf.add_page()
 
    font_hazir = False
    try:
        import matplotlib
        font_yolu = matplotlib.get_data_path() + "/fonts/ttf/DejaVuSans.ttf"
        pdf.add_font("DejaVu", "", font_yolu)
        pdf.set_font("DejaVu", size=16)
        font_hazir = True
    except Exception:
        pdf.set_font("Helvetica", size=16)
 
    def guvenli_metin(metin):
        if font_hazir:
            return str(metin)
        return str(metin).encode("latin-1", "replace").decode("latin-1")
 
    pdf.cell(0, 12, guvenli_metin(baslik), ln=True)
    pdf.set_font(pdf.font_family, size=11)
    pdf.ln(4)
    for etiket, deger in ozet_dict.items():
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(0, 8, guvenli_metin(f"{etiket}: {deger}"))
    pdf.ln(4)
    pdf.set_font_size(8)
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(0, 6, guvenli_metin(
        "Bu rapor otomatik oluşturulmuştur, deneme/prototip amaçlıdır ve resmi bir ekspertiz raporu yerine geçmez."
    ))
 
    cikti = pdf.output()
    return bytes(cikti)
 
 
# =========================================================================
# ADRES ARAMA
# =========================================================================
if "gecmis_aramalar" not in st.session_state:
    st.session_state["gecmis_aramalar"] = []
 
arama_col1, arama_col2 = st.columns([4, 1])
with arama_col1:
    girilen_adres = st.text_input(
        "Adres ara", placeholder="Örn: Melikgazi, Kayseri  veya  38.72, 35.51",
        label_visibility="collapsed",
    )
with arama_col2:
    ara_butonu = st.button("🔍 Değerini Öğren", use_container_width=True)
 
aranan_konum = None
if ara_butonu and girilen_adres:
    with st.spinner("Adres aranıyor..."):
        sonuc = adresi_koordinata_cevir(girilen_adres)
    if sonuc:
        aranan_konum = sonuc
        st.session_state["aranan_konum"] = sonuc
 
        gecmis = st.session_state["gecmis_aramalar"]
        gecmis = [g for g in gecmis if g["tam_adres"] != sonuc["tam_adres"]]
        gecmis.insert(0, sonuc)
        st.session_state["gecmis_aramalar"] = gecmis[:5]
    else:
        st.error("Adres bulunamadı. Daha genel bir adres deneyin (örn. sadece ilçe adı).")
 
if "aranan_konum" in st.session_state and not ara_butonu:
    aranan_konum = st.session_state["aranan_konum"]
 
if st.session_state["gecmis_aramalar"]:
    with st.expander("🕘 Son Aramalar", expanded=False):
        for i, gecmis_konum in enumerate(st.session_state["gecmis_aramalar"]):
            if st.button(f"📍 {gecmis_konum['tam_adres']}", key=f"gecmis_{i}"):
                st.session_state["aranan_konum"] = gecmis_konum
                st.rerun()
 
# ---------------- SOL PANEL: FİLTRELER ----------------
st.sidebar.header("Filtreler")
 
ilceler = sorted(df["ilce"].dropna().unique())
min_m2, max_m2 = int(df["m2"].min()), int(df["m2"].max())
 
yapi_tarzi_kod_sayilari = df["yapi_tarzi_kod"].value_counts().sort_index()
yapi_tarzi_secenekleri = ["Tümü"] + [
    f"Tip {int(kod)} ({adet} kayıt)" for kod, adet in yapi_tarzi_kod_sayilari.items()
]
 
with st.sidebar.form("filtre_formu"):
    secili_ilceler = st.multiselect("İlçe", ilceler, default=ilceler)
    m2_araligi = st.slider("m² aralığı", min_m2, max_m2, (min_m2, min(max_m2, 400)))
    bina_yasi_girisi = st.number_input(
        "Bina Yaşı (değeri hesaplanacak taşınmaz için)", min_value=0, max_value=150, value=10,
        help="Bu değer sadece aşınma payı hesabında kullanılır, emsal listesini filtrelemez.",
    )
    bina_yasi_ile_filtrele = st.checkbox(
        "Emsalleri de bu yaşa yakın binalarla sınırla (bilinmeyen yaşlıları hariç tutar)",
        value=False,
    )
    konut_tipi_secimi = st.selectbox(
        "Konut Tipi", options=["Tümü", "Apartman/Mesken", "Villa"],
    )
    yapi_tarzi_secimi = st.selectbox(
        "Yapı Tarzı Kodu (veri setinden filtrele)",
        options=yapi_tarzi_secenekleri,
        help="Bu kodların gerçek adları (örn. betonarme/yığma) kaynak veride belirtilmemiş; "
             "burada sadece veri setindeki gruplama olarak kullanılıyor.",
    )
    yapi_tipi_secimi = st.selectbox(
        "Aşınma Payı İçin Yapı Tipi (Resmi Gazete Kategorisi)",
        options=list(ASINMA_TABLOSU.keys()),
        format_func=lambda k: ASINMA_TABLOSU[k]["ad"],
        help="Bu seçim yalnızca aşınma payı hesabında kullanılır.",
    )
    arama_yaricapi_km = st.slider("Emsal arama yarıçapı (km)", 0.5, 10.0, 2.0, step=0.5)
    isi_haritasi_goster = st.checkbox("Isı haritası katmanını da ekle", value=True)
    st.form_submit_button("Filtreleri Uygula", use_container_width=True)
 
mask = (df["ilce"].isin(secili_ilceler)) & (df["m2"].between(*m2_araligi))
 
if bina_yasi_ile_filtrele:
    mask &= (df["bina_yasi"] <= bina_yasi_girisi)
 
if konut_tipi_secimi != "Tümü":
    mask &= (df["konut_tipi"] == konut_tipi_secimi)
 
if yapi_tarzi_secimi != "Tümü":
    secili_kod = float(yapi_tarzi_secimi.split("Tip ")[1].split(" ")[0])
    mask &= (df["yapi_tarzi_kod"] == secili_kod)
 
filtreli_df = df[mask]
 
st.sidebar.markdown(f"**{len(filtreli_df)}** kayıt gösteriliyor")
 
# Yan Panel TÜİK Canlı Güncelleme Butonu (tek buton, tüm TÜİK güncellemesi buradan yapılır)
if st.sidebar.button("🔄 TÜİK Verilerini Yenile (Selenium)", key="sidebar_tuik_btn"):
    with st.sidebar.spinner("TÜİK'ten Kayseri verisi yeniden çekiliyor..."):
        il_gosterge_karti_tam_cek(iller=["KAYSERİ"])
        st.cache_data.clear()
        st.sidebar.success("TÜİK verileri güncellendi!")
        st.rerun()
 
# ---------------- ÜST METRİKLER ----------------
col_m1, col_m2, col_m3 = st.columns(3)
col_m1.metric("Toplam Kayıt", len(filtreli_df))
col_m2.metric(
    "Ortalama m² Fiyatı",
    f"{filtreli_df['m2_fiyat_guncel'].mean():,.0f} ₺" if len(filtreli_df) else "-",
)
col_m3.metric("Ortalama Fiyat", f"{filtreli_df['fiyat'].mean():,.0f} ₺" if len(filtreli_df) else "-")
 
st.divider()
 
# =========================================================================
# SEKMELER (TABLAR): EKSPERTİZ ANALİZİ / TÜİK DEMOGRAFİ
# =========================================================================
tab_degerleme, tab_tuik = st.tabs(["🏛️ Gayrimenkul Değerleme ve Harita", "📊 TÜİK Kayseri Demografi Analizi"])
 
with tab_degerleme:
    col1, col2 = st.columns([1.3, 1])
 
    with col1:
        st.subheader("Emsal Harita")
 
        if len(filtreli_df) > 0:
            merkez_lat = aranan_konum["lat"] if aranan_konum else filtreli_df["lat"].mean()
            merkez_lon = aranan_konum["lon"] if aranan_konum else filtreli_df["lon"].mean()
            yakinlastirma = 14 if aranan_konum else 11
 
            aranan_lat = aranan_konum["lat"] if aranan_konum else None
            aranan_lon = aranan_konum["lon"] if aranan_konum else None
 
            harita_df = filtreli_df.dropna(subset=["lat", "lon", "m2_fiyat_guncel"]).copy()
 
            bina_yasi_metin = harita_df["bina_yasi"].round(0).fillna(-1).astype(int).astype(str).replace("-1", "Bilinmiyor")
            kat_metin = harita_df["kat"].round(0).fillna(-99).astype(int).astype(str).replace("-99", "Bilinmiyor")
            etiketler = (
                harita_df["ilce"] + " | "
                + harita_df["m2"].round(0).astype(int).astype(str) + " m² | "
                + harita_df["fiyat"].round(0).astype(int).map("{:,}".format) + " ₺ | Yaş: "
                + bina_yasi_metin + " | Kat: " + kat_metin
            )
            nokta_listesi = tuple(zip(
                harita_df["lat"].tolist(),
                harita_df["lon"].tolist(),
                etiketler.tolist(),
            ))
 
            fiyat_min = harita_df["m2_fiyat_guncel"].min()
            fiyat_max = harita_df["m2_fiyat_guncel"].max()
            if fiyat_max > fiyat_min:
                agirliklar = (harita_df["m2_fiyat_guncel"] - fiyat_min) / (fiyat_max - fiyat_min)
            else:
                agirliklar = pd.Series(0.5, index=harita_df.index)
            isi_verisi = list(zip(harita_df["lat"].tolist(), harita_df["lon"].tolist(), agirliklar.tolist()))
 
            def harita_olustur(nokta_listesi, isi_verisi, merkez_lat, merkez_lon, yakinlastirma,
                               aranan_lat, aranan_lon, yaricap_km, isi_haritasi_goster):
                m = folium.Map(location=[merkez_lat, merkez_lon], zoom_start=yakinlastirma, tiles="CartoDB positron")
 
                renk_js = """
                    function(row) {
                        var marker = L.circleMarker(new L.LatLng(row[0], row[1]), {radius: 6, fillOpacity: 0.7});
                        marker.bindPopup(row[2]);
                        return marker;
                    }
                """
                fg_kume = folium.FeatureGroup(name="Emsal Noktalar (Küme)", show=True)
                FastMarkerCluster(data=list(nokta_listesi), callback=renk_js).add_to(fg_kume)
                fg_kume.add_to(m)
 
                if isi_haritasi_goster:
                    fg_isi = folium.FeatureGroup(name="Yoğunluk (Isı Haritası)", show=False)
                    HeatMap(isi_verisi, radius=18, blur=15).add_to(fg_isi)
                    fg_isi.add_to(m)
 
                if aranan_lat is not None:
                    folium.Marker(
                        location=[aranan_lat, aranan_lon],
                        tooltip="Aranan Konum",
                        icon=folium.Icon(color="blue", icon="home", prefix="fa"),
                    ).add_to(m)
                    folium.Circle(
                        location=[aranan_lat, aranan_lon],
                        radius=yaricap_km * 1000,
                        color="blue", fill=True, fill_opacity=0.05,
                    ).add_to(m)
 
                folium.LayerControl(collapsed=False).add_to(m)
                return m
 
            with st.spinner("Harita oluşturuluyor..."):
                m = harita_olustur(
                    nokta_listesi, isi_verisi, merkez_lat, merkez_lon, yakinlastirma,
                    aranan_lat, aranan_lon, arama_yaricapi_km, isi_haritasi_goster,
                )
 
            ilceler_key = tuple(sorted(secili_ilceler))
            harita_key = f"harita_{hash(ilceler_key)}_{m2_araligi[0]}_{m2_araligi[1]}_{aranan_lat}_{aranan_lon}"
 
            secim = st_folium(
                m, width=700, height=520,
                returned_objects=["last_object_clicked_tooltip"],
                key=harita_key,
            )
        else:
            st.warning("Seçilen filtrelere uyan veri yok.")
            secim = None
 
        # DEĞER TESPİTİ SONUCU
        if aranan_konum and len(filtreli_df) > 0:
            filtreli_df = filtreli_df.copy()
 
            R = 6371
            lat1, lon1 = np.radians(aranan_konum["lat"]), np.radians(aranan_konum["lon"])
            lat2, lon2 = np.radians(filtreli_df["lat"].to_numpy()), np.radians(filtreli_df["lon"].to_numpy())
            dlat, dlon = lat2 - lat1, lon2 - lon1
            a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
            filtreli_df["mesafe_km"] = 2 * R * np.arcsin(np.sqrt(a))
 
            emsal_df_ham = filtreli_df[filtreli_df["mesafe_km"] <= arama_yaricapi_km]
 
            if len(emsal_df_ham) > 0:
                emsal_df, cikarilan_sayisi = aykiri_degerleri_temizle(emsal_df_ham, "m2_fiyat_guncel")
 
                if len(emsal_df) == 0:
                    st.warning("Aykırı değer temizleme sonrasında arama yarıçapında geçerli emsal kalmadı.")
                else:
                    emsal_m2_fiyat_guncel = emsal_df["m2_fiyat_guncel"].mean()
 
                    emsal_bilgi_metni = (
                        f"📍 **{aranan_konum['tam_adres']}**\n\n"
                        f"Yarıçap içinde **{len(emsal_df_ham)}** emsal bulundu"
                    )
                    if cikarilan_sayisi > 0:
                        emsal_bilgi_metni += f", bunlardan **{cikarilan_sayisi}** tanesi aykırı değer olduğu için hesaba katılmadı"
                    emsal_bilgi_metni += (
                        f".\n\nEmsal bazlı ortalama m² fiyatı (bugüne taşınmış): **{emsal_m2_fiyat_guncel:,.0f} ₺**"
                    )
                    st.success(emsal_bilgi_metni)
 
                    ornek_m2 = st.number_input("Değeri hesaplanacak taşınmazın m²'si", min_value=10, value=100)
                    ornek_kat = st.number_input("Kat", min_value=-2, max_value=40, value=2)
 
                    en_yakin_satir = emsal_df.loc[emsal_df["mesafe_km"].idxmin()]
 
                    model_sonuc = model_ile_deger_tahmini(
                        lat=aranan_konum["lat"], lon=aranan_konum["lon"],
                        m2=ornek_m2, kat=ornek_kat, bina_yasi=bina_yasi_girisi,
                        ilce=en_yakin_satir["ilce"],
                        yapi_tarzi_kod=en_yakin_satir["yapi_tarzi_kod"],
                        yapi_kalitesi_kod=en_yakin_satir["yapi_kalitesi_kod"],
                    )
 
                    piyasa_m2_fiyat = emsal_ve_model_birlestir(
                        emsal_m2_fiyat_guncel, model_sonuc["tahmini_m2_fiyat"],
                        emsal_agirlik=0.7 if len(emsal_df) >= 20 else 0.3,
                    )
                    piyasa_bazli_deger = piyasa_m2_fiyat * ornek_m2
 
                    asinma_sonucu = asinma_uygula(piyasa_bazli_deger, bina_yasi_girisi, yapi_tipi_secimi)
                    nihai_deger = asinma_sonucu["asinma_sonrasi_deger"]
 
                    std_m2_fiyat = emsal_df["m2_fiyat_guncel"].std() if len(emsal_df) >= 2 else 0
                    belirsizlik_orani = min((std_m2_fiyat / emsal_m2_fiyat_guncel) if emsal_m2_fiyat_guncel else 0, 0.4)
                    alt_deger = nihai_deger * (1 - belirsizlik_orani)
                    ust_deger = nihai_deger * (1 + belirsizlik_orani)
 
                    kalite_skoru = emsal_kalite_skoru_hesapla(emsal_df, ornek_m2, bina_yasi_girisi, arama_yaricapi_km)
 
                    st.markdown("### Değer Tespiti Sonucu")
                    d1, d2, d3, d4 = st.columns(4)
                    d1.metric("Emsal Bazlı m²", f"{emsal_m2_fiyat_guncel:,.0f} ₺")
                    d2.metric("Model Bazlı m²", f"{model_sonuc['tahmini_m2_fiyat']:,.0f} ₺")
                    d3.metric("Aşınma Öncesi (Birleşik)", f"{piyasa_bazli_deger:,.0f} ₺")
                    d4.metric("Nihai Tahmini Değer", f"{nihai_deger:,.0f} ₺")
 
                    d5, d6 = st.columns(2)
                    d5.metric("Tahmini Değer Aralığı", f"{alt_deger:,.0f} ₺ – {ust_deger:,.0f} ₺")
                    d6.metric("Emsal Kalite Skoru", f"{kalite_skoru:,.0f} / 100")
 
                    rapor_ozet = {
                        "Adres": aranan_konum["tam_adres"],
                        "Tarih": pd.Timestamp.now().strftime("%d.%m.%Y %H:%M"),
                        "m²": ornek_m2,
                        "Kat": ornek_kat,
                        "Bina Yaşı": bina_yasi_girisi,
                        "Yapı Tipi": ASINMA_TABLOSU[yapi_tipi_secimi]["ad"],
                        "Emsal Sayısı": len(emsal_df),
                        "Emsal Bazlı m² Fiyatı (₺)": f"{emsal_m2_fiyat_guncel:,.0f}",
                        "Model Bazlı m² Fiyatı (₺)": f"{model_sonuc['tahmini_m2_fiyat']:,.0f}",
                        "Nihai Tahmini Değer (₺)": f"{nihai_deger:,.0f}",
                        "Tahmini Değer Aralığı (₺)": f"{alt_deger:,.0f} - {ust_deger:,.0f}",
                        "Emsal Kalite Skoru": f"{kalite_skoru:,.0f} / 100",
                    }
 
                    rapor_col1, rapor_col2 = st.columns(2)
                    with rapor_col1:
                        excel_verisi = rapor_excel_olustur(rapor_ozet, emsal_df)
                        st.download_button(
                            "📊 Excel Raporu İndir", data=excel_verisi,
                            file_name="deger_tespiti_raporu.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True,
                        )
                    with rapor_col2:
                        pdf_verisi = rapor_pdf_olustur("Değer Tespiti Raporu", rapor_ozet)
                        if pdf_verisi is not None:
                            st.download_button(
                                "📄 PDF Raporu İndir", data=pdf_verisi,
                                file_name="deger_tespiti_raporu.pdf", mime="application/pdf",
                                use_container_width=True,
                            )
 
                    st.markdown("---")
                    st.markdown("### 🏦 Kredi Hesaplayıcı")
                    kk1, kk2, kk3 = st.columns(3)
                    pesinat_orani = kk1.slider("Peşinat Oranı (%)", 0, 90, 20)
                    faiz_orani = kk2.number_input("Yıllık Faiz Oranı (%)", min_value=0.0, max_value=100.0, value=3.5, step=0.1)
                    vade_ay = kk3.selectbox("Vade (Ay)", options=[12, 24, 36, 60, 120, 180], index=3)
 
                    kredi_sonuc = kredi_hesapla(nihai_deger, pesinat_orani, faiz_orani, vade_ay)
                    kk4, kk5, kk6 = st.columns(3)
                    kk4.metric("Peşinat Tutarı", f"{kredi_sonuc['pesinat_tutari']:,.0f} ₺")
                    kk5.metric("Aylık Taksit", f"{kredi_sonuc['aylik_taksit']:,.0f} ₺")
                    kk6.metric("Toplam Ödenecek", f"{kredi_sonuc['toplam_odeme']:,.0f} ₺")
 
                    st.markdown("### 🏚️ Deprem Yönetmeliği Bilgisi")

                    yapim_yili_deger = en_yakin_satir.get("yapim_yili")
                    yapim_yili_turetildi = False

                    # yapim_yili boşsa (None/NaN), bina_yasi'ndan türetmeyi dene.
                    if yapim_yili_deger is None or (isinstance(yapim_yili_deger, float) and pd.isna(yapim_yili_deger)):
                        bina_yasi_deger = en_yakin_satir.get("bina_yasi")
                        if bina_yasi_deger is not None and not (isinstance(bina_yasi_deger, float) and pd.isna(bina_yasi_deger)):
                            bugunku_yil = datetime.datetime.now().year
                            yapim_yili_deger = bugunku_yil - int(bina_yasi_deger)
                            yapim_yili_turetildi = True

                    deprem_bilgi = deprem_yonetmeligi_kontrol(yapim_yili_deger)
                    if deprem_bilgi["renk"] == "red":
                        st.error(f"**{deprem_bilgi['baslik']}**\n\n{deprem_bilgi['mesaj']}")
                    elif deprem_bilgi["renk"] == "orange":
                        st.warning(f"**{deprem_bilgi['baslik']}**\n\n{deprem_bilgi['mesaj']}")
                    elif deprem_bilgi["renk"] == "green":
                        st.success(f"**{deprem_bilgi['baslik']}**\n\n{deprem_bilgi['mesaj']}")
                    else:
                        st.info(f"**{deprem_bilgi['baslik']}**\n\n{deprem_bilgi['mesaj']}")

                    if yapim_yili_turetildi:
                        st.caption("Not: Yapım yılı doğrudan veride yoktu, bina yaşından tahmin edilmiştir (yaklaşık değerdir).")
                    st.caption("Not: En yakın emsalin yapım yılına dayalı genel bilgidir, profesyonel deprem risk analizi yerine geçmez.") 
 
                    st.markdown("### 💰 Kira Getirisi Tahmini")
                    st.caption("Veri setinde gerçek kira verisi yok — aşağıdaki oran tamamen sizin varsayımınıza dayalı bir hesaplama aracıdır.")
                    getiri_orani = st.slider("Varsayılan Yıllık Brüt Kira Getiri Oranı (%)", 1.0, 10.0, 4.0, 0.5)
                    kira_sonuc = kira_getirisi_hesapla(nihai_deger, getiri_orani)
                    kg1, kg2, kg3 = st.columns(3)
                    kg1.metric("Tahmini Aylık Kira", f"{kira_sonuc['aylik_kira_tahmini']:,.0f} ₺")
                    kg2.metric("Yıllık Kira Geliri", f"{kira_sonuc['yillik_kira_geliri']:,.0f} ₺")
                    kg3.metric("Geri Ödeme Süresi", f"{kira_sonuc['geri_odeme_suresi_yil']:,.1f} yıl" if kira_sonuc['geri_odeme_suresi_yil'] else "-")
 
                    st.markdown("### 🏘️ Yakın Çevre Puanı")
                    with st.spinner("Yakın çevredeki okul, sağlık, ulaşım ve market bilgisi alınıyor..."):
                        cevre_sonuc = yakin_cevre_puani_hesapla(aranan_konum["lat"], aranan_konum["lon"])
                    if cevre_sonuc:
                        st.metric("Yaşanabilirlik Puanı", f"{cevre_sonuc['puan']} / 100")
                        detay_kolonlar = st.columns(5)
                        etiketler = {"okul": "🏫 Okul", "saglik": "🏥 Sağlık", "toplu_tasima": "🚌 Durak", "market": "🛒 Market", "park": "🌳 Park"}
                        for col, (kategori, adet) in zip(detay_kolonlar, cevre_sonuc["detaylar"].items()):
                            col.metric(etiketler[kategori], adet)
                        st.caption(f"Kaynak: OpenStreetMap, {cevre_sonuc['yaricap_m']}m yarıçap içinde.")
                    else:
                        st.info("Yakın çevre verisi şu an alınamadı (internet bağlantısını veya Overpass API erişimini kontrol edin).")
            else:
                st.warning(f"Bu konumun {arama_yaricapi_km} km çevresinde emsal bulunamadı. Yarıçapı artırmayı deneyin.")
 
    with col2:
        st.subheader("İlçe Karşılaştırması")
 
        if len(filtreli_df) > 0:
            ilce_ozet = (
                filtreli_df.groupby("ilce")
                .agg(ortalama_m2_fiyat=("m2_fiyat_guncel", "mean"), kayit_sayisi=("m2_fiyat_guncel", "count"))
                .reset_index()
                .sort_values("ortalama_m2_fiyat", ascending=False)
            )
 
            fig = px.bar(
                ilce_ozet, x="ilce", y="ortalama_m2_fiyat",
                labels={"ilce": "İlçe", "ortalama_m2_fiyat": "Ort. m² Fiyatı (₺)"},
                color_discrete_sequence=["#3B82F6"],
            )
            fig.update_layout(template="plotly_white", margin=dict(t=20, l=10, r=10, b=10))
            fig.update_yaxes(tickformat=",.0f", ticksuffix=" ₺")
 
            filtre_imzasi = f"{tuple(sorted(secili_ilceler))}_{m2_araligi}"
            st.plotly_chart(
                fig,
                use_container_width=True,
                key=f"ilce_karsilastirma_{hash(filtre_imzasi)}",
            )
        else:
            st.info("İlçe karşılaştırması için veri bulunamadı.")
 
        st.markdown("---")
        st.subheader("Zaman İçinde m² Fiyatı")
        if len(filtreli_df) > 0 and filtreli_df["rapor_yili"].notna().sum() > 0:
            zaman_ozet = (
                filtreli_df.dropna(subset=["rapor_yili"])
                .groupby("rapor_yili")
                .agg(
                    guncel=("m2_fiyat_guncel", "mean"),
                    ham=("m2_fiyat", "mean"),
                    adet=("m2_fiyat", "count"),
                )
                .reset_index()
                .sort_values("rapor_yili")
            )
            zaman_ozet_uzun = zaman_ozet.melt(
                id_vars=["rapor_yili", "adet"], value_vars=["guncel", "ham"],
                var_name="tip", value_name="m2_fiyat",
            )
            zaman_ozet_uzun["tip"] = zaman_ozet_uzun["tip"].map({
                "guncel": "Bugüne Taşınmış (KFE ile)", "ham": "Ham (O Yılın Fiyatı)",
            })
            fig_zaman = px.line(
                zaman_ozet_uzun, x="rapor_yili", y="m2_fiyat", color="tip", markers=True,
                labels={"rapor_yili": "Rapor Yılı", "m2_fiyat": "Ort. m² Fiyatı (₺)", "tip": ""},
            )
            fig_zaman.update_layout(template="plotly_white", margin=dict(t=20, l=10, r=10, b=10), legend=dict(orientation="h", y=-0.3))
            fig_zaman.update_yaxes(tickformat=",.0f", ticksuffix=" ₺")
            st.plotly_chart(
                fig_zaman, use_container_width=True,
                key=f"zaman_serisi_{hash(filtre_imzasi)}",
            )
        else:
            st.info("Seçili filtrelerde yıl bilgisi bulunan yeterli veri yok.")
 
        st.markdown("---")
        st.subheader("KFE ile Geçmiş Değer Güncelleme")
        gecmis_deger = st.number_input("Geçmiş değer (₺)", min_value=0, value=1_000_000, step=50_000)
        gecmis_tarih = st.text_input("Tarih (YYYY-MM)", value="2019-01")
        if st.button("Güncelle"):
            try:
                sonuc = kfe_ile_guncelle(gecmis_deger, gecmis_tarih, kfe_df)
                st.info(
                    f"**{gecmis_tarih}** tarihindeki {gecmis_deger:,.0f} ₺, "
                    f"KFE'ye göre **{sonuc['guncel_endeks_tarihi']}** itibarıyla "
                    f"**{sonuc['guncel_deger']:,.0f} ₺**'ye karşılık geliyor "
                    f"(%{sonuc['artis_orani_yuzde']:.1f} artış)."
                )
            except ValueError as e:
                st.error(str(e))
 
        st.markdown("---")
        st.subheader("Tüm İlçeler Tablosu")
        if len(filtreli_df) > 0:
            st.dataframe(
                ilce_ozet.rename(columns={
                    "ilce": "İlçe", "ortalama_m2_fiyat": "Ort. m² Fiyatı (₺)", "kayit_sayisi": "Kayıt Sayısı"
                }),
                use_container_width=True, hide_index=True,
            )
 
# ---------------- TAB 2: TÜİK DEMOGRAFİ ANALİZİ ----------------
with tab_tuik:
    st.header("📊 TÜİK Kayseri Demografi Analizi")
    st.caption("Kaynak: nip.tuik.gov.tr — kayıtlı veri, sol paneldeki butonla güncellenir")
 
    if df_flat is None:
        st.warning("Henüz TÜİK verisi çekilmemiş. Sol paneldeki '🔄 TÜİK Verilerini Yenile' butonunu kullanın.")
    else:
        df_kayseri = df_flat[df_flat["İl"] == "KAYSERİ"]
        json_kayseri = json_veri.get("KAYSERİ", {})
 
        # ---- NÜFUS ----
        st.subheader("👥 Nüfus")
        n1, n2 = st.columns(2)
        with n1:
            fig = nufus_simdiki_grafik(df_kayseri)
            if fig:
                st.plotly_chart(fig, use_container_width=True, key="nufus_simdiki")
        with n2:
            fig = nufus_tarihsel_grafik(json_kayseri)
            if fig:
                st.plotly_chart(fig, use_container_width=True, key="nufus_tarihsel")
 
        nufus_tekil = df_kayseri[
            (df_kayseri["Kategori"] == "NÜFUS")
            & (~df_kayseri["Gösterge"].isin(["Erkek", "Kadın"]))
        ]
        if not nufus_tekil.empty:
            metrik_kolonlar = st.columns(len(nufus_tekil))
            for col, (_, satir) in zip(metrik_kolonlar, nufus_tekil.iterrows()):
                col.metric(satir["Gösterge"], satir["Değer"])
 
        st.markdown("#### 🗺️ Türkiye Haritasında Kayseri")
        geojson_veri = turkiye_geojson_yukle()
        harita = turkiye_haritasi_olustur(geojson_veri, "KAYSERİ")
        if harita:
            st_folium(harita, width=None, height=450, key="tuik_turkiye_haritasi", returned_objects=[])
        else:
            st.info("Harita verisi indirilemedi (internet bağlantısını kontrol edin).")
 
        st.divider()
 
        # ---- GÖÇ ----
        st.subheader("🚚 Göç")
        fig = goc_grafik(df_kayseri)
        if fig:
            st.plotly_chart(fig, use_container_width=True, key="goc_grafik")
 
        st.divider()
 
        # ---- HANEHALKI ----
        st.subheader("👨‍👩‍👧‍👦 Hanehalkı Nitelikleri")
        h1, h2 = st.columns([1, 1])
        with h1:
            fig = hanehalki_kompozisyon_grafik(df_kayseri)
            if fig:
                st.plotly_chart(fig, use_container_width=True, key="hanehalki_grafik")
        with h2:
            hane_tekil = df_kayseri[
                (df_kayseri["Kategori"] == "HANEHALKI NİTELİKLERİ")
                & (df_kayseri["Gösterge"].isin(["Toplam Hanehalkı Sayısı", "Ortalama Hanehalkı Büyüklüğü"]))
            ]
            for _, satir in hane_tekil.iterrows():
                st.metric(satir["Gösterge"], satir["Değer"])
 
        st.divider()
 
        # ---- MEDENİ DURUM ----
        st.subheader("💍 Medeni Durum")
        fig = medeni_durum_grafik(df_kayseri)
        if fig:
            st.plotly_chart(fig, use_container_width=True, key="medeni_durum_grafik")
 
        st.divider()
 
        # ---- EĞİTİM DURUMU ----
        st.subheader("🎓 Eğitim Durumu")
        fig = egitim_durumu_grafik(df_kayseri)
        if fig:
            st.plotly_chart(fig, use_container_width=True, key="egitim_durumu_grafik")
 
        st.divider()
 
        # ---- HAYATİ İSTATİSTİKLER ----
        st.subheader("❤️ Hayati İstatistikler")
        kartlar = kategori_kartlari(df_kayseri, "HAYATİ İSTATİSTİKLER")
        if kartlar:
            kolonlar = st.columns(4)
            for i, (etiket, deger) in enumerate(kartlar):
                kolonlar[i % 4].metric(etiket, deger)
 
        st.divider()
 
        # ---- İSİM İSTATİSTİKLERİ ----
        st.subheader("📛 İsim İstatistikleri")
        kartlar = kategori_kartlari(df_kayseri, "İSİM İSTATİSTİKLER")
        if kartlar:
            kolonlar = st.columns(len(kartlar))
            for col, (etiket, deger) in zip(kolonlar, kartlar):
                col.metric(etiket, deger)
 
        st.divider()
 
        # ---- KONUT TALEP TAHMİN ENDEKSİ ----
        st.subheader("🎯 Konut Talep Tahmin Endeksi")
        st.caption(
            "Evlenme/boşanma dinamiği, net göç hızı ve nüfus artış hızından türetilen, "
            "kural tabanlı ve açıklanabilir bir endeks. Bir regresyon/ML tahmini değildir."
        )
 
        with st.expander("⚙️ Ağırlıkları Ayarla (varsayılan: 0.4 / 0.3 / 0.3)", expanded=False):
            ag1, ag2, ag3 = st.columns(3)
            agirlik_evlilik = ag1.slider("Hanehalkı Oluşumu Ağırlığı", 0.0, 1.0, 0.4, 0.05)
            agirlik_goc = ag2.slider("Net Göç Ağırlığı", 0.0, 1.0, 0.3, 0.05)
            agirlik_nufus = ag3.slider("Nüfus Artışı Ağırlığı", 0.0, 1.0, 0.3, 0.05)
 
        talep_sonucu = talep_endeksi_hesapla(
            json_veri,
            agirlik_evlilik=agirlik_evlilik,
            agirlik_goc=agirlik_goc,
            agirlik_nufus=agirlik_nufus,
        )
 
        if talep_sonucu["endeks"] is not None:
            te1, te2 = st.columns([1, 2])
            with te1:
                st.metric("Kayseri Geneli Talep Endeksi", f"{talep_sonucu['endeks']:.1f} / 100")
                if talep_sonucu["eksik_veri_uyarisi"]:
                    st.caption(f"⚠️ {talep_sonucu['eksik_veri_uyarisi']}")
            with te2:
                bilesen_df = pd.DataFrame([
                    {"Bileşen": k, "Puan": v}
                    for k, v in talep_sonucu["bilesen_puanlari"].items() if v is not None
                ])
                if not bilesen_df.empty:
                    fig_bilesen = px.bar(
                        bilesen_df, x="Bileşen", y="Puan", range_y=[0, 100],
                        color_discrete_sequence=["#2563EB"],
                    )
                    fig_bilesen.update_layout(template="plotly_white", margin=dict(t=10, l=10, r=10, b=10), height=280)
                    st.plotly_chart(fig_bilesen, use_container_width=True, key="talep_bilesen_grafik")
 
            with st.expander("📐 Hesaplama Detayı (Ham Veriler)"):
                ham = talep_sonucu["ham_veri"]
                st.write(f"- Evlenme Sayısı: **{ham['evlenme_sayisi']:,.0f}**" if ham["evlenme_sayisi"] else "- Evlenme Sayısı: bulunamadı")
                st.write(f"- Boşanma Sayısı: **{ham['bosanma_sayisi']:,.0f}**" if ham["bosanma_sayisi"] else "- Boşanma Sayısı: bulunamadı")
                st.write(f"- Net Göç (ham sayı): **{ham['net_goc_sayisi']:,.0f}**" if ham["net_goc_sayisi"] is not None else "- Net Göç (ham sayı): bulunamadı")
                st.write(f"- Net Göç Hızı: **{ham['net_goc_hizi']:,.1f} ‰**" if ham["net_goc_hizi"] is not None else "- Net Göç Hızı: bulunamadı")
                st.write(f"- Nüfus Artış Hızı: **{ham['nufus_artis_hizi']:,.1f} ‰**" if ham["nufus_artis_hizi"] is not None else "- Nüfus Artış Hızı: bulunamadı")
 
            st.markdown("#### 🏘️ İlçe Yatırım Skoru")
            st.caption("İl geneli talep tabanı (%50) + ilçe bazlı fiyat momentumu (%35) + kayıt likiditesi (%15)")
            ilce_skor_df = ilce_yatirim_skoru_hesapla(df, talep_sonucu)
            if not ilce_skor_df.empty:
                fig_ilce_skor = px.bar(
                    ilce_skor_df, x="ilce", y="yatirim_skoru",
                    labels={"ilce": "İlçe", "yatirim_skoru": "Yatırım Skoru"},
                    color="yatirim_skoru", color_continuous_scale="Blues",
                )
                fig_ilce_skor.update_layout(template="plotly_white", margin=dict(t=10, l=10, r=10, b=10))
                st.plotly_chart(fig_ilce_skor, use_container_width=True, key="ilce_yatirim_skoru_grafik")
                st.dataframe(
                    ilce_skor_df.rename(columns={
                        "ilce": "İlçe", "ortalama_m2_fiyat": "Ort. m² Fiyatı (₺)",
                        "kayit_sayisi": "Kayıt Sayısı", "fiyat_momentumu_yuzde": "Fiyat Momentumu (%)",
                        "momentum_puani": "Momentum Puanı", "likidite_puani": "Likidite Puanı",
                        "yatirim_skoru": "Yatırım Skoru",
                    }),
                    use_container_width=True, hide_index=True,
                )
            else:
                st.info("İlçe yatırım skoru için yeterli emlak kaydı yok (filtreleri gevşetmeyi deneyin).")
        else:
            st.warning(talep_sonucu["eksik_veri_uyarisi"] or "Talep endeksi için gerekli TÜİK göstergeleri bulunamadı.")
 