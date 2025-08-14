from PySide6.QtCore import QAbstractTableModel, Qt, QModelIndex
import pandas as pd

class PandasModel(QAbstractTableModel):
    """A model to interface a pandas DataFrame with a QTableView."""
    def __init__(self, dataframe: pd.DataFrame, parent=None):
        super().__init__(parent)
        self._dataframe = dataframe

    def rowCount(self, parent=QModelIndex()):
        """Return the number of rows in the model."""
        if parent.isValid():
            return 0
        return len(self._dataframe)

    def columnCount(self, parent=QModelIndex()):
        """Return the number of columns in the model."""
        if parent.isValid():
            return 0
        return len(self._dataframe.columns)

    def data(self, index: QModelIndex, role=Qt.ItemDataRole.DisplayRole):
        """Return data from the DataFrame."""
        if not index.isValid() or role != Qt.ItemDataRole.DisplayRole:
            return None
        return str(self._dataframe.iloc[index.row(), index.column()])

    def headerData(self, section: int, orientation: Qt.Orientation, role=Qt.ItemDataRole.DisplayRole):
        """Return header data."""
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                return str(self._dataframe.columns[section])
            if orientation == Qt.Orientation.Vertical:
                return str(self._dataframe.index[section])
        return None

    def setDataFrame(self, dataframe: pd.DataFrame):
        """Set a new DataFrame to the model."""
        self.beginResetModel()
        self._dataframe = dataframe
        self.endResetModel()
