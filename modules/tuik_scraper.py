"""
TÜİK Nüfus İstatistikleri Portalı - Kayseri Çoklu Veri Kazıma Modülü (KEŞİF SÜRÜMÜ)
Kaynak: nip.tuik.gov.tr

Bu sürüm "keşif modu" içerir: her sayfaya girer, sayfadaki TÜM <select>
elementlerinin id/name/seçeneklerini ve TÜM <table> elementlerinin
class/id'lerini terminale yazdırır. Bu bilgiyi kullanarak bir sonraki
adımda her sayfa için kesin doğru seçicileri (selector) yazacağız.

Çalıştırmak için:
    python -m modules.tuik_scraper
(proje ana klasöründeyken)
"""

import os
import time
from io import StringIO
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC

DATA_DIR = os.path.join("data", "tuik_kayseri")

# Doğrulanmış gerçek URL'ler (nip.tuik.gov.tr ana sayfasından alındı)
ENDPOINTS = [
    {"name": "bina_insa_yili", "url": "https://nip.tuik.gov.tr/?value=BinaIstatistikleri", "gender": None},
    {"name": "konut_mulkiyet_durumu", "url": "https://nip.tuik.gov.tr/?value=KonutIstatistikleri", "gender": None},
    {"name": "dogum_yeri_nufus", "url": "https://nip.tuik.gov.tr/?value=DogumYerineNufus", "gender": None},
    {"name": "egitim_durumu_kadin", "url": "https://nip.tuik.gov.tr/?value=EgitimDurumu", "gender": "Kadın"},
    {"name": "egitim_durumu_erkek", "url": "https://nip.tuik.gov.tr/?value=EgitimDurumu", "gender": "Erkek"},
    {"name": "okuma_yazma_durumu", "url": "https://nip.tuik.gov.tr/?value=OkumaYazmaDurumu", "gender": None},
    {"name": "goc_ulke_ici", "url": "https://nip.tuik.gov.tr/?value=UlkeIciGoc", "gender": None},
    {"name": "goc_iller_arasi", "url": "https://nip.tuik.gov.tr/?value=IllerArasiGoc", "gender": None},
    {"name": "goc_etme_nedenleri", "url": "https://nip.tuik.gov.tr/?value=GocEtmeNedenleri", "gender": None},
    {"name": "goc_uluslararasi", "url": "https://nip.tuik.gov.tr/?value=UluslararasiGoc", "gender": None},
    {"name": "hanehalki_sayisi", "url": "https://nip.tuik.gov.tr/?value=HanehalkiSayisi", "gender": None},
    {"name": "hanehalki_buyuklugune_gore", "url": "https://nip.tuik.gov.tr/?value=HanehalkiBuyukluguneGoreHs", "gender": None},
    {"name": "hanehalki_tipi", "url": "https://nip.tuik.gov.tr/?value=HanehalkiTipi", "gender": None},
    {"name": "ortalama_hanehalki_buyuklugu", "url": "https://nip.tuik.gov.tr/?value=OrtalamaHanehalkiBuyuklugu", "gender": None},
    {"name": "medeni_durum", "url": "https://nip.tuik.gov.tr/?value=MedeniDurum", "gender": None},
    {"name": "il_gosterge_karti", "url": "https://nip.tuik.gov.tr/?value=IlGostergeKartlari", "gender": None},
]


def setup_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    return webdriver.Chrome(options=chrome_options)


