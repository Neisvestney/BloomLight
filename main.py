import logging
import os
import sys
import time

import cv2
import imutils as imutils
from PyQt5 import QtWidgets
from PyQt5.QtCore import QTimer, QThread
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import QLabel, QListWidgetItem, QFileDialog

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

        self.select_video_path.pressed.connect(self.select_video_path_pressed)

        self.cameras_list.addItem("0")
        self.cameras_list.addItem("1")
        self.cameras_list.setCurrentRow(0)

        self.cap = cv2.VideoCapture(0)
        self.writer = None
        # while not self.cap.isOpened(): continue
        # fourcc = cv2.VideoWriter_fourcc('X', 'V', 'I', 'D')
        # w, h = self.cap.get(3), self.cap.get(4)
        # print(w, h)
        # writer = cv2.VideoWriter(os.path.join(self.vidio_path.text(), "1.mp4"), fourcc, 30, (w, h))

        self.cam_worker = Worker(self.cam_process, self.cam_startup, self.cam_terminate)
        # self.cam_worker.data.connect(lambda d: self.view_camera.setEnabled(d))
        # self.pushButton.pressed.connect(lambda: self.view_cam_worker.terminate())
        self.cam_worker.start()

    def select_video_path_pressed(self):
        self.vidio_path.setText(str(QFileDialog.getExistingDirectory(self, "Выберете путь")))

    def cam_startup(self, data_callback):
        self.cap = cv2.VideoCapture(int(self.cameras_list.selectedItems()[0].text()))
        if not os.path.exists(self.vidio_path.text()):
            os.makedirs(self.vidio_path.text())
        s = (int(self.cap.get(3)), int(self.cap.get(4)))
        fourcc = cv2.VideoWriter_fourcc(*'MJPG')
        self.writer = cv2.VideoWriter(os.path.join(self.vidio_path.text(), "1.avi"), fourcc, 30, s)

    def cam_terminate(self, data_callback, *args, **kwargs):
        self.writer.release()
        self.cap.release()
        print("rel")

    def cam_process(self, data_callback, *args, **kwargs):
        # read image in BGR format
        _, frame = self.cap.read()
        # frame = imutils.resize(frame, width=500)
        self.writer.write(frame)
        print("write")
        if self.cam_view.isChecked():
            cv2.imshow("Security Feed", frame)
            cv2.waitKey(1) & 0xFF
        else:
            cv2.destroyAllWindows()

    def closeEvent(self, event):
        self.cam_worker.terminate()
        logging.info("Good bye!")


def main():
    app = QtWidgets.QApplication(sys.argv)
    window = App()
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
