#!/bin/sh
"export" "DIR=$(dirname $0)"
"exec" "$DIR/venv/bin/python3" "$0" "$@"

import re as re
import sys
from PyQt6.QtCore import Qt, QAbstractTableModel, QSortFilterProxyModel, QPoint,QTimer,QModelIndex
from PyQt6.QtWidgets import QApplication, QMainWindow, QTableView, QHeaderView, QLineEdit, QItemDelegate, QWidget, QLabel, QGroupBox, QGridLayout, QToolBar, QVBoxLayout
from PyQt6.QtGui import QColor, QAction, QIcon
from functools import partial
from collections import UserList, defaultdict
import random
import functools

# Override the default header in a table so that I can add filter boxes below the columns.
class SmartHeader(QHeaderView):
    def __init__(self, headers, parent):
        super().__init__(Qt.Orientation.Horizontal,parent)

        # Setup some switches by default that I'd want..
        self.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.setSectionsClickable(True)
        self.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.setStretchLastSection(True)

        # Make sure when the scroll bar moves the table, it also moves the filter boxes.
        parent.horizontalScrollBar().valueChanged.connect(self.alignFilterBoxes)

        # This helps move the filter boxes back toward the header to eliminate space.
        # Looks like I might not need anything, but keep them here anyway just in case.
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
        # This signal/slot will resize the filter boxes when the column width changes.
        self.sectionResized.connect(self.updateGeometries)

    def sizeHint(self):
        # Take the current size and add in the padding / size of the boxes.
        # I am overloading this mainly because the filter boxes float on the screen
        # so they aren't technically part of the header.  So I need to add in their
        # height plus any padding that I want.
        size = super().sizeHint()
        if self.filter_boxes:
            # all the filter boxes should be the same, so grab the height of the first one.
            height = self.filter_boxes[0].sizeHint().height()
            # Add the filter height so the header height
            size.setHeight(size.height() + height + self._padding)
        return size

    # When a section gets resized,  things like my filter boxes don't get resized with it.  
    # Use this function to update all the positions and geometries when things move.
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
        
    # This function places the filter boxes in the correct location.
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
            #print(f"Position = {pos}")
            #print(f"Box Height = {box_height}")
            #print(f"Section Position = {self.sectionPosition(pos)}")
            #print(f"Offset = {self.offset()}")
            #print(f"Total Header Width = {total_header_width}")
            #print(f"Height Offset = {self.heightOffset}")
            #print(f"Padding/2 = {self._padding/2}")
            #print(f"\n")
            move_to = QPoint(self.sectionPosition(pos) - self.offset() + 2 + total_header_width,
                            box_height + self.heightOffset + (int(self._padding/2)))
            
            #print(f"MoveTo:  {move_to.x()}, {move_to.y()}")
            filter_box.move(move_to)
            filter_box.resize(self.sectionSize(pos), box_height)
                
            
