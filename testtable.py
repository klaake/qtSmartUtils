#!/bin/sh
"export" "DIR=$(dirname $0)"
"exec" "$DIR/venv/bin/python3" "$0" "$@"

import typing
from PyQt6.QtCore import QObject, Qt, QAbstractTableModel, QSortFilterProxyModel, QPoint
from PyQt6.QtWidgets import QApplication, QMainWindow, QTableView, QHeaderView, QLineEdit


class SmartHeader(QHeaderView):
    def __init__(self, headers, parent):
        super().__init__(Qt.Orientation.Horizontal,parent)

        # Setup some switches by default that I'd want..
        self.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.setSectionsClickable(True)
        self.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.setStretchLastSection(True)


        # This helps move the filter boxes back toward the header to eliminate space.
        self.heightOffset = 0
        # This is the space between the header and the box we're making, in px
        self._padding = 0

        # Keep an ordered list of filter boxes
        self.filter_boxes = []

        # Make the filter boxes...
        for header_name in headers:
            new_box = QLineEdit(parent=parent)
            new_box.setPlaceholderText(header_name)
            self.filter_boxes.append(new_box)

        self.alignFilterBoxes()

    def sizeHint(self):
        # Take the current size and add in the padding / size of the boxes.
        size = super().sizeHint()
        if self.filter_boxes:
            height = self.filter_boxes[0].sizeHint().height()
            size.setHeight(size.height() + height + self._padding)
        return size

    def updateGeometries(self):
        try:
            if self.filter_boxes:
                height = self.filter_boxes[0].sizeHint().height()
                self.setViewportMargins(0,0,0, height + self._padding)
            else:
                self.setViewportMargins(0,0,0,0)
            super().updateGeometries()
            self.alignFilterBoxes()
        except:
            super().updateGeometries()
        
    def alignFilterBoxes(self):
        total_header_width = 0
        if self.parent() is not None:
            try:
                total_header_width = self.parent().verticalHeader().sizeHint().width()
            except:
                pass
        
        # Now that I have the total widtth of the header, go through each column and get it's width, then place it.
        for pos, filter_box in enumerate(self.filter_boxes):
            box_height = filter_box.sizeHint().height()
            print(f"Position = {pos}")
            print(f"Box Height = {box_height}")
            print(f"Section Position = {self.sectionPosition(pos)}")
            print(f"Offset = {self.offset()}")
            print(f"Total Header Width = {total_header_width}")
            print(f"Height Offset = {self.heightOffset}")
            print(f"Padding/2 = {self._padding/2}")
            print(f"\n")
            move_to = QPoint(self.sectionPosition(pos) - self.offset() + 2 + total_header_width,
                            box_height + self.heightOffset + (int(self._padding/2)))
            
            print(f"MoveTo:  {move_to.x()}, {move_to.y()}")
            filter_box.move(move_to)
            filter_box.resize(self.sectionSize(pos), box_height)
                
            
class SmartFilterProxy(QSortFilterProxyModel):
    def __init__(self, parent=None):
        super().__init__(parent)


class SmartTable():
    def __init__(self, data, headers, parent=None):

        # Make a new QTableView
        self.table_view = QTableView()
        # make a table model
        self.table_model = CustomTableModel(data, headers, parent)
        self.table_view.setModel(self.table_model)
        self.proxy_model = None
        self.filter_header = None

    def enableFiltering(self, switch:bool=True):
        if switch is True:
            if self.proxy_model is None:
                self.proxy_model = SmartFilterProxy()
                self.proxy_model.setSourceModel(self.table_model)
                self.table_view.setModel(self.proxy_model)
                self.filter_header = SmartHeader(headers=headers, parent=self.table_view)
                self.table_view.setHorizontalHeader(self.filter_header)
                self.filter_header.alignFilterBoxes()
    
    def getWidget(self):
        return self.table_view
    
class CustomTableModel(QAbstractTableModel):
    def __init__(self, data, headers, parent=None):
        super().__init__(parent)
        self._data = data
        self._headers = headers
        self.original_data = data

    def rowCount(self, parent=None):
        return len(self._data)

    def columnCount(self, parent=None):
        return len(self._headers)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < self.rowCount()) or not (0 <= index.column() < self.columnCount()):
            return None

        row = index.row()
        column = index.column()

        if role == Qt.ItemDataRole.DisplayRole:
            return str(self._data[row][column])

        return None

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return self._headers[section]

        return None

app = QApplication([])

data = [
    ['John', 'Doe', 'john.doe@example.com'],
    ['Jane', 'Smith', 'jane.smith@example.com'],
    ['Michael', 'Johnson', 'michael.johnson@example.com'],
    # ...
]

headers = ['First Name', 'Last Name', 'Email']

main_window = QMainWindow()
my_table = SmartTable(data=data, headers=headers, parent=main_window)
my_table.enableFiltering(True)
main_window.setCentralWidget(my_table.getWidget())
main_window.resize(400, 300)
main_window.show()

app.exec()
