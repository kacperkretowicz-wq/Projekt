import sys
import os
from typing import Optional, Tuple

import pandas as pd
from PySide6.QtCore import Qt, QModelIndex, QThreadPool
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QPushButton,
    QFileDialog,
    QTableView,
    QMessageBox,
    QHBoxLayout,
    QSplitter,
    QStatusBar,
)

# --- Importy: próbuj jako pakiet i jako moduły lokalne (uruchamiane bez -m) ---
try:  # uruchomione jako pakiet: python -m twojpakiet.main
    from . import ai_logic
    from .pandas_model import PandasModel
    from .chart_widget import ChartWidget
    from .feedback_dialog import FeedbackDialog
    from . import forecasting_logic
    from .worker import Worker
    from .common import data_processing
except Exception:  # uruchomione lokalnie: python main.py
    import ai_logic  # type: ignore
    from pandas_model import PandasModel  # type: ignore
    from chart_widget import ChartWidget  # type: ignore
    from feedback_dialog import FeedbackDialog  # type: ignore
    import forecasting_logic  # type: ignore
    from worker import Worker  # type: ignore
    from common import data_processing  # type: ignore

FEEDBACK_LOG_PATH = "feedback_log.csv"
REQUIRED_COLS = {"indeks", "stan"}


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()

        self.setWindowTitle("BOM OS - AI Dashboard")
        self.setGeometry(100, 100, 1600, 900)
        self.threadpool = QThreadPool()
        print(f"Multithreading with maximum {self.threadpool.maxThreadCount()} threads")

        # --- AI Model & Data Storage ---
        self.df: pd.DataFrame = pd.DataFrame()
        self.monthly_sales_df: pd.DataFrame = pd.DataFrame()
        self.ai_model = None
        self.ai_encoder = None
        self.ai_importances: Optional[pd.DataFrame] = None

        try:
            model_data = ai_logic.load_model()
        except Exception as e:
            print(f"Warning: could not load AI model: {e}")
            model_data = None

        if model_data:
            self.ai_model = model_data.get("model")
            self.ai_encoder = model_data.get("encoder")
            self.ai_importances = model_data.get("importances")

        # --- Layouts ---
        main_layout = QHBoxLayout()
        left_panel_layout = QVBoxLayout()
        right_panel = QSplitter(Qt.Orientation.Vertical)

        # --- Left Panel (Controls) ---
        left_panel = QWidget()
        left_panel.setLayout(left_panel_layout)
        left_panel.setFixedWidth(300)
        left_panel.setObjectName("glass-panel")  # stabilniejsze niż dynamiczna klasa

        self.btn_load_stany = QPushButton("1. Wczytaj Plik Stanów")
        self.btn_load_bomy = QPushButton("2. Wczytaj Plik BOM")
        self.btn_load_minimum = QPushButton("3. Wczytaj Plik Minimum")
        self.btn_load_sprzedaz = QPushButton("4. Wczytaj Plik Sprzedaży")
        self.btn_train_ai = QPushButton("Trenuj Model AI")
        self.btn_update_chart = QPushButton("Generuj Wykres")
        self.btn_export_data = QPushButton("Eksportuj do CSV")
        self.btn_forecast = QPushButton("Generuj Prognozę")

        self.control_buttons = [
            self.btn_load_stany,
            self.btn_load_bomy,
            self.btn_load_minimum,
            self.btn_load_sprzedaz,
            self.btn_train_ai,
            self.btn_update_chart,
            self.btn_export_data,
            self.btn_forecast,
        ]

        self.btn_load_stany.clicked.connect(lambda: self.load_file("stany"))
        self.btn_load_bomy.clicked.connect(lambda: self.load_file("bomy"))
        self.btn_load_minimum.clicked.connect(lambda: self.load_file("minimum"))
        self.btn_load_sprzedaz.clicked.connect(lambda: self.load_file("sprzedaz"))
        self.btn_train_ai.clicked.connect(self.train_ai_model)
        self.btn_update_chart.clicked.connect(self.update_chart)
        self.btn_export_data.clicked.connect(self.export_data)
        self.btn_forecast.clicked.connect(self.run_forecasting_worker)

        for w in [
            self.btn_load_stany,
            self.btn_load_bomy,
            self.btn_load_minimum,
            self.btn_load_sprzedaz,
        ]:
            left_panel_layout.addWidget(w)

        left_panel_layout.addSpacing(30)
        for w in [self.btn_train_ai, self.btn_update_chart, self.btn_forecast]:
            left_panel_layout.addWidget(w)
        left_panel_layout.addSpacing(30)
        left_panel_layout.addWidget(self.btn_export_data)
        left_panel_layout.addStretch()

        # --- Right Panel (Data Display) ---
        self.table_view = QTableView()
        self.table_view.setSortingEnabled(True)
        self.table_view.doubleClicked.connect(self.open_feedback_dialog)

        self.chart_widget = ChartWidget()

        right_panel.addWidget(self.table_view)
        right_panel.addWidget(self.chart_widget)
        right_panel.setSizes([600, 300])
        right_panel.setObjectName("glass-panel")

        # --- Main Layout Assembly ---
        main_layout.addWidget(left_panel)
        main_layout.addWidget(right_panel)

        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)
        self.setStatusBar(QStatusBar())

        # -- (Opcjonalnie) przezroczyste tło – bywa problematyczne na Windows
        try:
            self.setAttribute(Qt.WA_TranslucentBackground)
        except Exception:
            pass

        # --- File Paths Storage ---
        self.file_paths = {"stany": None, "bomy": None, "minimum": None, "sprzedaz": None}

    # -------------------- Helpers --------------------
    def set_controls_enabled(self, enabled: bool) -> None:
        for button in self.control_buttons:
            button.setEnabled(enabled)

    def validate_df_columns(self, df: pd.DataFrame) -> bool:
        missing = REQUIRED_COLS - set(df.columns)
        if missing:
            QMessageBox.critical(
                self,
                "Brak kolumn",
                f"W danych brakuje kolumn: {', '.join(sorted(missing))}. Upewnij się, że przetwarzanie tworzy kolumny 'indeks' i 'stan'.",
            )
            return False
        return True

    # -------------------- File loading & processing --------------------
    def load_file(self, file_type: str) -> None:
        path, _ = QFileDialog.getOpenFileName(self, f"Wybierz plik - {file_type}", "", "CSV Files (*.csv)")
        if path:
            self.file_paths[file_type] = path
            print(f"Załadowano plik '{file_type}': {path}")
            self.run_data_processing_worker()

    def run_data_processing_worker(self) -> None:
        # Przynajmniej 'stany' są wymagane do sensownego połączenia
        if not self.file_paths["stany"]:
            return

        self.set_controls_enabled(False)
        self.statusBar().showMessage("Przetwarzanie danych...")

        worker = Worker(data_processing.process_data_files, **self.file_paths)
        worker.signals.result.connect(self.on_processing_result)
        worker.signals.finished.connect(self.on_task_finished)
        worker.signals.error.connect(self.on_task_error)
        self.threadpool.start(worker)

    def on_processing_result(self, result: Tuple[pd.DataFrame, pd.DataFrame]) -> None:
        try:
            self.df, self.monthly_sales_df = result
        except Exception:
            self.df, self.monthly_sales_df = pd.DataFrame(), pd.DataFrame()

        if self.df is not None and not self.df.empty:
            if not self.validate_df_columns(self.df):
                # pokaż pustą tabelę, aby uniknąć błędów na dalszych etapach
                self.table_view.setModel(PandasModel(pd.DataFrame()))
                return

            # Predykcja alertów, jeśli model jest dostępny
            try:
                if self.ai_model is not None and self.ai_encoder is not None:
                    predictions = ai_logic.predict_with_model(self.ai_model, self.ai_encoder, self.df)
                    self.df["ai_alert"] = predictions
            except Exception as e:
                print(f"Prediction failed: {e}")

            model = PandasModel(self.df)
            self.table_view.setModel(model)
            print(f"Wyświetlono {len(self.df)} wierszy danych.")
        else:
            self.table_view.setModel(PandasModel(pd.DataFrame()))
            print("Brak danych do wyświetlenia.")

    # -------------------- AI Training & Charts --------------------
    def train_ai_model(self) -> None:
        if self.df.empty:
            QMessageBox.warning(self, "Brak Danych", "Najpierw wczytaj i przetwórz dane.")
            return

        self.set_controls_enabled(False)
        self.statusBar().showMessage("Trenowanie modelu AI...")

        worker = Worker(ai_logic.train_and_save_model, self.df, FEEDBACK_LOG_PATH)
        worker.signals.result.connect(self.on_training_result)
        worker.signals.finished.connect(self.on_task_finished)
        worker.signals.error.connect(self.on_task_error)
        self.threadpool.start(worker)

    def on_training_result(self, model_data):
        if model_data:
            self.ai_model = model_data.get("model")
            self.ai_encoder = model_data.get("encoder")
            self.ai_importances = model_data.get("importances")
            QMessageBox.information(self, "Sukces", "Model AI został pomyślnie douczony i zapisany.")
            self.update_chart()  # Update chart with new importances
            self.run_data_processing_worker()  # Refresh data to show new predictions
        else:
            QMessageBox.critical(self, "Błąd", "Nie udało się wytrenować modelu.")

    def update_chart(self) -> None:
        try:
            if self.ai_importances is not None and getattr(self.ai_importances, "empty", False) is False:
                self.chart_widget.plot_feature_importances(self.ai_importances)
                print("Wykres ważności cech został zaktualizowany.")
            elif not self.df.empty:
                self.chart_widget.plot_alert_distribution(self.df)
                print("Wykres rozkładu alertów został zaktualizowany.")
            else:
                QMessageBox.warning(self, "Brak Danych", "Najpierw wczytaj dane, aby wygenerować wykres.")
        except Exception as e:
            QMessageBox.critical(self, "Błąd Wykresu", f"Nie udało się narysować wykresu: {e}")

    # -------------------- Forecasting --------------------
    def run_forecasting_worker(self) -> None:
        sel_model = self.table_view.selectionModel()
        if sel_model is None:
            QMessageBox.warning(self, "Brak Danych", "Najpierw wczytaj dane i wybierz wiersz.")
            return

        selected_indexes = sel_model.selectedRows()
        if not selected_indexes:
            QMessageBox.warning(self, "Brak Zaznaczenia", "Proszę zaznaczyć wiersz w tabeli, aby wygenerować prognozę.")
            return

        row = selected_indexes[0].row()
        try:
            product_id = self.df.iloc[row]["indeks"]
            current_stock = self.df.iloc[row]["stan"]
        except Exception:
            QMessageBox.critical(self, "Błąd", "Zaznaczony wiersz nie posiada kolumn 'indeks' oraz 'stan'.")
            return

        product_sales = self.monthly_sales_df[self.monthly_sales_df.get("indeks") == product_id]
        if product_sales is None or product_sales.empty:
            QMessageBox.warning(
                self,
                "Brak Danych",
                f"Brak danych sprzedażowych dla produktu {product_id}, aby stworzyć prognozę.",
            )
            return

        try:
            sales_series = product_sales.set_index("date")["sales"]
        except Exception:
            QMessageBox.critical(self, "Błąd", "Dane sprzedaży muszą zawierać kolumny 'date' oraz 'sales'.")
            return

        self.set_controls_enabled(False)
        self.statusBar().showMessage(f"Generowanie prognozy dla produktu {product_id}...")

        def forecast_task(sales_data, prod_id, stock):
            model = forecasting_logic.load_forecast_model(prod_id)
            if not model:
                model = forecasting_logic.train_and_save_forecast_model(sales_data, prod_id)

            if model:
                return forecasting_logic.generate_forecast(model, stock)
            return None, None

        worker = Worker(forecast_task, sales_series, product_id, current_stock)
        worker.signals.result.connect(self.on_forecast_result)
        worker.signals.finished.connect(self.on_task_finished)
        worker.signals.error.connect(self.on_task_error)
        self.threadpool.start(worker)

    def on_forecast_result(self, result) -> None:
        forecast_df, stockout_date = result if isinstance(result, tuple) else (None, None)
        if forecast_df is not None:
            # toleruj różne typy daty (pd.Timestamp / np.datetime64 / str / None)
            try:
                from pandas import to_datetime

                sdate_str = (
                    to_datetime(stockout_date).strftime("%Y-%m-%d") if stockout_date is not None else "Poza horyzontem prognozy"
                )
            except Exception:
                sdate_str = str(stockout_date) if stockout_date is not None else "Poza horyzontem prognozy"

            try:
                self.chart_widget.plot_forecast(forecast_df, stockout_date)
            except Exception as e:
                print(f"Plot forecast failed: {e}")

            QMessageBox.information(self, "Prognoza Gotowa", f"Prognoza została wygenerowana.\nPrzewidywany brak zapasów: {sdate_str}")
        else:
            QMessageBox.critical(self, "Błąd Prognozy", "Nie udało się wygenerować prognozy.")

    # -------------------- Export & Feedback --------------------
    def export_data(self) -> None:
        if self.df.empty:
            QMessageBox.warning(self, "Brak Danych", "Brak danych do wyeksportowania. Najpierw wczytaj i przetwórz pliki.")
            return

        path, _ = QFileDialog.getSaveFileName(self, "Eksportuj do CSV", "", "CSV Files (*.csv)")

        if path:
            try:
                self.df.to_csv(path, index=False, encoding="utf-8-sig")
                QMessageBox.information(self, "Sukces", f"Dane zostały pomyślnie wyeksportowane do:\n{path}")
            except Exception as e:
                QMessageBox.critical(self, "Błąd Eksportu", f"Nie udało się zapisać pliku:\n{e}")

    def open_feedback_dialog(self, index: QModelIndex) -> None:
        if "ai_alert" not in self.df.columns:
            QMessageBox.information(self, "Informacja", "Kolumna 'ai_alert' nie istnieje. Najpierw wytrenuj model i dokonaj predykcji.")
            return

        row = index.row()
        try:
            row_data = self.df.iloc[row].to_dict()
        except Exception:
            QMessageBox.critical(self, "Błąd", "Nie można pobrać danych wiersza.")
            return

        dialog = FeedbackDialog(row_data, self)  # poprawny import klasy
        if dialog.exec():
            corrected_label = dialog.get_correction()
            if corrected_label:
                self.handle_feedback(row, corrected_label)

    def handle_feedback(self, row_index: int, corrected_label) -> None:
        print(f"Otrzymano korektę dla wiersza {row_index}. Nowy alert: {corrected_label}")

        try:
            feedback_df = self.df.iloc[[row_index]].copy()
            feedback_df["alert"] = corrected_label

            # Save feedback to a log file
            mode = "a" if os.path.exists(FEEDBACK_LOG_PATH) else "w"
            header = not os.path.exists(FEEDBACK_LOG_PATH)
            feedback_df.to_csv(FEEDBACK_LOG_PATH, mode=mode, header=header, index=False)

            QMessageBox.information(
                self,
                "Dziękujemy!",
                "Twoja informacja zwrotna została zapisana i zostanie użyta do douczenia modelu.",
            )
        except Exception as e:
            QMessageBox.critical(self, "Błąd Zapisu", f"Nie udało się zapisać feedbacku: {e}")

    # -------------------- Common task hooks --------------------
    def on_task_finished(self) -> None:
        self.set_controls_enabled(True)
        self.statusBar().showMessage("Gotowy.", 2000)  # 2 sekundy

    def on_task_error(self, error_tuple) -> None:
        # spodziewany format: (exc_type, exc_value, traceback_str)
        try:
            _, value, tb = error_tuple
            msg = f"{value}\n\nSzczegóły:\n{tb}" if tb else str(value)
        except Exception:
            msg = str(error_tuple)

        print(error_tuple)
        QMessageBox.critical(self, "Błąd krytyczny", f"Wystąpił błąd podczas operacji w tle:\n{msg}")


def main() -> None:
    app = QApplication(sys.argv)

    # Load and apply stylesheet
    style_path = os.path.join(os.path.dirname(__file__), "style.qss")
    try:
        with open(style_path, "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())
    except FileNotFoundError:
        print(f"Warning: Stylesheet '{style_path}' not found.")

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
