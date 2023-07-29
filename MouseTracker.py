from PyQt6.QtCore import Qt, QObject, QEvent

class MouseTracker(QObject):
    """
    This class keeps track of mouse click events, and store the location of that click.
    This is useful when trying to open up menu items directly where the clicking happened.
    
    Example usage:
    
    # Creation
    mouse_event_tracker = MouseTracker()

    # Usage (with a simple widget)
    myWidget = QWidget()
    global_position = myWidget.mapToGlobal(QPoint(mouse_event_tracker.x(), mouse_event_tracker.y()))
    myWidget.move(global_position)

    Args:
        parent (optional): The parent widget.  None is the default

    Returns:
        None
    """
    current_mouse_position = None

    def __init__(self, parent=None):
        super().__init__(parent)
        
    def eventFilter(self, obj, event:QEvent):
        if event.type() == Qt.MouseButton.LeftButton:
            clicked_location = event.globalPos()
            MouseTracker.current_mouse_position = clicked_location
        return super().eventFilter(obj, event)
