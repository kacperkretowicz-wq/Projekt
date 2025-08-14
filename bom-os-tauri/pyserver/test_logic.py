import unittest
import pandas as pd
import os
import shutil

# Dodaj ścieżkę do modułów, aby testy mogły je znaleźć
import sys
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

# Importuj moduły do testowania
from common import data_processing
from pyserver import ai_logic

class TestDataProcessing(unittest.TestCase):

    def test_process_data_files_robustness(self):
        """Testuje, czy przetwarzanie danych jest odporne na brakujące pliki."""
        # Scenariusz: podano tylko plik stanów, reszta to `None`
        stany_df = pd.DataFrame({
            "Indeks": ["A1", "B2"],
            "Name": ["Produkt A", "Produkt B"],
            "Ilość na stanie": [10, 5],
        })
        # Zapisz tymczasowy plik CSV
        stany_path = "test_stany.csv"
        stany_df.to_csv(stany_path, index=False)
        
        df, monthly_sales_df = data_processing.process_data_files(
            stany_path=stany_path,
            bomy_path=None,
            minimum_path=None,
            sprzedaz_path=None
        )
        
        # Sprawdzenia
        self.assertFalse(df.empty, "Ramka danych nie powinna być pusta")
        self.assertTrue(monthly_sales_df.empty, "Ramka sprzedaży powinna być pusta")
        self.assertEqual(len(df), 2)
        self.assertIn("alert", df.columns, "Brak kolumny 'alert'")
        self.assertEqual(df.iloc[0]["alert"], "OK")

        # Posprzątaj
        os.remove(stany_path)

    def test_dynamic_sales_column_detection(self):
        """Testuje, czy funkcja poprawnie wykrywa kolumny sprzedaży."""
        stany_df = pd.DataFrame({"Indeks": ["A1"], "Name": ["Produkt A"], "Ilość na stanie": [100]})
        sprzedaz_df = pd.DataFrame({
            "ID": [1],
            "GSM1": ["A1"],
            "Name": ["Produkt A"],
            "Cokolwiek": ["inna dana"],
            "Sty-23": [10],
            "Lut-23": [15],
            "Mar-24": [20] # Inny rok
        })
        stany_path = "test_stany.csv"
        sprzedaz_path = "test_sprzedaz.csv"
        stany_df.to_csv(stany_path, index=False)
        sprzedaz_df.to_csv(sprzedaz_path, index=False)

        df, monthly_sales_df = data_processing.process_data_files(
            stany_path=stany_path, bomy_path=None, minimum_path=None, sprzedaz_path=sprzedaz_path
        )
        
        self.assertEqual(df.iloc[0]["sprzedaż"], 45) # 10 + 15 + 20
        self.assertEqual(len(monthly_sales_df), 3) # Powinny być 3 wiersze w danych miesięcznych

        os.remove(stany_path)
        os.remove(sprzedaz_path)


class TestAILogic(unittest.TestCase):
    
    def setUp(self):
        """Przygotowanie przed każdym testem"""
        self.model_dir = ai_logic.MODEL_DIR
        if os.path.exists(self.model_dir):
            shutil.rmtree(self.model_dir) # Wyczyść stare modele

    def tearDown(self):
        """Sprzątanie po każdym teście"""
        if os.path.exists(self.model_dir):
            shutil.rmtree(self.model_dir)

    def test_train_and_predict(self):
        """Testuje, czy model AI może być trenowany i używany do predykcji."""
        df = pd.DataFrame({
            "indeks": [f"SKU-{i}" for i in range(20)],
            "stan": [10, 2, 30, 5, 8, 1, 50, 6, 9, 4] * 2,
            "minimum": [5, 3, 20, 10, 10, 2, 40, 5, 8, 5] * 2,
            "ilośćBom": [1, 0, 1, 1, 0, 1, 1, 0, 0, 1] * 2,
            "sprzedaż": [100, 20, 50, 15, 30, 5, 120, 25, 40, 10] * 2,
            "alert": ["OK", "Stan poniżej minimum – zleć BOM!", "OK", "Brak produktu – pilnie BOM!","OK"] * 4
        })
        
        # Trenowanie
        model_data = ai_logic.train_and_save_model(df, feedback_log_path="non_existent_file.csv")
        self.assertIsNotNone(model_data, "Trenowanie nie zwróciło danych modelu")
        
        # Wczytywanie
        loaded_model_data = ai_logic.load_model()
        self.assertIsNotNone(loaded_model_data, "Nie udało się wczytać modelu z pliku")
        
        # Predykcja
        model = loaded_model_data.get("model")
        encoder = loaded_model_data.get("encoder")
        predictions = ai_logic.predict_with_model(model, encoder, df)
        self.assertEqual(len(predictions), len(df), "Liczba predykcji nie zgadza się z liczbą wierszy")

if __name__ == '__main__':
    unittest.main()
