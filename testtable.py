#!/bin/sh
"export" "DIR=$(dirname $0)"
"exec" "$DIR/venv/bin/python3" "$0" "$@"

import re as re
from PyQt6.QtCore import QObject, Qt, QAbstractTableModel, QSortFilterProxyModel, QPoint,QTimer,QModelIndex
from PyQt6.QtWidgets import QApplication, QMainWindow, QTableView, QHeaderView, QLineEdit
from functools import partial

# Override the default header in a table so that I can add filter boxes below the columns.
class SmartHeader(QHeaderView):
    def __init__(self, headers, parent):
        super().__init__(Qt.Orientation.Horizontal,parent)

        # Setup some switches by default that I'd want..
        self.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.setSectionsClickable(True)
        self.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.setStretchLastSection(True)

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

    def applyFilters(self):
        # Get my parent model
        parent_table_model = self.sourceModel()

        # Get the original data from the source model
        original_data = parent_table_model.original_data

        # This will store the filtered results
        filtered_data = []

        # Get the filter boxes
        filter_boxes = self.table_header.filter_boxes

        # Iterate over each row in the original dataset and try to determine if the filter matches.
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
        print(filtered_data)
        parent_table_model._data = filtered_data
                
        # Tell the table model to update the view
        parent_table_model.updateView()

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

            
        # Check for math regex.  If it's math, we have to do some special stuff.
        math_search_results = self.is_math.search(regex)
        print(math_search_results)
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
        super().__init__(parent)

class SmartTable():
    def __init__(self, data, headers, parent=None):

        # Make a new QTableView
        self.table_view = SmartTableView()
        # make a table model
        self.table_model = SmartTableModel(data, headers, parent)
        self.table_view.setModel(self.table_model)
        self.proxy_model = None
        self.filter_header = None

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

    def getWidget(self):
        return self.table_view
    
class SmartTableModel(QAbstractTableModel):
    def __init__(self, data, headers, parent=None):
        super().__init__(parent)
        self._data = data
        self._headers = headers
        self.original_data = data
        self.view_size = len(data)

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

    def updateView(self):
        # Get the new length of the data
        new_view_size = len(self._data)

        # By how much as the row size changed
        new_row_difference = new_view_size - self.view_size

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

app = QApplication([])

data = [
    ['John', 'Doe', 'john.doe@example.com', "30"],
    ['Jane', 'Smith', 'jane.smith@example.com', "50"],
    ['Michael', 'Johnson', 'michael.johnson@example.com', 60],
    # ...
]

headers = ['First Name', 'Last Name', 'Email', "Age"]

main_window = QMainWindow()
my_table = SmartTable(data=data, headers=headers, parent=main_window)
my_table.enableFiltering(True)
my_table.enableSorting(True)
main_window.setCentralWidget(my_table.getWidget())
main_window.resize(400, 300)
main_window.show()

app.exec()
