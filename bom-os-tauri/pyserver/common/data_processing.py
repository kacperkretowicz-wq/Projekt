import pandas as pd
import os
import numpy as np
from rapidfuzz import process, fuzz

def fuzzy_match(new_names, known_names, threshold=80):
    """
    Finds the best match for each name in new_names from a list of known_names.
    """
    mapping = {}
    for name in new_names:
        match = process.extractOne(name, known_names, scorer=fuzz.token_set_ratio)
        if match and match[1] > threshold:
            mapping[name] = match[0]
    return mapping

def process_data_files(stany, bomy_path, minimum_path, sprzedaz_path):
    """
    Loads and processes data from four CSV files to create a unified DataFrame.
    """
    # Define expected columns for empty dataframes
    stany_cols = ["Indeks", "Name", "Ilość na stanie"]
    bomy_cols = ["Indeks", "Nazwa", "Ilość"]
    minimum_cols = ["Indeks", "Minimum"]
    
    # Load dataframes, creating empty ones if files don't exist
    if stany_path and os.path.exists(stany_path):
        stany = pd.read_csv(stany_path)
    else:
        stany = pd.DataFrame(columns=stany_cols)

    if bomy_path and os.path.exists(bomy_path):
        bomy = pd.read_csv(bomy_path)
    else:
        bomy = pd.DataFrame(columns=bomy_cols)

    if minimum_path and os.path.exists(minimum_path):
        minimum = pd.read_csv(minimum_path)
    else:
        minimum = pd.DataFrame(columns=minimum_cols)
    
    if sprzedaz_path and os.path.exists(sprzedaz_path):
        sprzedaz = pd.read_csv(sprzedaz_path)
    else:
        sprzedaz = pd.DataFrame()

    if stany.empty:
        # Return empty dataframes if there's no base data
        return pd.DataFrame(), pd.DataFrame()

    # 1. Process Bomy
    if not bomy.empty:
        bomy_agg = bomy.groupby("Indeks")["Ilość"].sum().reset_index()
        bomy_agg = bomy_agg.rename(columns={"Ilość": "ilośćBom"})
    else:
        bomy_agg = pd.DataFrame(columns=["Indeks", "ilośćBom"])

    # 2. Process Sprzedaz
    monthly_sales_df = pd.DataFrame()
    if not sprzedaz.empty and 'GSM1' in sprzedaz.columns:
        # Assume columns are named like 'Jan-23', 'Feb-23' etc.
        # For this example, let's assume columns 3 to 14 are the 12 months of a year
        sales_cols = sprzedaz.columns[3:15] 
        
        # Calculate total sales for the summary table
        sprzedaz_total = sprzedaz.copy()
        sprzedaz_total["sprzedaż"] = sprzedaz_total[sales_cols].sum(axis=1)
        sprzedaz_total = sprzedaz_total.rename(columns={"GSM1": "Indeks"})
        sprzedaz_agg = sprzedaz_total[["Indeks", "sprzedaż"]]
        
        # Reshape data for time series forecasting
        id_vars = ['GSM1', 'Name']
        sprzedaz_long = pd.melt(sprzedaz, id_vars=id_vars, value_vars=sales_cols, var_name='month', value_name='sales')
        sprzedaz_long.rename(columns={'GSM1': 'indeks'}, inplace=True)
        
        try:
            sprzedaz_long['date'] = pd.to_datetime(sprzedaz_long['month'], format='%b-%y')
        except ValueError:
            sprzedaz_long['date'] = pd.to_datetime(sprzedaz_long['month'], errors='coerce')
            if sprzedaz_long['date'].isnull().any():
                num_months = len(sales_cols)
                dates = pd.date_range(start='2023-01-01', periods=num_months, freq='MS')
                date_map = {col: date for col, date in zip(sales_cols, dates)}
                sprzedaz_long['date'] = sprzedaz_long['month'].map(date_map)

        monthly_sales_df = sprzedaz_long[['indeks', 'date', 'sales']].dropna(subset=['date'])

    else:
        sprzedaz_agg = pd.DataFrame(columns=["Indeks", "sprzedaż"])

    # 3. Fuzzy Match
    stany_names = stany["Name"].unique()
    bom_names = bomy["Nazwa"].unique() if not bomy.empty else []
    mapping = fuzzy_match(bom_names, stany_names)

    # 4. Merge DataFrames
    df = pd.merge(stany, bomy_agg, on="Indeks", how="left")
    if not minimum.empty:
        df = pd.merge(df, minimum, on="Indeks", how="left")
    if not sprzedaz_agg.empty:
        df = pd.merge(df, sprzedaz_agg, on="Indeks", how="left")

    df["ilośćBom"] = df["ilośćBom"].fillna(0).astype(int)
    if "Minimum" in df.columns:
        df["Minimum"] = df["Minimum"].fillna(0).astype(int)
    else:
        df["Minimum"] = 0
    if "sprzedaż" in df.columns:
        df["sprzedaż"] = df["sprzedaż"].fillna(0).astype(int)
    else:
        df["sprzedaż"] = 0

    # 5. Calculate Alert Status
    conditions = [
        df["Ilość na stanie"] == 0,
        df["Ilość na stanie"] < df["Minimum"],
    ]
    choices = [
        "Brak produktu – pilnie BOM!",
        "Stan poniżej minimum – zleć BOM!",
    ]
    df["alert"] = np.select(conditions, choices, default="OK")

    # 6. Add other columns
    df["bom"] = df["ilośćBom"].apply(lambda x: "TAK" if x > 0 else "NIE")
    df["match"] = df["Name"].map(mapping).fillna("-")

    # 7. Final selection and renaming
    df = df.rename(columns={
        "Indeks": "indeks",
        "Name": "nazwa",
        "Ilość na stanie": "stan",
        "Minimum": "minimum"
    })
    
    final_cols = ["indeks", "nazwa", "stan", "minimum", "bom", "ilośćBom", "sprzedaż", "alert", "match"]
    for col in final_cols:
        if col not in df.columns:
            df[col] = "-" if col in ["indeks", "nazwa", "bom", "alert", "match"] else 0
            
    df = df[final_cols]

    return df, monthly_sales_df
