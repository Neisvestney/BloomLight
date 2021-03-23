import datetime
import logging
import os
import socket
import sys
import time
from copy import deepcopy

import coloredlogs
import cv2
import imutils as imutils
import numpy as np
from PyQt5 import QtWidgets
from PyQt5.QtCore import QTimer, QThread
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import QLabel, QListWidgetItem, QFileDialog

import design
from config import Field, ConfigManager
from theard import Worker

sys._excepthook = sys.excepthook


def my_exception_hook(exctype, value, traceback):
    print(exctype, value, traceback)
    sys._excepthook(exctype, value, traceback)
    sys.exit(1)


sys.excepthook = my_exception_hook

logging.basicConfig(level=logging.DEBUG)
coloredlogs.install(level='DEBUG')
logging.info("Starting BloomLight Server by SenterisTeam")


# noinspection PyTypeChecker
class App(QtWidgets.QMainWindow, design.Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)

        index = 0
        while True:
            logging.debug(f'Checking camera №{index}')
            cap = cv2.VideoCapture(index)
            if not cap.read()[0]:
                break
            cap.release()
            self.cameras_list.addItem(str(index))
            index += 1

        # self.cameras_list.addItem("0")

        # region Config
        self.is_video_recording: bool = Field(self.is_video_recording_field.isChecked, self.is_video_recording_field.setChecked, bool)
        self.video_path: str = Field(self.vidio_path_field.text, self.vidio_path_field.setText, str)

        self.ar_cam: bool = Field(self.ar_cam_field.isChecked, self.ar_cam_field.setChecked, bool)
        self.cam_view: bool = Field(self.cam_view_field.isChecked, self.cam_view_field.setChecked, bool)
        self.camera_id: int = Field(lambda: int(self.cameras_list.selectedItems()[0].text()) if self.cameras_list.selectedItems() else 0, self.cameras_list.setCurrentRow, int)

        self.min_area: int = Field(self.min_area_field.value, self.min_area_field.setValue, int)
        self.reset_area: int = Field(self.reset_area_field.value, self.reset_area_field.setValue, int)
        self.frame_to_delete: int = Field(self.frame_to_delete_field.value, self.frame_to_delete_field.setValue, int)
        self.static_offset: int = Field(self.static_offset_field.value, self.static_offset_field.setValue, int)

        self.center_offset: int = Field(self.center_offset_filed.value, self.center_offset_filed.setValue, int)
        self.time_to_off: int = Field(self.time_to_off_field.value, self.time_to_off_field.setValue, int)

        self.contr_ip: str = Field(self.contr_ip_field.text, self.contr_ip_field.setText, str)
        self.contr_ip_2: str = Field(self.contr_ip_2_field.text, self.contr_ip_2_field.setText, str)

        self.config = ConfigManager(self)
        self.save.pressed.connect(self.config.save)
        # endregion

        self.select_video_path.pressed.connect(self.select_video_path_pressed)

        if not self.cameras_list.selectedItems():
            self.cameras_list.setCurrentRow(self.camera_id)

        self.cameras_list.itemClicked.connect(self.restart_cam)

        self.cap: cv2.VideoCapture = None
        self.writer: cv2.VideoWriter = None
        self.base_frame = None
        self.position_data = [0, 0]
        self.previous_light = [[time.time(), False], [time.time(), False]]

        self.previous_cnts = list()
        self.same_cnts = list()
        self.cam_worker = Worker(self.cam_process, self.cam_startup, self.cam_terminate)
        self.cam_worker.data.connect(self.cam_worker_on_data)
        # self.pushButton.pressed.connect(lambda: self.view_cam_worker.terminate())
        self.cam_worker.start()

        self.light_worker = Worker(self.light_process, lambda *args, **kwargs: 0, lambda *args, **kwargs: 0)
        self.light_worker.data.connect(self.set_light_ui)
        self.light_worker.start()

        self.reset_base_frame.pressed.connect(self.reset_base_frame_fn)

    def reset_base_frame_fn(self):
        self.base_frame = None

    def cam_worker_on_data(self, d):
        self.bridness.setValue(int(d[0]))
        self.camera_view_main.setPixmap(d[1])
        self.people_count.setValue(d[2])

    # region cam_worker
    def restart_cam(self):
        self.cam_view_field.setChecked(False)
        self.config.save()
        time.sleep(1)
        self.cam_worker.terminate()
        self.cam_worker.start()

    def select_video_path_pressed(self):
        self.vidio_path_field.setText(str(QFileDialog.getExistingDirectory(self, "Выберете путь")))
        self.config.save()

    def cam_startup(self, *args, **kwargs):
        self.base_frame = None
        self.previous_cnts = list()
        self.same_cnts = list()
        self.cap = cv2.VideoCapture(int(self.cameras_list.selectedItems()[0].text()))
        if not os.path.exists(self.video_path):
            os.makedirs(self.video_path)

        _, frame = self.cap.read()
        # frame = imutils.resize(frame, width=640)

        s = (frame.shape[1], frame.shape[0])
        fourcc = cv2.VideoWriter_fourcc(*'MJPG')
        self.writer = cv2.VideoWriter(
            os.path.join(self.video_path, datetime.datetime.now().strftime("%H.%M.%S") + ".avi"), fourcc, 30, s)

    def in_range(self, c1, c2):
        # return c1 == c2
        return c1 in range(c2 - self.static_offset, c2 + self.static_offset)

    def cntr_in_range(self, c1, c2):
        (x, y, w, h) = c1
        (x2, y2, w2, h2) = c2
        return self.in_range(x, x2) and self.in_range(y, y2) and self.in_range(w, w2) and self.in_range(h, h2)

    def cam_terminate(self, *args, **kwargs):
        if self.is_video_recording:
            self.writer.release()

        self.cap.release()
        self.base_frame = None
        self.previous_cnts = list()
        self.same_cnts = list()

    def cam_process(self, data_callback, *args, **kwargs):
        _, frame = self.cap.read()
        if frame is None:
            return

        # frame = imutils.resize(frame, width=640)

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)

        if self.base_frame is None:
            logging.warning('Base frame reset')
            self.base_frame = gray
            return

        frame_delta = cv2.absdiff(self.base_frame, gray)
        thresh = cv2.threshold(frame_delta, 25, 255, cv2.THRESH_BINARY)[1]
        thresh = cv2.dilate(thresh, None, iterations=2)

        cnts = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL,
                                cv2.CHAIN_APPROX_SIMPLE)
        cnts = imutils.grab_contours(cnts)

        line_y = int(len(frame) / 2 + self.center_offset)
        self.position_data = [0, 0]

        for c in cnts:
            if self.min_area != 0 and cv2.contourArea(c) < self.min_area:
                continue
            if self.reset_area != 0 and cv2.contourArea(c) > self.reset_area:
                logging.warning('Base frame reset by reset area')
                self.base_frame = gray
                return

            (x, y, w, h) = cv2.boundingRect(c)
            center_y = int(y + h / 2)
            center = (int(x + w / 2), center_y)

            for p in self.previous_cnts:
                (x2, y2, w2, h2) = cv2.boundingRect(p)
                if self.cntr_in_range((x, y, w, h), (x2, y2, w2, h2)):
                    self.same_cnts.append([0, (x2, y2, w2, h2)])

            if center_y < line_y:
                self.position_data[0] += 1
            else:
                self.position_data[1] += 1

            if self.ar_cam:
                cv2.rectangle(frame, (x, y), (x + w, y + h), (205, 39, 95), 2)
                cv2.circle(frame, center, 3, (205, 39, 95), 5)

        for p in self.same_cnts[:]:
            detected = False
            for c in cnts:
                (x, y, w, h) = cv2.boundingRect(c)
                if self.cntr_in_range(cv2.boundingRect(c), p[1]):
                    p[0] += 1

                    if p[0] in range(150, 299):
                        if self.ar_cam:
                            center_y = int(y + h / 2)
                            center = (int(x + w / 2), center_y)
                            cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 255, 255), 2)
                            cv2.circle(frame, center, 3, (255, 255, 255), 5)
                    if p[0] == 300:
                        logging.warning(f'Cutting zone with unmoved object: {x}:{y} ({w} x {h}). Count: {p[0]}')
                        cropped = gray[y:y+h, x:x+w]
                        self.base_frame[y:y+h, x:x+w] = cropped
                        self.same_cnts.remove(p)
                        if self.cam_view:
                            cv2.imshow("Cropped", imutils.resize(cropped,  width=300))

                    detected = True
                    continue

            if not detected:
                self.same_cnts.remove(p)

        self.previous_cnts = cnts

        if self.ar_cam:
            cv2.line(frame, (0, line_y), (frame.shape[1], line_y), (255, 255, 255), 2)

        if self.is_video_recording:
            self.writer.write(frame)

        if self.cam_view:
            cv2.imshow("Camera", imutils.resize(frame, width=1000))
            cv2.imshow("Thresh", thresh)
            cv2.imshow("Gray", gray)
            cv2.imshow("Frame Delta", frame_delta)
            cv2.waitKey(1) & 0xFF
        else:
            cv2.destroyAllWindows()

        data_callback.emit([np.mean(np.mean(gray, axis=0), axis=0),
                            QPixmap.fromImage(QImage(frame, frame.shape[1], frame.shape[0], QImage.Format_BGR888)),
                            len(cnts)])

    # endregion

    # region light_worker
    def light_process(self, data_callback):
        time.sleep(1)
        light = list()

        for item in self.position_data:
            light.append(item > 0)

        new_previous_light = deepcopy(self.previous_light)

        for i, (t, l) in enumerate(self.previous_light):
            if light[i] != l:
                if (not light[i] and self.previous_light[i][1] and time.time() - self.previous_light[i][0] > self.time_to_off) or light[i] and not self.previous_light[i][1]:
                    new_previous_light[i][0] = time.time()
                    new_previous_light[i][1] = light[i]
                else:
                    light[i] = True

        data_callback.emit(light)
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        ip, port = self.contr_ip.split(":")
        sock.sendto(bytes(light), (ip, int(port)))

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        ip, port = self.contr_ip_2.split(":")
        sock.sendto(bytes(light), (ip, int(port)))
        # print(sock.recv(256))

        self.previous_light = new_previous_light

    def set_light_ui(self, light):
        self.light1.setChecked(light[0])
        self.light2.setChecked(light[1])

    # endregion

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