def sayfayi_kesfet(driver, ep):
    """
    Bir sayfaya girer, JS'in yüklenmesini bekler, sonra sayfadaki TÜM
    select ve table elementlerinin bilgisini terminale yazdırır.
    """
    print(f"\n{'=' * 70}")
    print(f"SAYFA: {ep['name']}  ({ep['url']})")
    print(f"{'=' * 70}")

    driver.get(ep["url"])

    # JS'in dropdown'ları oluşturmasını bekle (en az 1 select elementi çıkana kadar)
    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "select"))
        )
    except Exception:
        print("  [UYARI] 15 saniye içinde hiç <select> elementi çıkmadı. Sayfa yapısı farklı olabilir.")

    time.sleep(2)  # JS'in tamamen oturması için ekstra bekleme

    # Tüm select'leri listele
    selects = driver.find_elements(By.TAG_NAME, "select")
    print(f"\n  Bulunan <select> sayısı: {len(selects)}")
    for i, sel in enumerate(selects):
        try:
            sel_id = sel.get_attribute("id") or "(id yok)"
            sel_name = sel.get_attribute("name") or "(name yok)"
            options = [o.text.strip() for o in Select(sel).options][:8]  # ilk 8 seçenek
            print(f"    [{i}] id='{sel_id}' name='{sel_name}' -> ilk seçenekler: {options}")
        except Exception as e:
            print(f"    [{i}] okunamadı: {e}")

    # Tüm table'ları listele
    tables = driver.find_elements(By.TAG_NAME, "table")
    print(f"\n  Bulunan <table> sayısı: {len(tables)}")
    for i, tbl in enumerate(tables):
        try:
            tbl_id = tbl.get_attribute("id") or "(id yok)"
            tbl_class = tbl.get_attribute("class") or "(class yok)"
            satir_sayisi = len(tbl.find_elements(By.TAG_NAME, "tr"))
            print(f"    [{i}] id='{tbl_id}' class='{tbl_class}' -> {satir_sayisi} satır")
        except Exception as e:
            print(f"    [{i}] okunamadı: {e}")

    # "Tablo" butonu var mı kontrol et (bazı sayfalarda grafik/tablo geçişi olabilir)
    try:
        tablo_butonlari = driver.find_elements(
            By.XPATH, "//button[contains(text(),'Tablo')] | //a[contains(text(),'Tablo')]"
        )
        print(f"\n  'Tablo' metni içeren buton/link sayısı: {len(tablo_butonlari)}")
    except Exception:
        pass

    # Harita (SVG/canvas) elementi var mı kontrol et
    try:
        svg_sayisi = len(driver.find_elements(By.TAG_NAME, "svg"))
        canvas_sayisi = len(driver.find_elements(By.TAG_NAME, "canvas"))
        print(f"  <svg> sayısı: {svg_sayisi}, <canvas> sayısı: {canvas_sayisi} (harita/grafik bu ikisinden biriyle çizilmiş olabilir)")
    except Exception:
        pass


import json
import re
from bs4 import BeautifulSoup


def il_gosterge_kart_verisi_parse(html):
    """
    İl Gösterge Kartı sayfasının HTML'inden #tabloIcerik .card bloklarını
    okuyup {kart_basligi: {etiket: değer, ...}, ...} sözlüğü döner.
    """
    soup = BeautifulSoup(html, "html.parser")
    sonuc = {}

    kartlar = soup.select("#tabloIcerik .card")
    for kart in kartlar:
        basliklar = [h6.get_text(strip=True) for h6 in kart.select(".card-header h6")]
        if not basliklar:
            continue

        # Dış sarmalayıcı <div class="card"> tüm alt kartları içine aldığı için
        # onun .card-header h6 sorgusu TÜM alt başlıkları (Nüfus, Göç, ...)
        # birden yakalar -> bunları "gerçek" bir kart gibi eklemeyelim.
        if len(basliklar) > 2:
            continue

        kart_basligi = " / ".join(basliklar)

        veriler = {}
        dt_listesi = kart.select("dt")
        dd_listesi = kart.select("dd")
        for dt, dd in zip(dt_listesi, dd_listesi):
            etiket = dt.get_text(strip=True)
            deger = dd.get_text(strip=True)
            if etiket:
                veriler[etiket] = deger

        if veriler:
            sonuc[kart_basligi] = veriler

    return sonuc


def grafik_verisini_parse(html):
    """
    Sayfadaki <script> içinde JSON.parse('[...]') şeklinde gömülü olan
    nüfus grafiği verisini (yıllar + Erkek/Kadın serileri) regex ile çeker.
    """
    etiketler_match = re.search(r"labels:\s*JSON\.parse\('(\[[^\]]+\])'\)", html)
    etiketler = json.loads(etiketler_match.group(1)) if etiketler_match else None

    seri_eslesmeleri = re.findall(
        r'label:\s*"([^"]+)",\s*data:\s*JSON\.parse\(\'(\[[^\]]+\])\'\)', html
    )
    seriler = []
    for ad, veri_str in seri_eslesmeleri:
        try:
            seriler.append({"ad": ad, "veri": json.loads(veri_str)})
        except json.JSONDecodeError:
            pass

    return {"yillar": etiketler, "seriler": seriler}


