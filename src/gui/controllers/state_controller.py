from PyQt5.QtWidgets import QPushButton, QStatusBar


class StateController:
    """
    Handles the busy and idle states of the PyQT app
    """
    def __init__(self, status_bar: QStatusBar, *buttons: list[QPushButton]):
        self.status = status_bar
        self.buttons = buttons

    def busy(self, msg: str | None = None):
        """
        Disables buttons
        """
        for b in self.buttons:
            b.setDisabled(True)
        if msg:
            self.status.showMessage(msg)

    def idle(self, msg: str | None = None):
        """
        Enables buttons
        """
        for b in self.buttons:
            b.setDisabled(False)
        if msg:
            self.status.showMessage(msg)
