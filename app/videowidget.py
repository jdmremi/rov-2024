from PyQt5.QtWidgets import QWidget, QLabel
from PyQt5.QtCore import pyqtSlot
import numpy as np
import logging
import coloredlogs

# Local
from videothread import VideoThread

WINDOW_TITLE = "ROV Control"
VIDEO_WIDTH = int(640*1.25)
VIDEO_HEIGHT = int(480)
WINDOW_WIDTH = 1920
WINDOW_HEIGHT = 1080
GREEN_TEXT_CSS = "color: green"
RED_TEXT_CSS = "color: red"

coloredlogs.install(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class VideoWidget(QWidget):
    def __init__(self, width, height):
        super().__init__()
        logger.info("Video thread initialized")

        # Part of the GUI which displays the camera input.
        self.__image_label = QLabel(self)
        self.__image_label.setFixedSize(width, height)
        self.__image_label.setScaledContents(True)
        # create the video capture thread, attach the event handler, and start it.
        self.__video_thread = VideoThread(width, height)
        self.__video_thread.change_pixmap_signal.connect(self.update_image)
        self.__video_thread.start()

    # Event handler for updating the image_label with a new opencv image.
    @pyqtSlot(np.ndarray)
    def update_image(self, cv_img):
        qt_img = self.__video_thread.convert_cv_qt(cv_img)
        self.__image_label.setPixmap(qt_img)

    def get_video_thread(self):
        return self.__video_thread