def il_gosterge_karti_tam_cek(iller=None):
    """
    İl Gösterge Kartı sayfasından, verilen il listesi için (varsayılan: KAYSERİ)
    tüm demografik göstergeleri (Nüfus, Göç, Hanehalkı, Medeni Durum, Eğitim,
    Hayati İstatistikler, İsim İstatistikleri) ve nüfus grafiğinin ham
    (yıl bazlı Erkek/Kadın) verisini çeker.

    Dönüş: {il_adi: {"kartlar": {...}, "nufus_grafigi": {...}}, ...}
    Ayrıca sonucu data/tuik_kayseri/il_gosterge_kartlari.json'a kaydeder ve
    app.py'nin kolayca gösterebilmesi için düz (flat) bir DataFrame de üretir.
    """
    if iller is None:
        iller = ["KAYSERİ"]

    os.makedirs(DATA_DIR, exist_ok=True)
    driver = setup_driver()
    tum_sonuclar = {}

    try:
        url = "https://nip.tuik.gov.tr/?value=IlGostergeKartlari"
        print(f"Sayfaya gidiliyor: {url}")
        driver.get(url)
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.ID, "tableIl")))
        time.sleep(1.5)

        for il in iller:
            print(f"--> {il} için veri çekiliyor...")

            # Önce bilerek FARKLI bir ile geçiyoruz ki, hedef il zaten seçili
            # olsa bile jQuery 'change' event'i kesin tetiklensin.
            try:
                driver.execute_script("""
                    $('#tableIl').val('ADANA').trigger('change');
                """)
                time.sleep(1.5)
            except Exception as e:
                print(f"    (ön-değiştirme uyarısı: {e})")

            # Şimdi JS ile DEĞERİ ZORLA ayarlayıp change event'ini tetikliyoruz
            # (Selenium'un native select_by_value'suna ek güvence olarak).
            driver.execute_script(
                "$('#tableIl').val(arguments[0]).trigger('change');", il
            )

            # #tabloIcerik içeriğinin GERÇEKTEN güncellendiğini bekle:
            # aranan ilin adı metin olarak sayfada görünene kadar bekle.
            try:
                WebDriverWait(driver, 15).until(
                    lambda d: il in d.find_element(By.ID, "tabloIcerik").text
                    and "Toplam" in d.find_element(By.ID, "tabloIcerik").text
                )
            except Exception as e:
                print(f"    [UYARI] Veri yüklenmesi beklenirken zaman aşımı: {e}")

            time.sleep(1)  # ekstra güvenlik payı

            html = driver.page_source
            print(f"    Sayfa HTML uzunluğu: {len(html)} karakter, 'Toplam' geçiyor mu: {'Toplam' in html}")

            kartlar = il_gosterge_kart_verisi_parse(html)
            grafik = grafik_verisini_parse(html)

            print(f"    {len(kartlar)} kart bulundu: {list(kartlar.keys())}")
            print(f"    Grafik: {len(grafik['seriler'])} seri, {len(grafik['yillar'] or [])} yıl")

            tum_sonuclar[il] = {"kartlar": kartlar, "nufus_grafigi": grafik}

        json_yolu = os.path.join(DATA_DIR, "il_gosterge_kartlari.json")
        with open(json_yolu, "w", encoding="utf-8") as f:
            json.dump(tum_sonuclar, f, ensure_ascii=False, indent=2)
        print(f"\nJSON kaydedildi: {json_yolu}")

        # app.py'nin mevcut tablo/grafik gösterim mantığına uysun diye
        # düz (flat) bir CSV de üretelim: İl, Kategori, Gösterge, Değer
        satirlar = []
        for il, veri in tum_sonuclar.items():
            for kategori, gostergeler in veri["kartlar"].items():
                for gosterge, deger in gostergeler.items():
                    satirlar.append({"İl": il, "Kategori": kategori, "Gösterge": gosterge, "Değer": deger})
        df_flat = pd.DataFrame(satirlar)
        csv_yolu = os.path.join(DATA_DIR, "il_gosterge_kartlari.csv")
        df_flat.to_csv(csv_yolu, index=False, encoding="utf-8-sig")
        print(f"CSV kaydedildi: {csv_yolu}")

    finally:
        driver.quit()

    return tum_sonuclar


