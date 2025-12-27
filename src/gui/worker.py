from PyQt5.QtCore import QThread, pyqtSignal

class Worker(QThread):
    """Generic worker thread to run a blocking map generation or simulation function.

    Emits:
            finished(object): result returned by the function (usually the saved file path)
            error(str): error message if exception occurs
            progress(str): optional progress messages
    """

    # Running self.finished.connect, self.error.connect, and self.progress.connect effectively causes those functions to be called when running .emit
    # eg. when connecting showMessage to self.progress, running self.progress.emit("Hello world") will run showMessage() with "Hello world" passed as an argument
    finished = pyqtSignal(object)
    error = pyqtSignal(str)
    progress = pyqtSignal(str)

    def __init__(self, func, *args, **kwargs):
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs

    def run(self):
        try:
            self.progress.emit("starting...")
            res = self.func(*self.args, **self.kwargs)
            self.finished.emit(res)
        except Exception as e:
            self.error.emit(str(e))
