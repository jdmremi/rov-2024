import serial
from PyQt5.QtCore import pyqtSignal, QThread, QObject, QTimer, pyqtSlot
import platform
import serial.tools.list_ports as ports
import coloredlogs
import logging
import json
from queue import Queue

coloredlogs.install(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class ArduinoWorker(QObject):
    arduino_data_channel_signal = pyqtSignal(dict)

    def __init__(self, serial_port, queue):
        super().__init__()
        self.serial_port = serial_port
        self.queue = queue
        self.running = True

    def read_arduino(self):
        while self.running:
            try:
                payload = self.serial_port.readline().decode("utf-8")
                if payload:
                    data = json.loads(payload)
                    self.arduino_data_channel_signal.emit(data)
            except Exception as e:
                logger.critical(f"Error reading Arduino: {e}")

    def handle_data(self):
        while self.running:
            if not self.queue.empty():
                data = self.queue.get()
                try:
                    payload = json.dumps(data)
                    self.serial_port.write(bytes(payload, 'utf-8'))
                    self.serial_port.flush()
                except Exception as e:
                    logger.critical(f"Error writing to Arduino: {e}")


class ArduinoThread(QThread):
    arduino_data_channel_signal = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self.queue = Queue()
        self.__serial = None
        self.__initialize_serial()

        if self.__serial:
            self.worker = ArduinoWorker(self.__serial, self.queue)
            self.worker_thread = QThread()
            self.worker.moveToThread(self.worker_thread)
            self.worker.arduino_data_channel_signal.connect(
                self.forward_arduino_data)
            self.worker_thread.started.connect(self.worker.read_arduino)
            self.worker_thread.start()

            self.write_timer = QTimer()
            self.write_timer.timeout.connect(self.worker.handle_data)
            self.write_timer.start(100)  # Adjust the interval as needed

        logger.info("Arduino thread ready!")

    def __initialize_serial(self):
        port_filter = None
        available_ports = self.__list_ports()

        logger.debug(f"Available ports: {available_ports}")

        match platform.system():
            case "Darwin":
                port_filter = "/dev/cu.usbmodem"
            case "Linux":
                port_filter = "/dev/ttyACM"

        filtered_ports = list(
            filter(lambda name: port_filter in name, available_ports))

        if len(filtered_ports) == 0:
            logger.critical(
                "Arduino port not found! Ensure proper connection.")
        else:
            port = filtered_ports[0]
            logger.debug(f"Available ports: {filtered_ports}")
            self.__serial = serial.Serial(
                port=port, baudrate=9600, timeout=.1, dsrdtr=True)
            logger.debug(f"Serial: {self.__serial}")

    def __list_ports(self):
        return [port.device for port in list(ports.comports())]

    def stop(self):
        if self.worker:
            self.worker.running = False
        self.worker_thread.quit()
        self.worker_thread.wait()
        self.write_timer.stop()
        self._run_flag = False
        self.wait()

    def handle_data(self, data):
        self.queue.put(data)

    @pyqtSlot(dict)
    def forward_arduino_data(self, data):
        logger.debug(f"Forwarding data to main thread: {data}")
        self.arduino_data_channel_signal.emit(data)
