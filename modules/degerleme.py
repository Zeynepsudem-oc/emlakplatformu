# modules/degerleme.py
def degerleme_yap(eski_deger, eski_tarih, konum_bilgisi, endeks_verileri, model):
    tufe_deger = tufe_ile_guncelle(eski_deger, eski_tarih, endeks_verileri['tufe'])
    dolar_deger = dolar_ile_guncelle(eski_deger, eski_tarih, endeks_verileri['kur'], endeks_verileri['cpi'])
    endeks_ortalama = (tufe_deger + dolar_deger) / 2

    piyasa_deger = piyasa_tahmini(model, **konum_bilgisi)

    # Ağırlıklı ortalama (başlangıçta %50-%50, sonra ayarlanabilir)
    nihai_deger = 0.5 * endeks_ortalama + 0.5 * piyasa_deger

    return {
        "tufe_bazli": tufe_deger,
        "dolar_bazli": dolar_deger,
        "endeks_ortalama": endeks_ortalama,
        "piyasa_bazli": piyasa_deger,
        "nihai_deger": nihai_deger
    }
