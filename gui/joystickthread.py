from PyQt5.QtCore import pyqtSignal, QThread
from PyQt5.QtCore import QTimer, pyqtSlot
import pygame
import math
import logging
import coloredlogs

coloredlogs.install(level=logging.DEBUG)
logger = logging.getLogger(__name__)

GREEN_TEXT_CSS = "color: green"
RED_TEXT_CSS = "color: red"
YELLOW_TEXT_CSS = "color: yellow"


class JoystickThread(QThread):
    joystick_change_signal = pyqtSignal(dict)

    def __init__(self, x_bar, y_bar, z_bar, status_bar, arduino_thread, video_thread):
        super().__init__()
        logger.info("Joystick thread initialized")
        self.__run_flag = True
        self.__joystick = None
        # These are QProgressBar(s) which we can update depending on the controller input.
        self.__x_bar = x_bar
        self.__y_bar = y_bar
        self.__z_bar = z_bar
        self.__connection_status_bar = status_bar
        self.__arduino_thread = arduino_thread
        self.__video_thread = video_thread

        pygame.init()
        # If no joysticks are initially connected, we run wait_for_joystick() which waits for new joysticks to be connected.
        if pygame.joystick.get_count() == 0:
            logger.warn("No joystick detected! Waiting for joysticks...")
            self.__wait_for_joystick()
        # If joysticks are initially connected, we just go straight to this block:
        else:
            self.__joystick = pygame.joystick.Joystick(0)
            self.__joystick.init()  # initialize joystick
            logger.info(f"Joystick found! Name: {self.__joystick.get_name()}")

        # Aattach the event handler, and start it.
        self.joystick_change_signal.connect(
            self.handle_joystick)
        self.start()

        # pygame needs to run on the main thread - don't ask me how or why this works.
        self.__joystick_timer = QTimer(self)
        self.__joystick_timer.timeout.connect(
            self.check_joystick_input)
        self.__joystick_timer.start(10)

    def stop(self):
        self.__run_flag = False
        self.wait()

    # This is used to handle joystick connections and reconnections.
    def __wait_for_joystick(self):
        logger.debug("Waiting for joystick...")
        pygame.quit()
        pygame.init()
        if pygame.joystick.get_count() > 0 and self.__joystick is not None:
            self.__joystick = pygame.joystick.Joystick(0)
            self.__joystick.init()
            logger.info(f"Joystick found! Name: {self.__joystick.get_name()}")

        # Handle joystick events here (send to arduino, display, etc.)

    @pyqtSlot(dict)
    def handle_joystick(self, commands):
        is_joystick_connected = commands["connected"]
        if is_joystick_connected:
            logger.debug(commands)
        else:
            logger.warn("Joystick disonnected")

    def check_joystick_input(self):
        if self.__joystick is not None and pygame.joystick.get_count() > 0:
            pygame.event.pump()

            for event in pygame.event.get():
                if event.type == pygame.JOYBUTTONDOWN and event.button == 4:
                    self.__video_thread.save_screenshot()

            joystick_info = {}

            """
            x: Horizontal axis of the left joystick.
            y: Vertical axis of the left joystick.
            z: Horizontal axis of the right joystick.   
            """
            x = self.__joystick.get_axis(0)
            y = self.__joystick.get_axis(1)
            z = self.__joystick.get_axis(2)

            # Deadzone -- Applied to the joystick axes to ignore small, unintended movements:
            if abs(y) < .2:
                y = 0
            if abs(x) < .2:
                x = 0
            if abs(z) < .2:
                z = 0

            y = -y * 1.414
            x = x * 1.414

            # Rotate x and y axis of joystick 45 degrees:
            x_new = (x*math.cos(math.pi/-4)) - \
                (y*math.sin(math.pi/-4))  # horizontal left
            y_new = (x*math.sin(math.pi/-4)) + \
                (y*math.cos(math.pi/-4))  # horizontal right

            if x_new > 1:
                x_new = 1.0
            if y_new > 1:
                y_new = 1.0
            if x_new < -1:
                x_new = -1.0
            if y_new < -1:
                y_new = -1.0

            # Updates the progress bars on the GUI -- these values may need to be tweaked
            self.__x_bar.setValue(int(abs(x_new)) * 100)
            self.__y_bar.setValue(int(abs(y_new)) * 100)
            self.__z_bar.setValue(int(abs(z)) * 100)

            joystick_info["connected"] = True
            joystick_info["joystickName"] = self.__joystick.get_name()
            joystick_info["tleft"] = x_new ** 3
            joystick_info["tright"] = y_new ** 3
            joystick_info["tup"] = -z ** 3

            rumble_freq = 0

            if x_new != 0:
                rumble_freq = x_new
            if y_new != 0:
                rumble_freq = y_new
            elif -z**3 != 0:
                rumble_freq = -z**3

            self.__joystick.rumble(0, abs(rumble_freq), 1)
            self.joystick_change_signal.emit(joystick_info)
            self.__connection_status_bar.setText(
                f"Joystick ({self.__joystick.get_name()}) connected")
            self.__connection_status_bar.setStyleSheet(GREEN_TEXT_CSS)

        else:
            self.joystick_change_signal.emit({
                "connected": False
            })

            self.__connection_status_bar.setText(f"Joystick disconnected")
            self.__connection_status_bar.setStyleSheet(RED_TEXT_CSS)
            self.__wait_for_joystick()