# I'm only really using the QSortFilterProxyModel for their sort function.  I do my own thing for filtering, but I store all 
#   of that in this class anyway.
class SmartFilterProxy(QSortFilterProxyModel):

    def __init__(self, parent=None):
        super().__init__(parent)

        # Define some special regex
        self.is_math = re.compile("^\s*(>|<|=)(\=*)\s*(.+)$")
        self.is_and = re.compile("^.+\&\&")
        self.is_or = re.compile("^.+\|\|")
        self.is_not = re.compile("^!(.+)")
 

    def custom_sort(self, item1, item2, sort_column):
        value1 = item1[sort_column]
        value2 = item2[sort_column]
        try:
            float1 = float(value1)
            float2 = float(value2)
            return float1-float2
        except:
            return value1<value2

    def key_func(self, sort_column):
        return functools.cmp_to_key(lambda item1, item2: self.custom_sort(item1, item2, sort_column))

    
    def sort(self, column, order):
    #    # Get the data in the specified column from the source model
        source_column = self.mapToSource(self.index(0, column)).column()
        data = self.sourceModel().unpaged_data

        #data_sorted = sorted(data, key=lambda row: row[source_column])
        data_sorted = sorted(data, key=self.key_func(source_column))
        #print(data_sorted)

    #    # Apply the sort order (ascending or descending)
        if order == Qt.SortOrder.DescendingOrder:
            data_sorted.reverse()

        self.sourceModel().unpaged_data = data_sorted
        self.sourceModel().updateView()

    #    # Notify the view that the data has changed
        self.layoutChanged.emit()

    def connectTextToFilter(self, table_header):
        # Store the table header
        self.table_header = table_header

        for filter_box in table_header.filter_boxes:
            # Make a timer that will delay doing anything for a small amount of time so the user can type
            #   their filter w/o it trying to update constantly
            filter_delay_timer = QTimer()
            filter_delay_timer.setSingleShot(True)
            filter_delay_timer.setInterval(750)

            # Store the timer in the filter text box so I can cross-assosiate them
            filter_box.delay_timer = filter_delay_timer

            # 'regex' is where I'll store a modified version of the text entered.
            # For example, I might want to find [ or ] and delimit them 
            filter_box.regex = ""

            # In the text change slot, look for a signal that the filter has been updated, then call the timer.
            filter_box.textChanged.connect(partial(self.filterDelay, filter_box))
            filter_delay_timer.timeout.connect(partial(self.filterDelayTimeout, filter_box))
    
    # This function starts the delay timer on the filter box
    def filterDelay(self, filter_box):
        filter_box.delay_timer.start()

    # This function is called when the timer hits timeout.  At this point, 
    # we can apply the filters
    def filterDelayTimeout(self, filter_box):
        text = filter_box.text()
        # Delimit some special characters...
        #   TODO: Might want to make this a special option later...
        text = text.replace('[', '\[')
        text = text.replace(']', '\]')
        filter_box.regex = text
        self.applyFilters()
        self.sourceModel().updateView()
        # Notify the view that the data has changed
        self.layoutChanged.emit()

    def applyFilters(self):
        # Get my parent model
        parent_table_model = self.sourceModel()

        # Get the original data from the source model
        original_data = parent_table_model.original_data

        # This will store the filtered results
        filtered_data = SmartRow()

        # Get the filter boxes
        filter_boxes = self.table_header.filter_boxes

        # Iterate over each row in the original dataset and try to determine if the filter matches.
        # This is an n^2 iteration with regex that is probably slow.  Can I make this faster?
        for row_data in original_data:
            row_matched = True
            # Now iterate over the filter boxes and see if they match..
            for pos, box in enumerate(filter_boxes):
                # Check if the filter is a pattern I want to skip
                if self.skipRegex(box.regex): continue
                # Regex pattern is good.  Try to apply it to the column data.
                if self.filterMatched(box.regex, row_data[pos]) is False:
                    row_matched = False
                    break
            # If all the patterns match, then keep the data around...
            if row_matched is True:
                filtered_data.append(row_data)
        
        # I now have a new list of data that's been filtered.  Update the table model 
        #  with the new filtered data
        #print(filtered_data)
        parent_table_model.unpaged_data = filtered_data
                
    # This is where we try to apply the filter to the actual text in the box...
    def filterMatched(self, regex, column_value):

        # First, check and see if the regex has an and/or in it.  If so, split it up and 
        # perform the checks seperately
        if self.is_and.match(regex):
            # Split the regex by the and and call seperately
            for sub_regex in regex.split('&&'):
                # If any of the "AND" values return false then we don't match...
                if self.filterMatched(sub_regex, column_value) is False:
                    return False
            # If I'm here, all the sub_regex AND stuff matched, so return true
            return True

        # Now check the OR condition.  If any of the segments match, then return true
        if self.is_or.match(regex):
            # Split the regex by the and and call seperately
            for sub_regex in regex.split('||'):
                # If any of the "OR" values return true then we DO match...
                if self.filterMatched(sub_regex, column_value) is True:
                    return True
            # If I'm here, all the sub_regex OR stuff DIDN'T matched, so return false
            return False

        if self.is_not.match(regex):
            regex = regex.replace('!', "", 1)
            if self.filterMatched(regex, column_value) is False:
                return True
            else:
                return False
            
        # Check for math regex.  If it's math, we have to do some special stuff.
        math_search_results = self.is_math.search(regex)
        #print(math_search_results)
        if math_search_results:
            # get the pieces of the math puzzle
            operator = math_search_results.groups()[0]
            is_equal = math_search_results.groups()[1]
            value = math_search_results.groups()[2]
            # Try to convert the value (which is a string) into a number that I can do
            # a math operation on...
            try:
                regex_number = float(value)
                column_number = float(column_value)
            except:
                # If I'm here, the user tried to do a numerical operation on a non-number OR the col value isn't.  
                # That doens't match...
                return False
            
            # Go through all the math conditions and see if they match...
            if operator == '=' and is_equal == '=':
                return True if (column_number == regex_number) else False
            if operator == '>' and is_equal == '=':
                return True if (column_number >= regex_number) else False
            if operator == '<' and is_equal == '=':
                return True if (column_number <= regex_number) else False
            if operator == '>' and is_equal == '':
                return True if (column_number > regex_number) else False
            if operator == '<' and is_equal == '':
                return True if (column_number < regex_number) else False

            # If I'm here, then it seems like none of my math regex worked.  Should return False
            return False
            
        if re.search(regex, str(column_value)):
          return True
        else:
          return False

    def skipRegex(self, pattern):
        # These are some patterns we want to skip
        if pattern == "": return True
        if pattern == "!": return True
        if pattern == "=": return True
        if pattern == "==": return True
        if pattern == ">": return True
        if pattern == "<": return True
        if pattern == "<=": return True
        if pattern == ">=": return True
        if pattern == ">-": return True
        if pattern == ">-": return True
        if pattern == ">=-": return True
        if pattern == ">=-": return True
        return False
        
