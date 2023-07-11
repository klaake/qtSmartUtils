#!/bin/sh
"export" "DIR=$(dirname $0)"
"exec" "$DIR/venv/bin/python3" "$0" "$@"

import sys
from abc import ABC, abstractmethod
import typing
from PyQt6 import QtCore, QtGui
# Importing all this stuff might be a waste of resources...check it later...
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from collections import defaultdict
from functools import partial

# This is an abstract class.  It helps keep all the classes that 
#  inherit from it consistent by enforcing they have certain functions.  You can 
#  enforce these functions with the @abstractmethod decorator:
#  https://blog.teclado.com/python-abc-abstract-base-classes/
class guiInput(ABC):
    @abstractmethod
    def get_label(self):
        pass
    @abstractmethod
    def get_value(self):
        pass
    @abstractmethod
    def get_object(self):
        pass
    
class booleanInput(guiInput):
    def __init__(self, label:str, init_value:bool=False):
        self.label = label
        self.object = QCheckBox()
        self.object.setChecked(init_value)

    def get_label(self):
        return self.label
    def get_value(self):
        return self.object.isChecked()
    def get_object(self):
        return self.object
    def set_size(self, size:int):
        pass
    def set_value(self, value:bool):
        self.object.setChecked(value)
    def onSelectConditional(self, selection, actionProc=None):
        pass
    def onBoolConditional(self, actionProc=None):
        pass
    
class intSpinInput(guiInput):
    def __init__(self, label:str, init_value:int=0, min:int=0, max:int=100, increment:int=1):
        self.label = label
        self.object = QSpinBox()
        self.object.setMinimum(min)
        self.object.setMaximum(max)
        self.object.setValue(init_value)
        self.object.setSingleStep(increment)

    def get_label(self):
        return self.label
    def get_value(self):
        return self.object.value()
    def get_object(self):
        return self.object
    def set_size(self, size:int):
        pass
    def set_value(self, value:int):
        return self.object.setValue(value)
    def onSelectConditional(self, selection, actionProc=None):
        pass
    def onBoolConditional(self, actionProc=None):
        pass
    
    
class textLineInput(guiInput):
    def __init__(self, label:str, init_value:str=''):
        self.label = label
        self.object = QLineEdit()
        self.object.setText(init_value)
    # These are the 3 required functions
    def get_label(self):
        return self.label
    def get_value(self):
        return self.object.text()
    def get_object(self):
        return self.object
    def set_size(self, size:int):
        return self.object.setMinimumWidth(size)
    def set_value(self, value:str):
        return self.object.setText(value)
    def onSelectConditional(self, selection, actionProc=None):
        pass
    def onBoolConditional(self, actionProc=None):
        pass

class dateInput(guiInput):
    def __init__(self, label:str):
        self.label = label
        self.object = QDateEdit()
        self.current_date = QtCore.QDate.currentDate()
        self.future_date = self.current_date.addYears(10)
        self.past_date = self.current_date.addYears(-10)
        self.object.setDateRange(self.past_date, self.future_date)
        self.object.setDate(self.current_date)
        self.object.setCalendarPopup(True)
    # These are the 3 required functions
    def get_label(self):
        return self.label
    def get_value(self):
        return self.object.date()
    def get_object(self):
        return self.object
    def set_size(self, size:int):
        pass
    def set_value(self, date:QDate):
        return self.object.setDate(date)
    def onSelectConditional(self, selection, actionProc=None):
        pass
    def onBoolConditional(self, actionProc=None):
        pass

class optionInput(guiInput):
    def __init__(self, label:str, option_values, default_selection=None, flags=None):
        self.label = label
        self.object = QComboBox()

        for value in option_values:
            if type(value) is str:
                self.object.addItem(value)

        if default_selection is not None:
            if default_selection in option_values:
                self.object.setCurrentIndex(self.object.findText(default_selection))
            
    def get_label(self):
        return self.label
    def get_value(self):
        return self.object.currentText()
    def get_object(self):
        return self.object
    def set_size(self, size:int):
        self.object.setMinimumWidth(size)
        self.object.setMaximumWidth(size)
        return
    def set_value(self, value:str):
        index = self.object.findText(value)
        # returns -1 if the value is not in the combo box
        if index > 0:
          self.object.setCurrentIndex(index)
        return
    def onSelectConditional(self, selection, actionProc=None):
        pass
    def onBoolConditional(self, actionProc=None):
        pass

