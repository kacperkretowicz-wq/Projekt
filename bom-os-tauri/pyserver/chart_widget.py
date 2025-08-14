from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtCharts import (QChart, QChartView, QBarSeries, QBarSet, 
                               QValueAxis, QBarCategoryAxis, QLineSeries, QDateTimeAxis)
from PySide6.QtGui import QPainter, QColor, QFont
from PySide6.QtCore import Qt

class ChartWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.chart = QChart()
        self.chart_view = QChartView(self.chart)
        self.chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)

        # --- Chart Styling ---
        self.chart.setBackgroundBrush(QColor("#0A2239"))
        self.chart.setTitleFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        self.chart.setTitleBrush(QColor("#FFFFFF"))
        
        # --- Legend Styling ---
        legend = self.chart.legend()
        legend.setAlignment(Qt.AlignmentFlag.AlignBottom)
        legend.setLabelColor(QColor("#FFFFFF"))
        legend.setFont(QFont("Segoe UI", 10))
        
        layout = QVBoxLayout()
        layout.addWidget(self.chart_view)
        self.setLayout(layout)

    def plot_alert_distribution(self, df):
        self.chart.removeAllSeries()
        self.chart.setTitle("Rozkład Alertów")

        # --- Data Preparation ---
        rule_counts = df['alert'].value_counts()
        categories = rule_counts.index.tolist()
        
        bar_set_rule = QBarSet("Regułowy")
        bar_set_rule.setColor(QColor("#00E5FF")) # Cyan
        bar_set_rule.append(rule_counts.tolist())

        series = QBarSeries()
        series.append(bar_set_rule)

        if 'ai_alert' in df.columns:
            ai_counts = df['ai_alert'].value_counts().reindex(categories).fillna(0)
            bar_set_ai = QBarSet("AI")
            bar_set_ai.setColor(QColor("#FF00E5")) # Magenta
            bar_set_ai.append(ai_counts.tolist())
            series.append(bar_set_ai)

        self.chart.addSeries(series)

        # --- Axes ---
        axis_x = QBarCategoryAxis()
        axis_x.append(categories)
        axis_x.setLabelsColor(QColor("white"))
        self.chart.setAxisX(axis_x, series)

        axis_y = QValueAxis()
        axis_y.setLabelFormat("%i")
        axis_y.setLabelsColor(QColor("white"))
        self.chart.setAxisY(axis_y, series)

    def plot_feature_importances(self, importances_df):
        self.chart.removeAllSeries()
        self.chart.setTitle("Ważność Cech Modelu AI")

        importances_df.sort_values('importance', ascending=False, inplace=True)
        
        bar_set = QBarSet("Ważność")
        bar_set.setColor(QColor("#FF00E5")) # Magenta
        bar_set.append(importances_df['importance'].tolist())

        series = QBarSeries()
        series.append(bar_set)
        self.chart.addSeries(series)

        # --- Axes ---
        axis_x = QBarCategoryAxis()
        axis_x.append(importances_df['feature'].tolist())
        axis_x.setLabelsColor(QColor("white"))
        self.chart.setAxisX(axis_x, series)

        axis_y = QValueAxis()
        axis_y.setLabelsColor(QColor("white"))
        self.chart.setAxisY(axis_y, series)
        
    def clear_chart(self):
        self.chart.removeAllSeries()
        self.chart.setTitle("")

    def plot_forecast(self, forecast_df, stockout_date):
        self.chart.removeAllSeries()
        self.chart.setTitle("Prognoza Stanu Magazynowego")

        line_series = QLineSeries()
        line_series.setName("Przewidywany Stan")
        line_series.setColor(QColor("#00E5FF"))

        for timestamp, value in forecast_df['forecasted_stock'].items():
            line_series.append(timestamp.timestamp() * 1000, value) # QtCharts uses ms timestamps

        self.chart.addSeries(line_series)

        # --- Axes ---
        axis_x = QDateTimeAxis()
        axis_x.setFormat("MMM yyyy")
        axis_x.setLabelsColor(QColor("white"))
        axis_x.setTitleText("Data")
        axis_x.setTitleBrush(QColor("white"))
        self.chart.setAxisX(axis_x, line_series)

        axis_y = QValueAxis()
        axis_y.setLabelFormat("%i")
        axis_y.setLabelsColor(QColor("white"))
        axis_y.setTitleText("Przewidywany Stan")
        axis_y.setTitleBrush(QColor("white"))
        self.chart.setAxisY(axis_y, line_series)

        if stockout_date:
            self.chart.setTitle(f"Prognoza Stanu Magazynowego (Brak: {stockout_date.strftime('%Y-%m-%d')})")
