import pandas as pd
import statsmodels.api as sm
import os
import joblib
from datetime import datetime

FORECAST_MODEL_DIR = "saved_forecast_models"
os.makedirs(FORECAST_MODEL_DIR, exist_ok=True)

def get_model_path(product_id):
    return os.path.join(FORECAST_MODEL_DIR, f"forecast_model_{product_id}.joblib")

def train_and_save_forecast_model(sales_data: pd.Series, product_id):
    """
    Trains a SARIMA model and saves it.
    Assumes sales_data is a Series with a monthly DatetimeIndex.
    """
    if len(sales_data) < 24: # Need enough data for seasonality
        print(f"Not enough historical data for product {product_id} to train a forecast model.")
        return None
        
    try:
        # A simple SARIMA model, assuming monthly data with yearly seasonality
        model = sm.tsa.SARIMAX(
            sales_data,
            order=(1, 1, 1),
            seasonal_order=(1, 1, 1, 12),
            enforce_stationarity=False,
            enforce_invertibility=False
        )
        results = model.fit(disp=False)
        
        # Save the fitted model
        joblib.dump(results, get_model_path(product_id))
        print(f"Forecast model for product {product_id} trained and saved.")
        return results
    except Exception as e:
        print(f"Error training forecast model for product {product_id}: {e}")
        return None

def load_forecast_model(product_id):
    """
    Loads a previously trained forecast model for a specific product.
    """
    model_path = get_model_path(product_id)
    if os.path.exists(model_path):
        return joblib.load(model_path)
    return None

def generate_forecast(model, current_stock: int, start_date: datetime, steps=24):
    """
    Generates a forecast of stock levels.
    """
    # Get forecast of sales
    forecast_object = model.get_forecast(steps=steps)
    forecast_sales = forecast_object.predicted_mean
    
    # Create a DataFrame for the forecast
    forecast_df = pd.DataFrame({
        'forecasted_sales': forecast_sales.round().astype(int)
    })
    
    # Calculate cumulative sales and future stock level
    forecast_df['cumulative_sales'] = forecast_df['forecasted_sales'].cumsum()
    forecast_df['forecasted_stock'] = current_stock - forecast_df['cumulative_sales']
    
    # Find estimated stockout date
    stockout_date = None
    stockout_candidates = forecast_df[forecast_df['forecasted_stock'] <= 0]
    if not stockout_candidates.empty:
        stockout_date = stockout_candidates.index[0]
        
    return forecast_df, stockout_date
