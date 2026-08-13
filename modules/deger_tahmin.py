"""
Eğitilmiş m² fiyat modelini (data/m2_fiyat_modeli.joblib) yükleyip tek bir
taşınmaz için bugünkü değer tahmini üretir. app.py / appy.py bu modülü
çağırarak hem harita üstünden hem manuel formdan tahmin gösterebilir.
"""

import joblib
import pandas as pd

_model_cache = {}


def model_yukle(model_yolu: str = "data/m2_fiyat_modeli.joblib"):
    if model_yolu not in _model_cache:
        _model_cache[model_yolu] = joblib.load(model_yolu)
    return _model_cache[model_yolu]


def model_ile_deger_tahmini(
    lat: float, lon: float, m2: float, kat: float, bina_yasi: float,
    ilce: str, yapi_tarzi_kod, yapi_kalitesi_kod,
    model_yolu: str = "data/m2_fiyat_modeli.joblib",
) -> dict:
    """
    Model bugüne-taşınmış (KFE düzeltmeli) m² fiyatı üzerinden eğitildiği için
    döndürdüğü tahmin zaten "bugünkü TL" cinsindendir; ayrıca bir endeks
    güncellemesi yapmaya gerek yoktur. Aşınma payı (bina fiziksel durumu)
    hâlâ ayrıca uygulanmalıdır — o, enflasyondan bağımsız, tamamen farklı
    bir düzeltmedir (bkz. asinma_payi.py).

    NOT: kat_bilinmiyor / bina_yasi_bilinmiyor sütunları model_egit.py'deki
    veri_hazirla() içinde eğitim verisine otomatik eklenmişti (eksik kat/
    bina_yasi'yi medyanla doldurup "bu değer aslında bilinmiyordu" bilgisini
    ayrı bir bayrakla taşımak için). Kullanıcı burada kat ve bina_yasi'yi
    GERÇEKTEN girdiği için bu iki bayrak her zaman 0 (yani "biliniyor").
    civar_ortalama_m2_fiyat sütununu elle eklemeye gerek yok; pipeline'ın
    ilk adımı (CivarOrtalamaFiyatEkleyici) bunu lat/lon'dan otomatik hesaplar.
    """
    model = model_yukle(model_yolu)

    # Eğitimde (veri_hazirla) yapi_tarzi_kod / yapi_kalitesi_kod boşsa
    # "Bilinmiyor" metnine çevrilmişti. Tahmin sırasında da AYNI dönüşüm
    # yapılmazsa (örn. en_yakin_satir'dan gelen değer NaN ise) OneHotEncoder
    # NaN'ı tanımadığı için hata verir. Burada aynı kuralı uyguluyoruz.
    def _kategori_temizle(deger):
        if deger is None or (isinstance(deger, float) and pd.isna(deger)):
            return "Bilinmiyor"
        if isinstance(deger, str) and deger.strip() == "":
            return "Bilinmiyor"
        return str(deger)

    yapi_tarzi_kod = _kategori_temizle(yapi_tarzi_kod)
    yapi_kalitesi_kod = _kategori_temizle(yapi_kalitesi_kod)

    # kat / bina_yasi de teorik olarak NaN gelebilir (örn. en_yakin_satir
    # içinde eksikse) -- bu durumda modele boş değer değil, eğitimdekiyle
    # tutarlı bir "bilinmiyor" bayrağı + medyan mantığı gerekir. En basit
    # ve güvenli çözüm: NaN ise bayrağı 1 yapıp 0 gönder (RandomForest bu
    # ikiliye zaten eğitimde alışkın); değer varsa bayrak 0.
    kat_bilinmiyor = 1 if (kat is None or (isinstance(kat, float) and pd.isna(kat))) else 0
    bina_yasi_bilinmiyor = 1 if (bina_yasi is None or (isinstance(bina_yasi, float) and pd.isna(bina_yasi))) else 0
    kat_guvenli = 0 if kat_bilinmiyor else kat
    bina_yasi_guvenli = 0 if bina_yasi_bilinmiyor else bina_yasi

    girdi = pd.DataFrame([{
        "lat": lat, "lon": lon, "m2": m2,
        "kat": kat_guvenli, "bina_yasi": bina_yasi_guvenli,
        "kat_bilinmiyor": kat_bilinmiyor, "bina_yasi_bilinmiyor": bina_yasi_bilinmiyor,
        "ilce": ilce, "yapi_tarzi_kod": yapi_tarzi_kod,
        "yapi_kalitesi_kod": yapi_kalitesi_kod,
    }])

    tahmini_m2_fiyat = float(model.predict(girdi)[0])
    tahmini_deger = tahmini_m2_fiyat * m2

    return {
        "tahmini_m2_fiyat": tahmini_m2_fiyat,
        "tahmini_deger": tahmini_deger,
    }


def emsal_ve_model_birlestir(
    emsal_ortalama_m2_fiyat_guncel: float,
    model_m2_fiyat: float,
    emsal_agirlik: float = 0.5,
) -> float:
    """
    İki bağımsız tahmini (yarıçap-emsal ortalaması ve ML modeli) ağırlıklı
    ortalar. degerleme.py'deki mevcut ağırlıklı-ortalama desenini izler.

    emsal_agirlik=0.5 -> ikisine eşit güven. Yarıçapta az emsal varsa
    (örn. <5 nokta) emsal_agirlik'i düşürüp modele daha çok güvenmek,
    çoksa (örn. >30 nokta) emsal_agirlik'i yükseltmek mantıklı olabilir —
    çünkü emsal az olduğunda o küçük örneklemin ortalaması gürültülüdür.
    """
    return emsal_agirlik * emsal_ortalama_m2_fiyat_guncel + (1 - emsal_agirlik) * model_m2_fiyat