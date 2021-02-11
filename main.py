import datetime
import logging
import os
import sys
import time

import cv2
import imutils as imutils
import numpy as np
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
        self.cameras_list.itemClicked.connect(self.restart_cam)

        self.cap: cv2.VideoCapture = None
        self.writer: cv2.VideoWriter = None
        self.base_frame = None

        self.cam_worker = Worker(self.cam_process, self.cam_startup, self.cam_terminate)
        self.cam_worker.data.connect(lambda d: self.bridness.setValue(int(d)))
        # self.pushButton.pressed.connect(lambda: self.view_cam_worker.terminate())
        self.cam_worker.start()

    def restart_cam(self):
        self.cam_view.setChecked(False)
        time.sleep(1)
        self.cam_worker.terminate()
        self.cam_worker.start()

    def select_video_path_pressed(self):
        self.vidio_path.setText(str(QFileDialog.getExistingDirectory(self, "Выберете путь")))

    def cam_startup(self, *args, **kwargs):
        self.base_frame = None
        self.cap = cv2.VideoCapture(int(self.cameras_list.selectedItems()[0].text()))
        if not os.path.exists(self.vidio_path.text()):
            os.makedirs(self.vidio_path.text())

        _, frame = self.cap.read()
        frame = imutils.resize(frame, width=500)

        s = (frame.shape[1], frame.shape[0])
        fourcc = cv2.VideoWriter_fourcc(*'MJPG')
        self.writer = cv2.VideoWriter(os.path.join(self.vidio_path.text(), datetime.datetime.now().strftime("%H.%M.%S") + ".avi"), fourcc, 30, s)

    def cam_terminate(self, *args, **kwargs):
        self.writer.release()
        self.cap.release()

    def cam_process(self, data_callback, data2_callback, *args, **kwargs):
        _, frame = self.cap.read()

        frame = imutils.resize(frame, width=500)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)

        data_callback.emit(np.mean(np.mean(gray, axis=0), axis=0))

        if self.base_frame is None:
            self.base_frame = gray
            return

        frame_delta = cv2.absdiff(self.base_frame, gray)
        thresh = cv2.threshold(frame_delta, 25, 255, cv2.THRESH_BINARY)[1]
        thresh = cv2.dilate(thresh, None, iterations=2)

        cnts = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL,
                                cv2.CHAIN_APPROX_SIMPLE)
        cnts = imutils.grab_contours(cnts)

        line_y = int(len(frame) / 2 + self.center_offset.value())
        position_data = [0, 0]

        for c in cnts:
            if self.min_area.text() != "0" and self.min_area.text() != "" and cv2.contourArea(c) < int(self.min_area.text()):
                continue
            if self.reset_area.text() != "0" and self.reset_area.text() != "" and cv2.contourArea(c) > int(self.reset_area.text()):
                logging.info('Base frame reset')
                self.base_frame = gray
                return
            (x, y, w, h) = cv2.boundingRect(c)
            center_y = int(y + h/2)
            center = (int(x + w/2), center_y)

            if center_y < line_y:
                position_data[0] += 1
            else:
                position_data[1] += 1

            if self.ar_cam.isChecked():
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                cv2.circle(frame, center, 5, (0, 0, 255), 4)

        data2_callback.emit(position_data)
        print(position_data)

        if self.ar_cam.isChecked():
            cv2.line(frame, (0, line_y), (500, line_y), (255, 0, 0), 2)

        self.writer.write(frame)

        if self.cam_view.isChecked():
            cv2.imshow("Camera", frame)
            cv2.imshow("Thresh", thresh)
            cv2.imshow("Gray", gray)
            cv2.imshow("Frame Delta", frame_delta)
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
