import cv2
import numpy as np
from PyQt5.QtCore import pyqtSignal, QThread
from PyQt5.QtGui import QPixmap
from PyQt5 import QtGui
from PyQt5.QtCore import Qt
import logging
import coloredlogs
import os
import random
import string

coloredlogs.install(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class VideoThread(QThread):
    change_pixmap_signal = pyqtSignal(np.ndarray)

    def __init__(self, width, height):
        super().__init__()
        self.__run_flag = True
        self.__display_width = height
        self.__display_height = width
        self.__recent_frame = None

    def run(self):
        # Capture from webcam 0. Device 0 is generally the only camera plugged in, but this will error if there are no cameras plugged in.
        # Sadly, OpenCV doesn't provide a straightforward way to get the number of cameras present.
        cap = cv2.VideoCapture(0)
        while self.__run_flag:
            ret, cv_img = cap.read()
            if ret:
                self.change_pixmap_signal.emit(cv_img)
                self.__recent_frame = cv_img
            else:
                logger.error(
                    "Error reading camera input. Verify that the camera is connected and restart the application.")
        # shut down capture system
        cap.release()

    # Sets run flag to False and waits for thread to finish
    def stop(self):
        self.__run_flag = False
        self.wait()

    def convert_cv_qt(self, cv_img):
        """Convert from an opencv image to QPixmap"""
        rgb_image = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        convert_to_Qt_format = QtGui.QImage(
            rgb_image.data, w, h, bytes_per_line, QtGui.QImage.Format_RGB888)
        p = convert_to_Qt_format.scaled(
            self.__display_width, self.__display_height, Qt.KeepAspectRatio)
        return QPixmap.fromImage(p)

    def save_screenshot(self, path="../rov_images/"):
        if not os.path.exists(path):
            os.mkdir(path)

        if self.__recent_frame is not None:
            file_name = ''.join(random.SystemRandom().choice(
                string.ascii_uppercase + string.digits) for _ in range(6))

            full_path = path + file_name + ".jpg"
            cv2.imwrite(full_path, self.__recent_frame)
            logger.info(f"Screenshot saved: {full_path}")
