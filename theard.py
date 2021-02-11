import logging
import sys
import traceback

from PyQt5.QtCore import QObject, pyqtSignal, QThread


logging.basicConfig(format='[%(asctime)s] %(message)s', level=logging.DEBUG)


class Worker(QThread):
    finished = pyqtSignal()
    error = pyqtSignal(tuple)

    progress = pyqtSignal(int)
    data = pyqtSignal(object)
    data2 = pyqtSignal(object)

    def __init__(self, fn, startup, terminatefn, *args, **kwargs):
        super(Worker, self).__init__()

        # Store constructor arguments (re-used for processing)
        self.fn = fn
        self.startup = startup
        self.terminatefn = terminatefn
        self.args = args
        self.kwargs = kwargs

        # Add the callback to our kwargs
        self.kwargs['data_callback'] = self.data
        self.kwargs['data2_callback'] = self.data2

    def run(self):
        """
        Initialise the runner function with passed args, kwargs.
        """
        logging.info(f"Started thread {self.fn} with {self.args} and {self.kwargs}")
        # Retrieve args/kwargs here; and fire processing using them
        try:
            self.startup(*self.args, **self.kwargs)
            while True:
                self.fn(*self.args, **self.kwargs)
        except:
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            self.error.emit((exctype, value, traceback.format_exc()))
        finally:
            self.finished.emit()  # Done

    def terminate(self):
        self.terminatefn(*self.args, **self.kwargs)
        logging.info(f"Thread {self.fn} terminated")
        super(Worker, self).terminate()
