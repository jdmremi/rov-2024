
import serial
from PyQt5.QtCore import pyqtSignal, QThread
import platform
import time
import serial.tools.list_ports as ports
import coloredlogs
import logging
import json
from PyQt5.QtCore import pyqtSlot

coloredlogs.install(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class ArduinoThread(QThread):
    arduino_data_channel_signal = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self._run_flag = True
        self.__serial = None
        self.__initialize_serial()
        self.__list_ports()
        self.start()  # This starts the thread and calls the run() method
        logger.info("Arduino thread ready!")

    def __initialize_serial(self):
        # Port names are different depending on the platform.
        port_filter = None
        available_ports = self.__list_ports()

        logger.debug(f"Available ports: {available_ports}")

        match platform.system():
            case "Darwin":  # macOS
                port_filter = "/dev/cu.usbmodem"  # /dev/cu.usbmodem101 on macOS
            case "Linux":
                port_filter = "/dev/ttyACM"  # /dev/ttyACM{#} on Linux

        # Get a list of ports depending on the platform.
        filtered_ports = list(
            filter(lambda name: port_filter in name, available_ports))

        # If no ports are found, then we need to log a critical error.
        if len(filtered_ports) == 0:
            logger.critical(
                "Arduino port not found! Ensure proper connection.")
            # Otherwise, we'll assume that the port for our Arduino is the first in the list.
            # Then we'll initialize a serial connection under that port.
        else:
            port = filtered_ports[0]
            logger.debug(f"Available ports: {filtered_ports}")
            self.__serial = serial.Serial(port=port,
                                          baudrate=9600, timeout=.1, dsrdtr=True)
            logger.debug(f"Serial: {self.__serial}")
            # Required
            # logger.info(
            #   "Sleeping Arduino thread for 10s to ensure proper connection")
            # time.sleep(10)

    def __list_ports(self):
        # create a list of com ['COM1','COM2']
        return [port.device for port in list(ports.comports())]

    def run(self):
        logger.debug("Arduino read thread started")
        while self._run_flag and self.__serial:
            try:
                payload = self.__serial.readline().decode("utf-8")
                if payload:
                    data = json.loads(payload)
                    logger.debug(f"Payload received from Arduino: {payload}")
                    self.arduino_data_channel_signal.emit(data)
            except Exception as e:
                logger.critical(f"Error reading arduino: {e}")

    def stop(self):
        self._run_flag = False
        self.wait()

    def handle_data(self, data):
        payload = json.dumps(data)
        if self.__serial:
            self.__serial.write(bytes(payload, 'utf-8'))