class radioInput(guiInput):
    def __init__(self, label:str, option_values, default_selection=None, flags=None):
        self.label = label
        self.groupbox = QGroupBox()
        self.layout = QVBoxLayout()
        self.groupbox.setLayout(self.layout)
        self.button_group = QButtonGroup()
        self.object = self.groupbox
        self.buttons_by_name = defaultdict(lambda: None)

        for value in option_values:
            if type(value) is str:
                button = QRadioButton(value)
                self.buttons_by_name[value] = button
                self.button_group.addButton(button)
                self.layout.addWidget(button)
        
        #self.layout.addWidget(self.groupbox)

        if default_selection is not None:
            button = self.buttons_by_name[default_selection]
            if button is not None:
                button.setChecked(True)
            
    def get_label(self):
        return self.label
    def get_value(self):
        selected_button = self.button_group.checkedButton()
        return selected_button.text()
    def get_object(self):
        return self.object
    def set_size(self, size:int):
        pass
    def set_value(self, value:str):
        if value is not None:
            button = self.buttons_by_name[value]
            if button is not None:
                button.setChecked(True)
        return
    def onSelectConditional(self, selection, actionProc=None):
        pass
    def onBoolConditional(self, actionProc=None):
        pass

class dirInput(guiInput):
    def __init__(self, label:str):
        self.label = label
        self.groupbox = QGroupBox()
        self.layout = QHBoxLayout()
        self.groupbox.setLayout(self.layout)
        self.object = self.groupbox

        self.dir_text_input = QLineEdit()
        self.dir_text_input.setMinimumWidth(300)
        self.layout.addWidget(self.dir_text_input)
        self.select_dir_button = QPushButton()
        self.select_dir_button.setText("Select Directory...")
        self.layout.addWidget(self.select_dir_button)
        self.select_dir_button.clicked.connect(self.selectDir)

    def selectDir(self):
        self.dir_name = QFileDialog.getExistingDirectory(None,"Select Directory...")
        if self.dir_name == "":
            return
        self.dir_text_input.setText(self.dir_name)
    def get_label(self):
        return self.label
    def get_value(self):
        return self.dir_text_input.text()
    def get_object(self):
        return self.object
    def set_size(self, size:int):
        return self.object.setMinimumWidth(size)
    def set_value(self, value:str):
        self.dir_text_input.setText(value)
        return
    def onSelectConditional(self, selection, actionProc=None):
        pass
    def onBoolConditional(self, actionProc=None):
        pass

class fileInput(guiInput):
    def __init__(self, label:str):
        self.label = label
        self.groupbox = QGroupBox()
        self.layout = QHBoxLayout()
        self.groupbox.setLayout(self.layout)
        self.object = self.groupbox

        self.file_text_input = QLineEdit()
        self.file_text_input.setMinimumWidth(300)
        self.layout.addWidget(self.file_text_input)
        self.select_file_button = QPushButton()
        self.select_file_button.setText("Select File...")
        self.layout.addWidget(self.select_file_button)
        self.select_file_button.clicked.connect(self.selectFile)

    def selectFile(self):
        self.file_name = QFileDialog.getOpenFileName(None, "Select File...")
        if self.file_name[0] == "":
            return
        self.file_text_input.setText(self.file_name[0])
    def get_label(self):
        return self.label
    def get_value(self):
        return self.file_text_input.text()
    def get_object(self):
        return self.object
    def set_size(self, size:int):
        return self.object.setMinimumWidth(size)
    def set_value(self, value:str):
        self.file_text_input.setText(value)
        return
    def onSelectConditional(self, selection, actionProc=None):
        pass
    def onBoolConditional(self, actionProc=None):
        pass
        

class groupBox():
    def __init__(self, title: str):
        self.title = title
        self.my_layout = None


