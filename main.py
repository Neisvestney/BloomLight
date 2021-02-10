import logging
import sys

import cv2
from PyQt5 import QtWidgets
from PyQt5.QtCore import QTimer, QThread
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import QLabel, QListWidgetItem

import design
from theard import Worker

sys._excepthook = sys.excepthook


def my_exception_hook(exctype, value, traceback):
    print(exctype, value, traceback)
    sys._excepthook(exctype, value, traceback)
    sys.exit(1)


sys.excepthook = my_exception_hook

logging.basicConfig(format='[%(asctime)s] %(message)s', level=logging.DEBUG)
logging.info("Starting BloomLight Server by SenterisTeam")


class App(QtWidgets.QMainWindow, design.Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)

        self.cap = cv2.VideoCapture(0)

        self.view_cam_worker = Worker(self.view_cam)
        self.view_cam_worker.data.connect(lambda d: self.cam_view.setPixmap(d))
        self.pushButton.pressed.connect(lambda: self.view_cam_worker.terminate())
        self.view_cam_worker.start()

    def view_cam(self, data_callback, *args, **kwargs):
        # read image in BGR format
        ret, image = self.cap.read()
        # convert image to RGB format
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        # get image infos
        height, width, channel = image.shape
        step = channel * width
        # create QImage from image
        qImg = QImage(image.data, width, height, step, QImage.Format_RGB888)
        # show image in img_label
        data_callback.emit(QPixmap.fromImage(qImg))

    def closeEvent(self, event):
        logging.info("Good bye!")

def main():
    app = QtWidgets.QApplication(sys.argv)
    window = App()
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
