import pandas as pd
import os
import re # Import modułu do wyrażeń regularnych
import numpy as np
from rapidfuzz import process, fuzz

def fuzzy_match(new_names, known_names, threshold=80):
    """
    Znajduje najlepsze dopasowanie dla każdej nazwy w new_names z listy known_names.
    """
    mapping = {}
    for name in new_names:
        match = process.extractOne(name, known_names, scorer=fuzz.token_set_ratio)
        if match and match[1] > threshold:
            mapping[name] = match[0]
    return mapping

def process_data_files(stany_path, bomy_path, minimum_path, sprzedaz_path):
    """
    Wczytuje i przetwarza dane z plików CSV, tworząc ujednoliconą ramkę danych.
    """
    # ZMIANA: Usunięto definicje pustych kolumn, logika została ulepszona
    
    # Wczytywanie danych, tworzenie pustych ramek w razie braku plików
    try:
        stany = pd.read_csv(stany_path) if stany_path and os.path.exists(stany_path) else pd.DataFrame()
        bomy = pd.read_csv(bomy_path) if bomy_path and os.path.exists(bomy_path) else pd.DataFrame()
        minimum = pd.read_csv(minimum_path) if minimum_path and os.path.exists(minimum_path) else pd.DataFrame()
        sprzedaz = pd.read_csv(sprzedaz_path) if sprzedaz_path and os.path.exists(sprzedaz_path) else pd.DataFrame()
    except Exception as e:
        print(f"Błąd podczas wczytywania plików CSV: {e}")
        return pd.DataFrame(), pd.DataFrame()


    if stany.empty:
        return pd.DataFrame(), pd.DataFrame()

    # 1. Przetwarzanie BOM-ów
    bomy_agg = pd.DataFrame()
    if not bomy.empty and "Indeks" in bomy.columns and "Ilość" in bomy.columns:
        bomy_agg = bomy.groupby("Indeks")["Ilość"].sum().reset_index()
        bomy_agg = bomy_agg.rename(columns={"Ilość": "ilośćBom"})

    # 2. Przetwarzanie Sprzedaży (UELASTYCZNIONE)
    monthly_sales_df = pd.DataFrame()
    sprzedaz_agg = pd.DataFrame()
    if not sprzedaz.empty and 'GSM1' in sprzedaz.columns:
        # ZMIANA: Dynamiczne wykrywanie kolumn ze sprzedażą za pomocą wyrażenia regularnego
        # Szuka kolumn w formacie 'Xxx-YY', np. 'Sty-23', 'Lut-24'
        sales_cols = [col for col in sprzedaz.columns if re.match(r"^[A-Za-z]{3}-\d{2}$", col)]
        
        if sales_cols:
            print(f"Wykryto kolumny sprzedaży: {sales_cols}")
            # Obliczanie sumy sprzedaży
            sprzedaz_total = sprzedaz.copy()
            sprzedaz_total["sprzedaż"] = sprzedaz_total[sales_cols].sum(axis=1)
            sprzedaz_total = sprzedaz_total.rename(columns={"GSM1": "Indeks"})
            sprzedaz_agg = sprzedaz_total[["Indeks", "sprzedaż"]]
            
            # Przekształcanie danych do prognozowania
            id_vars = ['GSM1', 'Name']
            # Upewnij się, że kolumny do identyfikacji istnieją
            id_vars = [v for v in id_vars if v in sprzedaz.columns] 
            sprzedaz_long = pd.melt(sprzedaz, id_vars=id_vars, value_vars=sales_cols, var_name='month', value_name='sales')
            sprzedaz_long.rename(columns={'GSM1': 'indeks'}, inplace=True)
            
            # Konwersja daty z obsługą błędów
            try:
                sprzedaz_long['date'] = pd.to_datetime(sprzedaz_long['month'], format='%b-%y', errors='coerce')
            except Exception: # Obsługa różnych lokalizacji (np. polskich nazw miesięcy)
                 sprzedaz_long['date'] = pd.to_datetime(sprzedaz_long['month'], errors='coerce')

            monthly_sales_df = sprzedaz_long[['indeks', 'date', 'sales']].dropna(subset=['date'])
        else:
            print("Ostrzeżenie: Nie znaleziono kolumn pasujących do formatu sprzedaży (np. 'Sty-23').")

    # 3. Fuzzy Match
    if "Name" in stany.columns and "Nazwa" in bomy.columns:
        stany_names = stany["Name"].unique()
        bom_names = bomy["Nazwa"].unique()
        mapping = fuzzy_match(bom_names, stany_names)
    else:
        mapping = {}

    # 4. Łączenie Danych
    df = stany.copy()
    if not bomy_agg.empty:
        df = pd.merge(df, bomy_agg, on="Indeks", how="left")
    if not minimum.empty:
        df = pd.merge(df, minimum, on="Indeks", how="left")
    if not sprzedaz_agg.empty:
        df = pd.merge(df, sprzedaz_agg, on="Indeks", how="left")

    # Czyszczenie i przygotowanie finalnych kolumn
    df.rename(columns={
        "Indeks": "indeks",
        "Name": "nazwa",
        "Ilość na stanie": "stan",
        "Minimum": "minimum"
    }, inplace=True)

    # Upewnienie się, że kluczowe kolumny istnieją i mają odpowiedni typ
    final_cols_spec = {
        "indeks": "-", "nazwa": "-", "stan": 0, "minimum": 0, 
        "ilośćBom": 0, "sprzedaż": 0, "bom": "NIE", "alert": "OK", "match": "-"
    }
    for col, default_value in final_cols_spec.items():
        if col not in df.columns:
            df[col] = default_value
        else:
            if pd.api.types.is_numeric_dtype(default_value):
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(type(default_value))

    # Obliczanie statusu alertu
    if "stan" in df.columns and "minimum" in df.columns:
        conditions = [
            df["stan"] <= 0,
            df["stan"] < df["minimum"],
        ]
        choices = [
            "Brak produktu – pilnie BOM!",
            "Stan poniżej minimum – zleć BOM!",
        ]
        df["alert"] = np.select(conditions, choices, default="OK")
    
    if "ilośćBom" in df.columns:
        df["bom"] = df["ilośćBom"].apply(lambda x: "TAK" if x > 0 else "NIE")
        
    if "nazwa" in df.columns and mapping:
         df["match"] = df["nazwa"].map(mapping).fillna("-")

    return df[list(final_cols_spec.keys())], monthly_sales_df