class SmartTableView(QTableView):
    def __init__(self, parent=None):
        self.size_to_data = False
        super().__init__(parent)
        
    def resizeToData(self, min_size=500, max_size=5000):
        if self.size_to_data is True:
            self.horizontalHeader().setMaximumSectionSize(min_size)
            self.resizeColumnsToContents()
            self.resizeRowsToContents()
            self.horizontalHeader().setMaximumSectionSize(max_size)

class SmartTable():
    def __init__(self, data, headers, page_size=1000, parent=None):

        # Make a new QTableView
        self.table_view = SmartTableView()

        self.container_widget = QGroupBox(parent=parent)
        self.container_layout = QGridLayout()
        self.container_widget.setLayout(self.container_layout)
        self.container_layout.addWidget(self.table_view,2,1)

        # make a table model
        self.table_model = SmartTableModel(data, headers, page_size=page_size, parent=self.container_widget, smart_table=self)
        self.table_view.setModel(self.table_model)
        self.table_model.setTableView(self.table_view)
        self.proxy_model = None
        self.filter_header = None
        self.count_label = None
        self.value_label = None
        self.tool_bar = None

    # This function places a text label at the bottom of the table, and displays the current number
    #  of rows being displayed.
    def enableRowCount(self, switch:bool=True):
        if switch is True:
            self.count_label = QLabel()
            self.container_layout.addWidget(self.count_label,3,1)
            self.updateRowCountLabel()

    # This function will display the current cell value in a label below the table.
    def enableValueLabel(self, switch:bool=True):
        if switch is True:
            self.value_label = QLabel()
            self.container_layout.addWidget(self.value_label,4,1)
            # selectionChanged is a slot I can use to determine when the cell selection changes, by any means.
            # when it's called, use the updateValueLabel function to get the value and update the label.
            self.table_view.selectionModel().selectionChanged.connect(self.updateValueLabel)

    # This function will update the value label when the cell selection changes.
    #  It uses the selectionModel to get the selected indexes, and always grabs the upper left in a 
    #  multi-cell selection.  It then gets the data from the cell and updates the label.
    def updateValueLabel(self):
        selected_indexes = self.table_view.selectedIndexes()
        if selected_indexes:
            current_index = selected_indexes[0]
            row = current_index.row()
            col = current_index.column()
            value = str(self.table_model._data[row][col])
            self.value_label.setText(value)
    
    def updateRowCountLabel(self):
        if self.count_label is not None:
            self.count_label.setText(f"Row Count: {len(self.table_model.unpaged_data)}")

    def enableSorting(self, switch:bool=True):
        if switch is True:
            if self.proxy_model is None:
                self.proxy_model = SmartFilterProxy()
            self.proxy_model.setSourceModel(self.table_model)
            self.table_view.setModel(self.proxy_model)
            self.proxy_model.setSortRole(Qt.ItemDataRole.DisplayRole)
            self.proxy_model.setDynamicSortFilter(True)
            self.table_view.setSortingEnabled(True)
        else:
            if self.proxy_model is None:
                return
            self.proxy_model.setDynamicSortFilter(False)
            self.table_view.setSortingEnabled(False)

    def toggleColumnHidden(self, column_name:str, switch:bool=True):
        # from the column name, get the index of the column
        try:
            column_number = self.table_model._headers.index(column_name)
            self.table_view.setColumnHidden(column_number, switch)
        except:
            pass
        
    # Override the default display rules...
    def setBackgroundRoleFunction(self, function):
        self.table_model.background_role_function = function
    def setForegroundRoleFunction(self, function):
        self.table_model.foreground_role_function = function

    def enableFiltering(self, switch:bool=True):
        if switch is True:
            if self.proxy_model is None:
                self.proxy_model = SmartFilterProxy()

            self.proxy_model.setSourceModel(self.table_model)
            self.table_view.setModel(self.proxy_model)
            self.filter_header = SmartHeader(headers=headers, parent=self.table_view)
            self.table_view.setHorizontalHeader(self.filter_header)
            self.filter_header.alignFilterBoxes()
            self.proxy_model.connectTextToFilter(self.filter_header)
    
    def enableEdit(self, column_name:str=None):
        if column_name is None:
            for col,name in enumerate(self.table_model._headers):
                self.table_model.editable_columns[col] = True
                edit_box = textEditDelegate(self.table_view)
                self.table_view.setItemDelegateForColumn(col, edit_box)
        else:
            if column_name in self.table_model._headers:
                column_index = self.table_model._headers.index(column_name)
                self.table_model.editable_columns[column_index] = True
                edit_box = textEditDelegate(self.table_view)
                self.table_view.setItemDelegateForColumn(column_index, edit_box)

    def getWidget(self):
        """
        This function will return the group box where the table and other stuff associated with the table
        lives.  This way, things are sort of self contained as one convenient widget that can be added to 
        any parent view.

        Returns:
            QWidget: A QGroupBox Widget containing all the items associated with the table.
        """
        return self.container_widget
    
    def enableSizeToData(self, switch=True):
        """
        This function simply allows the view to resize the cells to the size of the contexts, up to a limit

        Args:
            switch (bool, optional): Enable or disable the auto-sizing feature. Defaults to True.
        """
        if switch is True:
            self.table_view.size_to_data = True
            self.table_view.resizeToData()
        else:
            self.table_view.size_to_data = False
        
    def enableToolbar(self, switch=True):
        if switch is True:
            self.tool_bar = SmartToolbar(self)
            self.container_layout.addWidget(self.tool_bar,1,1)

    def __update_cell(self, row, col):
        index_to_udpate = self.table_model.index(row, col)
        self.table_model.dataChanged.emit(index_to_udpate, index_to_udpate)

