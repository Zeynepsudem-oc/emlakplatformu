# modules/piyasa_modeli.py
from sklearn.ensemble import RandomForestRegressor

def model_egit(df):
    X = df[['enlem', 'boylam', 'kat', 'm2', 'bina_yasi', 'oda_sayisi']]
    y = df['guncel_m2_fiyat']
    model = RandomForestRegressor(n_estimators=200, random_state=42)
    model.fit(X, y)
    return model

def piyasa_tahmini(model, enlem, boylam, kat, m2, bina_yasi, oda_sayisi):
    tahmin_m2_fiyat = model.predict([[enlem, boylam, kat, m2, bina_yasi, oda_sayisi]])[0]
    return tahmin_m2_fiyat * m2
