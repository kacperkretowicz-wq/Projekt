import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import accuracy_score
import joblib
import os

MODEL_DIR = "saved_models"
MODEL_PATH = os.path.join(MODEL_DIR, "ai_model.joblib")
ENCODER_PATH = os.path.join(MODEL_DIR, "label_encoder.joblib")

def ensure_model_dir_exists():
    """Ensures the directory for saving models exists."""
    os.makedirs(MODEL_DIR, exist_ok=True)

def train_and_save_model(df: pd.DataFrame, feedback_log_path: str):
    """
    Trains a RandomForest model on the provided DataFrame, incorporating feedback, and saves it.
    """
    ensure_model_dir_exists()
    
    features = ['stan', 'minimum', 'ilośćBom', 'sprzedaż']
    target = 'alert'

    # --- Incorporate Feedback ---
    training_df = df.copy()
    if os.path.exists(feedback_log_path):
        print(f"Znaleziono plik z informacjami zwrotnymi: {feedback_log_path}")
        feedback_df = pd.read_csv(feedback_log_path)
        
        # Combine original data with feedback, giving precedence to feedback
        # We assume 'indeks' is a unique identifier for a row
        if 'indeks' in training_df.columns and 'indeks' in feedback_df.columns:
            training_df.set_index('indeks', inplace=True)
            feedback_df.set_index('indeks', inplace=True)
            training_df.update(feedback_df)
            training_df.reset_index(inplace=True)
            print(f"Zaktualizowano {len(feedback_df)} wierszy na podstawie informacji zwrotnych.")

    # Ensure target is not all the same class
    if training_df[target].nunique() < 2:
        print("Not enough class diversity to train the model. Need at least 2 different alert types.")
        return None, None

    X = training_df[features]
    y = training_df[target]

    # Encode target labels
    encoder = LabelEncoder()
    y_encoded = encoder.fit_transform(y)

    # Split data for validation
    X_train, X_test, y_train, y_test = train_test_split(X, y_encoded, test_size=0.2, random_state=42, stratify=y_encoded)

    # Train model
    model = RandomForestClassifier(n_estimators=100, random_state=42, class_weight='balanced')
    model.fit(X_train, y_train)

    # Evaluate model
    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    print(f"Model training complete. Accuracy on test set: {accuracy:.2f}")

    # Create a DataFrame for feature importances
    importances_df = pd.DataFrame({
        'feature': X.columns,
        'importance': model.feature_importances_
    }).sort_values('importance', ascending=False)

    print("Feature Importances:")
    print(importances_df)

    # Save model, encoder and importances
    model_data = {
        'model': model,
        'encoder': encoder,
        'importances': importances_df
    }
    joblib.dump(model_data, MODEL_PATH)
    print(f"Model data (model, encoder, importances) saved to {MODEL_PATH}")
    
    return model_data

def load_model():
    """
    Loads the trained model, label encoder, and feature importances from disk.
    """
    if os.path.exists(MODEL_PATH):
        model_data = joblib.load(MODEL_PATH)
        print("AI model data loaded successfully.")
        return model_data
    return None

def predict_with_model(model, encoder, df: pd.DataFrame):
    """
    Makes predictions on new data using the loaded model.
    """
    if model is None or encoder is None:
        return None
        
    features = ['stan', 'minimum', 'ilośćBom', 'sprzedaż']
    X_new = df[features]
    
    predictions_encoded = model.predict(X_new)
    predictions = encoder.inverse_transform(predictions_encoded)
    
    return predictions