class SmartToolbar(QToolBar):
    def __init__(self, parent_table:SmartTable):
        super().__init__()
        # Set the styling
        self.setStyleSheet("""
                            SmartToolbar {
                              background-color: #858585; 
                              border: 2px inset grey;
                              border-radius: 5px;
                            }
                            QToolBar QToolButton {
                              padding: 0px;
                            }
                            """)
        
        # This will store all the actions
        self.actions = defaultdict(lambda: None)
        self.parent_table = parent_table

        self.actions['clear_filters'] = QAction(parent_table.getWidget())
        self.actions['clear_filters'].setText("Clear Table Filters")
        self.actions['clear_filters'].setIcon(QIcon(f"{sys.path[0]}/icons/clear.png"))
        self.addAction(self.actions['clear_filters'])
        self.actions['clear_filters'].triggered.connect(self.clearFilters)

    def clearFilters(self):
        # Get the filter boxes if they exist...
        filter_boxes = self.parent_table.filter_header.filter_boxes
        for box in filter_boxes:
            box.setText(None)


class textEditDelegate(QItemDelegate):
    def __init__(self, parent=None):
        QItemDelegate.__init__(self, parent)
    def createEditor(self, parent, option, index):
        return QLineEdit(parent)
    def setEditorData(self, editor: QWidget, index: QModelIndex) -> None:
        return super().setEditorData(editor, index)
    def setModelData(self, editor: QWidget, model: QAbstractTableModel, index: QModelIndex) -> None:
        text_box_value = editor.text()
        model.setData(index, text_box_value, Qt.ItemDataRole.EditRole)
    