# Override the QDialog to make a special one that adds inputs in an ordered manner.
class inputWidgets(QDialog):
    def __init__(self, dialogTitle="", groupTitle="", widget_grid=[], parent=None):
        super().__init__(parent)

        # Store all the inputs in a hash by their name so I can look them up easily later...
        #   Return None if nothing is stored...
        self.widgets_by_name = defaultdict(lambda: None)

        # set the layout of the dialog.
        # This is the overall layout of the dialog.
        self.parent_layout = QVBoxLayout(self)
        self.setWindowTitle(dialogTitle)
        self.setLayout(self.parent_layout)
        group_box = QGroupBox(groupTitle,self)
        widget_layout = QGridLayout()
        group_box.setLayout(widget_layout)
        self.parent_layout.addWidget(group_box)

        # now I can take the 2x2 array of inputs and start to add them to the layout
        row = 1
        col = 1
        for row_of_widgets in widget_grid:
            col = 1
            for widget in row_of_widgets:
                if widget.__class__.__name__ == "groupBox":
                    new_group = QGroupBox(widget.title, self)
                    widget_layout = QGridLayout()
                    new_group.setLayout(widget_layout)
                    self.parent_layout.addWidget(new_group)
                    row=1
                    break
                # Add the label first, then the actual object..
                label = QLabel(group_box)
                label.setText(widget.get_label())
                widget_layout.addWidget(label, row, col)
                col = col + 1
                # Now add the object....
                widget_layout.addWidget(widget.get_object(), row, col)
                # Store the widget for lookup later.
                self.widgets_by_name[widget.get_label()] = widget
                col = col + 1
            row = row + 1

        # Now we need to make the accept/cancel buttons
        self.button_box = QDialogButtonBox(self)
        # We add the buttons we want by using bitwise or'ing of special variables
        self.button_box.setStandardButtons(QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Ok)
        self.button_box.setOrientation(Qt.Orientation.Horizontal)
        # These are the slots that determine what happens when the user hits ok or cancel
        self.button_box.accepted.connect(lambda: self.button_action(True))
        self.button_box.rejected.connect(lambda: self.button_action(False))

        # Add the layouts to the dialog
        self.parent_layout.addWidget(self.button_box)

        self.setModal(True)
        self.output = None
        self.accepted = False

    def set_size(self, widget_name:str, size:int):
        widget = self.widgets_by_name[widget_name]
        if widget is None:
            return
        widget.set_size(size)

    def set_value(self, widget_name:str, value):
        widget = self.widgets_by_name[widget_name]
        if widget is None:
            return
        widget.set_value(value)

    # Override the closeEvent function of the dialog to do something after we're done...
    def closeEvent(self, event):
        self.output = defaultdict(lambda: None)
        for name, widget in self.widgets_by_name.items():
            self.output[name] = widget.get_value()
        
    def button_action(self, accepted):
        self.accepted = accepted
        self.close()

def main():
    app = QApplication(sys.argv)

    window = QMainWindow()
    window.setWindowTitle("Simple PyQt6 Program")
    window.setGeometry(100, 100, 300, 200)  # (x, y, width, height)
    window.show()

    myOptions = ["Option1", "Option2", "Option3", "DefaultOption"]
    myRadioOptions = ["Do It", "Dont Do it"]

    my_inputs = [ 
                 [textLineInput("Input #1"), textLineInput("Input #2")],
                 [groupBox("First Group")],
                 [textLineInput("Input #3")],
                 [groupBox("Second Group")],
                 [textLineInput("Input #4"), textLineInput("Input #5")],
                 [optionInput("Great Options", myOptions, "DefaultOption")],
                 [radioInput("One Or The Other", myRadioOptions, "Dont Do it")],
                 [booleanInput("Want This?"), booleanInput("How About This?")],
                 [groupBox("Number Stuff")],
                 [intSpinInput("Integer Number",13, -10, 100, 1)],
                 [groupBox("Calendar Stuff")],
                 [dateInput("Due Date")],
                 [groupBox("Filesystem Stuff")],
                 [fileInput("Important File")],
                 [dirInput("Important Dir")],
                ]
    dialog = inputWidgets(dialogTitle="My Inputs", groupTitle="Initial Box of Inputs", widget_grid=my_inputs, parent=window)
    dialog.set_size("Input #1", 200)
    dialog.set_size("Input #2", 100)
    dialog.set_value("Input #1", "Testing the value")
    dialog.exec()

    if dialog.accepted is True:
        print(f"Value of Input #1 is: {dialog.output['Input #1']}")
        print(f"Value of Input #2 is: {dialog.output['Input #2']}")
        print(f"Value of Input #3 is: {dialog.output['Input #3']}")
        print(f"Value of Input #4 is: {dialog.output['Input #4']}")
        print(f"Value of Input #5 is: {dialog.output['Input #5']}")
        print(f"Value of Great Options is: {dialog.output['Great Options']}")
        print(f"Value of One Or The Other is: {dialog.output['One Or The Other']}")
        print(f"Value of Want This: {dialog.output['Want This?']}")
        print(f"Value of How About This: {dialog.output['How About This?']}")
        print(f"Value of Integer Number {dialog.output['Integer Number']}")
        print(f"Value of Due Date {dialog.output['Due Date'].toString('yyyy-MM-dd')}")
        print(f"Value of Important File {dialog.output['Important File']}")
        print(f"Value of Important Dir {dialog.output['Important Dir']}")

    sys.exit(app.exec())

if __name__ == '__main__':
    main()
