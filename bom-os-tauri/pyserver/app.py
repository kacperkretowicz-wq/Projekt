
import os
import json
import traceback
from typing import Optional, Tuple, Dict, Any

from flask import Flask, request, jsonify
import pandas as pd

# --- Lazy/forgiving imports of your modules ---
try:
    import ai_logic  # your module
except Exception as e:
    ai_logic = None

try:
    import forecasting_logic  # your module
except Exception as e:
    forecasting_logic = None

try:
    from common import data_processing  # your module
except Exception as e:
    data_processing = None

app = Flask(__name__)

MODEL_STATE: Dict[str, Any] = {
    "df": pd.DataFrame(),
    "monthly_sales_df": pd.DataFrame(),
    "ai_model": None,
    "ai_encoder": None,
    "ai_importances": None,
}

@app.get("/health")
def health():
    return {"status": "ok"}

def error_json(msg: str, code: int = 400):
    return jsonify({"error": msg}), code

@app.post("/process")
def process():
    try:
        payload = request.get_json(silent=True) or {}
        stany = payload.get("stany")
        bomy = payload.get("bomy")
        minimum = payload.get("minimum")
        sprzedaz = payload.get("sprzedaz")

        if data_processing:
            df, monthly = data_processing.process_data_files(
                stany=stany, bomy=bomy, minimum=minimum, sprzedaz=sprzedaz
            )
        else:
            # fallback – sample frame
            df = pd.DataFrame([
                {"indeks": "SKU-1", "stan": 42, "nazwa": "Przykład"},
                {"indeks": "SKU-2", "stan": 5, "nazwa": "Przykład 2"}
            ])
            monthly = pd.DataFrame({
                "indeks": ["SKU-1"]*6,
                "date": pd.date_range("2024-01-01", periods=6, freq="MS"),
                "sales": [10, 12, 11, 15, 14, 18]
            })

        MODEL_STATE["df"] = df
        MODEL_STATE["monthly_sales_df"] = monthly

        rows = df.to_dict(orient="records")
        return jsonify({"rows": rows})
    except Exception as e:
        return error_json(f"process failed: {e}\n{traceback.format_exc()}", 500)

@app.post("/train")
def train():
    try:
        df = MODEL_STATE.get("df", pd.DataFrame())
        if df.empty:
            return error_json("Brak danych – wywołaj /process najpierw.", 400)

        if ai_logic:
            model_data = ai_logic.train_and_save_model(df, "feedback_log.csv")
            MODEL_STATE["ai_model"] = model_data.get("model")
            MODEL_STATE["ai_encoder"] = model_data.get("encoder")
            MODEL_STATE["ai_importances"] = model_data.get("importances")
            imp = MODEL_STATE["ai_importances"]
            if hasattr(imp, "to_dict"):
                imp = imp.to_dict(orient="records")
            return jsonify({"message": "model trained", "importances": imp})
        else:
            # fallback
            MODEL_STATE["ai_model"] = "stub"
            MODEL_STATE["ai_encoder"] = "stub"
            MODEL_STATE["ai_importances"] = pd.DataFrame([{"feature":"stan","importance":1.0}])
            return jsonify({"message": "stub model trained", "importances": [{"feature":"stan","importance":1.0}]})

    except Exception as e:
        return error_json(f"train failed: {e}\n{traceback.format_exc()}", 500)

@app.post("/predict")
def predict():
    try:
        payload = request.get_json(silent=True) or {}
        rows = payload.get("rows")
        if rows is not None:
            df = pd.DataFrame(rows)
            MODEL_STATE["df"] = df
        else:
            df = MODEL_STATE.get("df", pd.DataFrame())

        if df.empty:
            return error_json("Brak danych do predykcji.", 400)

        if ai_logic and MODEL_STATE["ai_model"] is not None and MODEL_STATE["ai_encoder"] is not None:
            preds = ai_logic.predict_with_model(MODEL_STATE["ai_model"], MODEL_STATE["ai_encoder"], df)
            df = df.copy()
            df["ai_alert"] = preds
            MODEL_STATE["df"] = df
            imp = MODEL_STATE.get("ai_importances")
            if hasattr(imp, "to_dict"):
                imp = imp.to_dict(orient="records")
            return jsonify({"rows": df.to_dict(orient="records"), "importances": imp})
        else:
            df = df.copy()
            df["ai_alert"] = (df["stan"] <= 5) if "stan" in df.columns else False
            MODEL_STATE["df"] = df
            return jsonify({"rows": df.to_dict(orient="records"), "importances": [{"feature":"stan","importance":1.0}]})

    except Exception as e:
        return error_json(f"predict failed: {e}\n{traceback.format_exc()}", 500)

@app.post("/forecast")
def forecast():
    try:
        payload = request.get_json(silent=True) or {}
        indeks = payload.get("indeks")
        stan = payload.get("stan", 0)
        monthly = MODEL_STATE.get("monthly_sales_df", pd.DataFrame())
        if not indeks:
            return error_json("Wymagany 'indeks'.", 400)

        product_sales = monthly[monthly.get("indeks") == indeks] if not monthly.empty else pd.DataFrame()
        if product_sales.empty:
            # fallback dummy
            dates = pd.date_range("2024-01-01", periods=12, freq="MS")
            sales = pd.Series(range(10, 22))
            product_sales = pd.DataFrame({"date": dates, "sales": sales, "indeks": indeks})

        if forecasting_logic:
            sales_series = product_sales.set_index("date")["sales"]
            model = forecasting_logic.load_forecast_model(indeks) or forecasting_logic.train_and_save_forecast_model(sales_series, indeks)
            forecast_df, stockout_date = forecasting_logic.generate_forecast(model, stan)
            out = {
                "forecast": forecast_df.reset_index().to_dict(orient="records"),
                "stockout_date": str(stockout_date) if stockout_date is not None else None
            }
            return jsonify(out)
        else:
            # simple linear projection
            df = product_sales.sort_values("date").copy()
            df["forecast"] = df["sales"].rolling(3, min_periods=1).mean()
            stockout_date = None
            return jsonify({"forecast": df.to_dict(orient="records"), "stockout_date": stockout_date})

    except Exception as e:
        return error_json(f"forecast failed: {e}\n{traceback.format_exc()}", 500)

@app.post("/export")
def export():
    try:
        payload = request.get_json(silent=True) or {}
        path = payload.get("path", "export.csv")
        df = MODEL_STATE.get("df", pd.DataFrame())
        if df.empty:
            return error_json("Brak danych do eksportu.", 400)
        df.to_csv(path, index=False, encoding="utf-8-sig")
        return jsonify({"message": "saved", "path": os.path.abspath(path)})
    except Exception as e:
        return error_json(f"export failed: {e}\n{traceback.format_exc()}", 500)

if __name__ == "__main__":
    port = int(os.environ.get("FLASK_PORT", "5005"))
    app.run(host="127.0.0.1", port=port, debug=True)