class SmartTableModel(QAbstractTableModel):
    def __init__(self, data, headers, page_size=100, parent=None, smart_table:SmartTable=None):
        super().__init__(parent)
        # Convert the 2nd order list into a smart row, and store what table it belongs to...
        self._data = []
        for row, sublist in enumerate(data):
            if isinstance(sublist, SmartRow) is False:
                smart_row = SmartRow(sublist)
                data[row] = smart_row
            data[row].smart_tables.append(smart_table)
            self._data.append(data[row])

        self.unpaged_data = self._data
        self._headers = headers
        self.original_data = self._data
        self.editable_columns = [False] * len(self._headers)
        self.table_view = None
        self.smart_table = smart_table

        # Set the page size and the initial size of the first page load.
        self.page_size = page_size
        if page_size < len(self._data):
            self.display_size = page_size
        else:
            self.display_size = len(self._data)

        # Override functions for different display roles...
        self.background_role_function = None
        self.foreground_role_function = None
        
        # Prune the data to the page size
        self._data = self.original_data[0:page_size]
        self.view_size = len(self._data)

    def rowCount(self, parent=None):
        return len(self._data)

    def columnCount(self, parent=None):
        return len(self._headers)

    def setTableView(self, table_view):
        self.table_view = table_view

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < self.rowCount()) or not (0 <= index.column() < self.columnCount()):
            return None

        row = index.row()
        column = index.column()

        if role == Qt.ItemDataRole.DisplayRole:
            #print(self._data[row])
            return str(self._data[row][column])

        if role == Qt.ItemDataRole.BackgroundRole:
            if self.background_role_function is not None:
                return self.background_role_function(index)
        if role == Qt.ItemDataRole.ForegroundRole:
            if self.foreground_role_function is not None:
                return self.foreground_role_function(index)

        return None

    def setData(self, index, value, role):
        if role == Qt.ItemDataRole.EditRole:
            self._data[index.row()][index.column()] = value
            return True

        return super().setData(index, value, role)

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return self._headers[section]

        return None

    def flags(self, index: QModelIndex):
        if not index.isValid(): return Qt.ItemFlag.ItemIsEnabled
        current_column = index.column()
        if self.editable_columns[current_column] is True:
            return super().flags(index) | Qt.ItemFlag.ItemIsEditable
        else:
            return super().flags(index) | Qt.ItemFlag.ItemIsEnabled


    def updateView(self):
        # Get the new length of the data
        new_view_size = len(self.unpaged_data)
        if new_view_size > self.page_size:
            new_view_size = self.page_size

        self._data = self.unpaged_data[0:new_view_size]

        # By how much as the row size changed
        new_row_difference = new_view_size - self.view_size

        self.smart_table.updateRowCountLabel()

        # If rows have been removed, handle it here
        if new_row_difference < 0:
            first_row_to_remove = self.view_size - abs(new_row_difference)
            last_row_to_remove =  self.view_size - 1
            self.beginRemoveRows(QModelIndex(), first_row_to_remove, last_row_to_remove)
            self.endRemoveRows()
            self.view_size = new_view_size
        elif new_row_difference > 0:
            first_row_to_add = self.view_size
            last_row_to_add =  self.view_size + new_row_difference - 1
            #print(f"adding: {first_row_to_add} to {last_row_to_add}")
            self.beginInsertRows(QModelIndex(), first_row_to_add, last_row_to_add)
            self.endInsertRows()
            self.view_size = new_view_size
        else:
            return

    def canFetchMore(self, parent: QModelIndex) -> bool:
        if len(self._data) < len(self.unpaged_data):
            return True
        else:
            return False

    def fetchMore(self, parent: QModelIndex) -> None:
        # Calculate how mnay available items there are to fetch
        unpaged_data_length = len(self.unpaged_data)
        paged_data_length = len(self._data)
        available_items = unpaged_data_length - paged_data_length
        # Don't load more than the page size allows...
        if available_items > self.page_size:
            available_items = self.page_size
        # I shouldn't get something less than 0, but if I do, just return.
        if available_items <= 0:
            return

        if available_items + paged_data_length > unpaged_data_length:
            available_items = unpaged_data_length - paged_data_length

        # Insert the new rows
        # Add the data from the unpaged data
        self._data = self.unpaged_data[0:len(self._data)+available_items]
        self.beginInsertRows(QModelIndex(), paged_data_length, paged_data_length+available_items-1)
        self.endInsertRows()
        self.view_size = len(self._data)
    
    def fitRowsDisplay(self):
        pass


