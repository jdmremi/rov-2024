import cv2
import serial
import numpy as np
from PyQt5.QtCore import pyqtSignal, QThread
import platform
import time
import serial.tools.list_ports as ports
import coloredlogs
import logging

coloredlogs.install(level=logging.DEBUG)
logger = logging.getLogger(__name__)

PORT_NAME = "none"


class ArduinoThread(QThread):
    arduino_data_channel_signal = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self._run_flag = True
        self.__arduino_port = None
        self.__initialize_serial()
        self.__list_ports()
        self.__serial = serial.Serial(port=PORT_NAME,
                                      baudrate=9600, timeout=.1, dsrdtr=True)

        logger.info(
            "Sleeping Arduino thread for 10s to ensure proper connection")
        time.sleep(10)
        logger.info("Arduino thread ready!")
        self.arduino_data_channel_signal.connect(self.handle_data)
        self.start()
        # Required to wait for connection to be initialized
        # time.sleep(7.5)

    def __initialize_serial(self):
        # If system platform is macos, linux, windows, etc:
        # get port name specific to platform
        # then, self.ser = ...
        platform = None

        match platform.system():
            case "Darwin":  # macOS
                pass
            case "Linux":
                pass
            case "Windows":
                pass

    def __list_ports(self):
        # create a list of com ['COM1','COM2']
        return list(ports.comports())

    def handle_data(self, data):
        pass