def il_gosterge_karti_cek():
    """
    'İl Gösterge Kartı' sayfasına gider, İl olarak KAYSERİ'yi seçer,
    sayfadaki tüm grafiklerin arkasındaki gerçek sayısal veriyi (Highcharts/
    Chart.js JS nesnelerinden) çekmeye çalışır. Bulamazsa grafiklerin
    ekran görüntüsünü alır (yedek plan).
    Sonuçları data/tuik_kayseri/il_gosterge_karti_veri.json ve
    data/tuik_kayseri/screenshots/ altına kaydeder.
    """
    os.makedirs(DATA_DIR, exist_ok=True)
    screenshot_dir = os.path.join(DATA_DIR, "screenshots")
    os.makedirs(screenshot_dir, exist_ok=True)

    driver = setup_driver()
    try:
        url = "https://nip.tuik.gov.tr/?value=IlGostergeKartlari"
        print(f"Sayfaya gidiliyor: {url}")
        driver.get(url)

        try:
            WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, "select")))
        except Exception:
            print("[UYARI] 15 saniyede select çıkmadı, yine de devam ediliyor.")
        time.sleep(2)

        # İl dropdown'unu bul ve KAYSERİ'yi seç
        secildi = False
        selects = driver.find_elements(By.TAG_NAME, "select")
        print(f"Bulunan <select> sayısı: {len(selects)}")
        for i, sel in enumerate(selects):
            try:
                sel_id = sel.get_attribute("id") or ""
                sel_name = sel.get_attribute("name") or ""
                secenekler = [o.text.strip() for o in Select(sel).options]
                print(f"  [{i}] id='{sel_id}' name='{sel_name}' seçenekler(ilk 5): {secenekler[:5]}")
                if any("KAYSERİ" in s.upper() for s in secenekler):
                    Select(sel).select_by_visible_text(
                        next(s for s in secenekler if "KAYSERİ" in s.upper())
                    )
                    print(f"  -> KAYSERİ bu dropdown'da seçildi: index {i}")
                    secildi = True
                    time.sleep(2.5)
                    break
            except Exception as e:
                print(f"  [{i}] hata: {e}")

        if not secildi:
            print("[UYARI] KAYSERİ seçeneği hiçbir dropdown'da bulunamadı!")

        time.sleep(2)

        # 1. YÖNTEM: Highcharts verisi var mı JS ile kontrol et
        highcharts_verisi = None
        try:
            highcharts_verisi = driver.execute_script("""
                if (typeof Highcharts !== 'undefined' && Highcharts.charts) {
                    return Highcharts.charts.filter(c => c).map(c => ({
                        baslik: c.title ? c.title.textStr : null,
                        seriler: c.series.map(s => ({
                            ad: s.name,
                            veri: s.data.map(p => ({
                                kategori: p.name || p.category || null,
                                deger: p.y
                            }))
                        }))
                    }));
                }
                return null;
            """)
        except Exception as e:
            print(f"Highcharts JS okuma hatası: {e}")

        if highcharts_verisi:
            print(f"\n[BAŞARILI] Highcharts üzerinden {len(highcharts_verisi)} grafik verisi bulundu!")
            import json
            json_yolu = os.path.join(DATA_DIR, "il_gosterge_karti_veri.json")
            with open(json_yolu, "w", encoding="utf-8") as f:
                json.dump(highcharts_verisi, f, ensure_ascii=False, indent=2)
            print(f"Kaydedildi: {json_yolu}")
        else:
            print("\n[BİLGİ] Highcharts verisi bulunamadı. Chart.js deneniyor...")
            chartjs_verisi = None
            try:
                chartjs_verisi = driver.execute_script("""
                    var canvases = document.querySelectorAll('canvas');
                    var sonuc = [];
                    canvases.forEach(function(c) {
                        if (c.chart) {
                            sonuc.push({
                                etiketler: c.chart.data.labels,
                                datasetler: c.chart.data.datasets.map(d => ({ad: d.label, veri: d.data}))
                            });
                        }
                    });
                    return sonuc;
                """)
            except Exception as e:
                print(f"Chart.js JS okuma hatası: {e}")

            if chartjs_verisi:
                print(f"[BAŞARILI] Chart.js üzerinden {len(chartjs_verisi)} grafik verisi bulundu!")
                import json
                json_yolu = os.path.join(DATA_DIR, "il_gosterge_karti_veri.json")
                with open(json_yolu, "w", encoding="utf-8") as f:
                    json.dump(chartjs_verisi, f, ensure_ascii=False, indent=2)
                print(f"Kaydedildi: {json_yolu}")
            else:
                print("[BİLGİ] Chart.js verisi de bulunamadı. Ekran görüntüsü alınıyor (yedek plan)...")

        # 2. YÖNTEM (her durumda ek güvence): tabloları da dene
        try:
            tables = driver.find_elements(By.TAG_NAME, "table")
            print(f"\nBulunan <table> sayısı: {len(tables)}")
            for i, tbl in enumerate(tables):
                try:
                    html_content = tbl.get_attribute("outerHTML")
                    dfs = pd.read_html(StringIO(html_content))
                    if dfs:
                        csv_yolu = os.path.join(DATA_DIR, f"il_gosterge_karti_tablo_{i}.csv")
                        dfs[0].to_csv(csv_yolu, index=False, encoding="utf-8-sig")
                        print(f"  Tablo {i} kaydedildi: {csv_yolu}")
                except Exception as e:
                    print(f"  Tablo {i} okunamadı: {e}")
        except Exception:
            pass

        # 3. YÖNTEM: her durumda ekran görüntüsü de al (görsel referans için)
        try:
            tam_sayfa_yolu = os.path.join(screenshot_dir, "il_gosterge_karti_tam_sayfa.png")
            driver.save_screenshot(tam_sayfa_yolu)
            print(f"\nTam sayfa ekran görüntüsü kaydedildi: {tam_sayfa_yolu}")
        except Exception as e:
            print(f"Ekran görüntüsü alınamadı: {e}")

        # Grafik/kart elementlerini tek tek de görüntüle
        try:
            olasi_grafik_elemanlari = driver.find_elements(
                By.XPATH,
                "//div[contains(@class,'highcharts-container')] | //div[contains(@class,'chart')] | //div[contains(@class,'card')]"
            )
            print(f"Olası grafik/kart elementi sayısı: {len(olasi_grafik_elemanlari)}")
            for i, el in enumerate(olasi_grafik_elemanlari[:15]):
                try:
                    el_yolu = os.path.join(screenshot_dir, f"il_gosterge_karti_eleman_{i}.png")
                    el.screenshot(el_yolu)
                except Exception:
                    pass
        except Exception as e:
            print(f"Grafik elementleri işlenemedi: {e}")

    finally:
        driver.quit()

    print(f"\n{'=' * 70}")
    print(f"TAMAMLANDI. '{DATA_DIR}' ve '{screenshot_dir}' klasörlerini kontrol et.")
    print(f"{'=' * 70}")


