from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                               QPushButton, QComboBox, QDialogButtonBox, QWidget)
from PySide6.QtCore import Qt

class FeedbackDialog(QDialog):
    def __init__(self, row_data, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Korekta Predykcji AI")
        self.row_data = row_data
        self.corrected_label = None

        main_layout = QVBoxLayout(self)

        # Display row data in a readable format
        data_label = QLabel("<b>Analizowany wiersz:</b>")
        main_layout.addWidget(data_label)
        
        details_text = ""
        for col, val in row_data.items():
            details_text += f"<b>{col}:</b> {val}<br>"
        details_widget = QLabel(details_text)
        details_widget.setTextFormat(Qt.TextFormat.RichText)
        details_widget.setStyleSheet("background-color: #0A2239; border-radius: 5px; padding: 10px;")
        main_layout.addWidget(details_widget)

        main_layout.addSpacing(20)

        # Ask for correctness
        question_label = QLabel(f"Czy predykcja AI: '<b>{row_data.get('ai_alert', 'N/A')}</b>' jest poprawna?")
        question_label.setTextFormat(Qt.TextFormat.RichText)
        main_layout.addWidget(question_label)

        # Correction widget (initially hidden)
        self.correction_widget = QWidget()
        correction_layout = QHBoxLayout(self.correction_widget)
        correction_layout.setContentsMargins(0, 0, 0, 0)
        correction_layout.addWidget(QLabel("Podaj poprawny alert:"))
        self.correction_combo = QComboBox()
        self.correction_combo.addItems(["OK", "Stan poniżej minimum – zleć BOM!", "Brak produktu – pilnie BOM!"])
        # Set current value to something different from the prediction
        if row_data.get('ai_alert') == "OK":
            self.correction_combo.setCurrentIndex(1)
        else:
            self.correction_combo.setCurrentIndex(0)
        correction_layout.addWidget(self.correction_combo)
        self.correction_widget.setVisible(False)
        main_layout.addWidget(self.correction_widget)

        # Dialog buttons
        self.button_box = QDialogButtonBox()
        self.yes_button = self.button_box.addButton("Tak, poprawna", QDialogButtonBox.ButtonRole.YesRole)
        self.no_button = self.button_box.addButton("Nie, błędna", QDialogButtonBox.ButtonRole.NoRole)
        main_layout.addWidget(self.button_box)

        self.yes_button.clicked.connect(self.accept)
        self.no_button.clicked.connect(self.prompt_for_correction)

    def prompt_for_correction(self):
        self.correction_widget.setVisible(True)
        self.button_box.clear()
        self.submit_button = self.button_box.addButton("Zatwierdź korektę", QDialogButtonBox.ButtonRole.AcceptRole)
        self.cancel_button = self.button_box.addButton("Anuluj", QDialogButtonBox.ButtonRole.RejectRole)
        self.submit_button.clicked.connect(self.submit_correction)
        self.cancel_button.clicked.connect(self.reject)
        
    def submit_correction(self):
        self.corrected_label = self.correction_combo.currentText()
        self.accept()

    def get_correction(self):
        return self.corrected_label