class SmartRow(UserList):
    def __init__(self, data=[]):
        self.hidden = False

        # Create a shadow list that will store formulas, but not the actual value
        self.formulas = [None] * len(data)

        # Store a list of all the smart tables this row exists in.  Then, when I update one cell I can update all the cells in the views...
        self.smart_tables = []

        super().__init__(data)

    def __setitem__(self, index, value):
        #print(f"Setting Value {value} at index {index}")
        super().__setitem__(index, value)
        # Now that the data is set, update the views of all the tables.
        for main_table in self.smart_tables:
            # Find the row that this row lives in...
            try:
                table_row = main_table.table_model._data.index(self)
                index_to_change = main_table.table_model.index(table_row, index)
                main_table.table_model.dataChanged.emit(index_to_change, index_to_change)
                #print(f"Updating Position: {table_row},{index}")
            except:
                continue

    def append(self, value):
        self.formulas.append(None)
        super().append(value)

app = QApplication([])

print("Loading Data...")
data = []
for i in range(1,1001):
    random1 = random.randrange(-100, 101)
    random2 = random.randrange(-100, 101)
    random3 = random.randrange(-100, 101)
    row_data = [random1, random2, random3]
    data.append(row_data)

headers = ['Num1', 'Num2', 'Num3']


def my_background_rule(index):
    model = index.model()
    column = index.column()
    if model.editable_columns[column] is True:
        return QColor(Qt.GlobalColor.white)
    else:
        return QColor(Qt.GlobalColor.black)

def my_foreground_rule(index):
    model = index.model()
    column = index.column()
    if model.editable_columns[column] is True:
        return QColor(Qt.GlobalColor.black)
    else:
        return QColor(Qt.GlobalColor.white)

main_window = QMainWindow()
main_widget = QWidget(main_window)
main_widget_layout = QVBoxLayout()
main_widget.setLayout(main_widget_layout)

print("Generating Table...")
my_table = SmartTable(data=data, headers=headers, page_size=100, parent=main_window)
print("Enabling Features...")
my_table.enableFiltering(True)
my_table.enableSorting(True)
my_table.enableEdit()
#my_table.enableEdit("Num3")
my_table.enableSizeToData()
my_table.enableRowCount(True)
my_table.enableValueLabel(True)
my_table.enableToolbar(True)
#my_table.toggleColumnHidden("Num2")
my_table.setBackgroundRoleFunction(my_background_rule)
my_table.setForegroundRoleFunction(my_foreground_rule)
main_widget_layout.addWidget(my_table.getWidget())


my_other_table = SmartTable(data=data, headers=headers, page_size=100, parent=main_window)
print("Enabling Features...")
my_other_table.enableFiltering(True)
my_other_table.enableSorting(True)
my_other_table.enableEdit()
#my_other_table.enableEdit("Num3")
my_other_table.enableSizeToData()
my_other_table.enableRowCount(True)
my_other_table.enableValueLabel(True)
my_other_table.enableToolbar(True)
#my_other_table.toggleColumnHidden("Num2")
my_other_table.setBackgroundRoleFunction(my_background_rule)
my_other_table.setForegroundRoleFunction(my_foreground_rule)
main_widget_layout.addWidget(my_other_table.getWidget())

main_window.setCentralWidget(main_widget)
main_window.resize(700, 500)
main_window.show()

app.exec()