def tum_sayfalari_kesfet():
    """Tüm ENDPOINTS listesindeki sayfaları gezip yapılarını terminale yazdırır."""
    os.makedirs(DATA_DIR, exist_ok=True)
    driver = setup_driver()
    try:
        for ep in ENDPOINTS:
            sayfayi_kesfet(driver, ep)
    finally:
        driver.quit()
    print(f"\n{'=' * 70}")
    print("KEŞİF TAMAMLANDI. Yukarıdaki tüm çıktıyı kopyalayıp paylaş.")
    print(f"{'=' * 70}")


# =========================================================================
# Bu fonksiyonlar app.py tarafından import ediliyor, keşif tamamlanana
# kadar geçici/basit bir davranışları var (henüz gerçek veri çekmiyor).
# =========================================================================

def tuik_kayseri_verilerini_cek(force_fetch=False):
    """
    app.py'deki 'TÜİK Verilerini Yenile' butonu tarafından çağrılır.
    İl Gösterge Kartı sayfasından KAYSERİ verisini yeniden çeker ve
    data/tuik_kayseri/il_gosterge_kartlari.csv + .json dosyalarını günceller.
    """
    il_gosterge_karti_tam_cek(iller=["KAYSERİ"])
    return {}  # app.py artık veriyi CSV/JSON'dan okuyor, bu dönüş değeri kullanılmıyor


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "il_gosterge":
        il_gosterge_karti_cek()
    elif len(sys.argv) > 1 and sys.argv[1] == "il_gosterge_tam":
        sonuc = il_gosterge_karti_tam_cek(iller=["KAYSERİ"])
        print("\n--- ÖZET ---")
        for il, veri in sonuc.items():
            print(f"\n{il}:")
            for kategori, gostergeler in veri["kartlar"].items():
                print(f"  {kategori}:")
                for g, d in gostergeler.items():
                    print(f"    {g}: {d}")
    else:
        tum_sayfalari_kesfet()
