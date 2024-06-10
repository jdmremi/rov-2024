from PyQt5.QtCore import pyqtSignal, QThread, QTimer, pyqtSlot
import pygame
import math
import logging
import coloredlogs

coloredlogs.install(level=logging.DEBUG)
logger = logging.getLogger(__name__)

GREEN_TEXT_CSS = "color: green"
RED_TEXT_CSS = "color: red"


class JoystickThread(QThread):
    joystick_change_signal = pyqtSignal(dict)

    def __init__(self, x_bar, y_bar, z_bar, status_bar, arduino_thread, video_thread):
        super().__init__()
        logger.info("Joystick thread initialized")
        self.__run_flag = True
        self.__joystick = None
        self.__x_bar = x_bar
        self.__y_bar = y_bar
        self.__z_bar = z_bar
        self.__connection_status_bar = status_bar
        self.__arduino_thread = arduino_thread
        self.__video_thread = video_thread

        pygame.init()

        # Initialize the timer to periodically check for joystick connection
        self._wait_for_joystick_timer = QTimer(self)
        self._wait_for_joystick_timer.timeout.connect(self._wait_for_joystick)

        if pygame.joystick.get_count() == 0:
            logger.warn("No joystick detected! Waiting for joysticks...")
            self._wait_for_joystick_timer.start(1000)  # Check every second
        else:
            self._initialize_joystick()

        self.joystick_change_signal.connect(self.handle_joystick)
        self.start()

        self.__joystick_timer = QTimer(self)
        self.__joystick_timer.timeout.connect(self.check_joystick_input)
        self.__joystick_timer.start(10)

    def stop(self):
        self.__run_flag = False
        self.wait()

    def _wait_for_joystick(self):
        pygame.quit()
        pygame.init()
        if pygame.joystick.get_count() > 0:
            self._initialize_joystick()
            self._wait_for_joystick_timer.stop()

    def _initialize_joystick(self):
        self.__joystick = pygame.joystick.Joystick(0)
        self.__joystick.init()
        logger.info(f"Joystick found! Name: {self.__joystick.get_name()}")
        self.__connection_status_bar.setText(
            f"Joystick ({self.__joystick.get_name()}) connected")
        self.__connection_status_bar.setStyleSheet(GREEN_TEXT_CSS)

    @pyqtSlot(dict)
    def handle_joystick(self, commands):
        is_joystick_connected = commands["connected"]
        if is_joystick_connected:
            pass
        else:
            logger.warn("Joystick disconnected")

    def check_joystick_input(self):
        if self.__joystick is not None and pygame.joystick.get_count() > 0:
            pygame.event.pump()

            for event in pygame.event.get():
                if event.type == pygame.JOYBUTTONDOWN and event.button == 4:
                    self.__video_thread.save_screenshot()

            joystick_info = {}
            x = self.__joystick.get_axis(0)
            y = self.__joystick.get_axis(1)
            z = self.__joystick.get_axis(2)

            if abs(y) < .2:
                y = 0
            if abs(x) < .2:
                x = 0
            if abs(z) < .2:
                z = 0

            y = -y * 1.414
            x = x * 1.414

            x_new = (x * math.cos(math.pi / -4)) - (y * math.sin(math.pi / -4))
            y_new = (x * math.sin(math.pi / -4)) + (y * math.cos(math.pi / -4))

            x_new = max(min(x_new, 1.0), -1.0)
            y_new = max(min(y_new, 1.0), -1.0)

            self.__x_bar.setValue(int(abs(x_new)) * 100)
            self.__y_bar.setValue(int(abs(y_new)) * 100)
            self.__z_bar.setValue(int(abs(z)) * 100)

            joystick_info["connected"] = True
            joystick_info["joystickName"] = self.__joystick.get_name()
            joystick_info["tleft"] = x_new ** 3
            joystick_info["tright"] = y_new ** 3
            joystick_info["tup"] = -z ** 3

            rumble_freq = max(abs(x_new), abs(y_new), abs(-z ** 3))
            self.__joystick.rumble(0, abs(rumble_freq), 1)

            self.__arduino_thread.handle_data(joystick_info)

            self.joystick_change_signal.emit(joystick_info)
        else:
            self.joystick_change_signal.emit({"connected": False})
            self.__connection_status_bar.setText(f"Joystick disconnected")
            self.__connection_status_bar.setStyleSheet(RED_TEXT_CSS)
            self._wait_for_joystick()
