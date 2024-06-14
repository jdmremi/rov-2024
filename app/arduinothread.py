import serial
from PyQt5.QtCore import pyqtSignal, QThread, QObject, QTimer, pyqtSlot
import platform
import serial.tools.list_ports as ports
import coloredlogs
import logging
import json
from queue import Queue
import time

coloredlogs.install(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class ArduinoReadWorker(QObject):
    arduino_data_channel_signal = pyqtSignal(dict)

    def __init__(self, serial_port):
        super().__init__()
        self.serial_port = serial_port  # Serial port for communication with Arduino
        self.running = True  # Flag to control the reading loop

    def read_arduino(self):
        while self.running:
            try:
                # Read a line from the serial port and decode it
                payload = self.serial_port.readline().decode("utf-8")
                logger.debug(f"PAYLOAD = {payload}")
                if payload:
                    # Parse the JSON data
                    data = json.loads(payload)
                    # Emit the signal with the received data
                    self.arduino_data_channel_signal.emit(data)
            except Exception as e:
                logger.critical(f"Error reading Arduino: {e}")


class ArduinoWriteWorker(QObject):
    def __init__(self, serial_port, queue):
        super().__init__()
        self.serial_port = serial_port  # Serial port for communication with Arduino
        self.queue = queue  # Queue for handling data to be sent to Arduino
        self.running = True  # Flag to control the writing loop

    def handle_data(self):
        while self.running:
            if not self.queue.empty():
                data = self.queue.get()  # Get data from the queue
                try:
                    # Convert data to JSON format and send to Arduino
                    payload = json.dumps(data)
                    # logger.debug(f"Sending payload to Arduino: {payload}")
                    self.serial_port.write(bytes(payload, 'utf-8'))
                    self.serial_port.flush()
                except Exception as e:
                    logger.critical(f"Error writing to Arduino: {e}")
            else:
                logger.debug("Queue is empty")
            time.sleep(0.1)  # Small delay to avoid busy waiting


class ArduinoThread(QThread):
    arduino_data_channel_signal = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self.write_queue = Queue()
        self.__serial = None
        self.__initialize_serial()

        if self.__serial:
            # Initialize reading worker and thread
            self.read_worker = ArduinoReadWorker(self.__serial)
            self.read_thread = QThread()
            self.read_worker.moveToThread(self.read_thread)
            self.read_worker.arduino_data_channel_signal.connect(
                self.forward_arduino_data)
            self.read_thread.started.connect(self.read_worker.read_arduino)
            self.read_thread.start()

            # Initialize writing worker and thread
            self.write_worker = ArduinoWriteWorker(
                self.__serial, self.write_queue)
            self.write_thread = QThread()
            self.write_worker.moveToThread(self.write_thread)
            self.write_thread.started.connect(self.write_worker.handle_data)
            self.write_thread.start()

        logger.info("Arduino thread ready!")

    def __initialize_serial(self):
        port_filter = None
        available_ports = self.__list_ports()

        logger.debug(f"Available ports: {available_ports}")

        # Set port filter based on operating system
        match platform.system():
            case "Darwin":
                port_filter = "/dev/cu.usb"
            case "Linux":
                port_filter = "/dev/ttyACM"

        # Filter ports based on the port filter
        filtered_ports = list(
            filter(lambda name: port_filter in name, available_ports))

        if len(filtered_ports) == 0:
            logger.critical(
                "Arduino port not found! Ensure proper connection.")
        else:
            port = filtered_ports[0]  # Use the first available port
            logger.debug(f"Using port: {port}")
            # Initialize serial connection
            self.__serial = serial.Serial(
                port=port, baudrate=9600, write_timeout=0, dsrdtr=True)
            logger.debug(f"Serial initialized: {self.__serial}")

    # Function to list available serial ports
    def __list_ports(self):
        return [port.device for port in list(ports.comports())]

    # Function to stop the workers and threads
    def stop(self):
        if self.read_worker:
            self.read_worker.running = False  # Stop the reading worker loop
        if self.write_worker:
            self.write_worker.running = False  # Stop the writing worker loop
        self.read_thread.quit()  # Quit the read thread
        self.read_thread.wait()  # Wait for the read thread to finish
        self.write_thread.quit()  # Quit the write thread
        self.write_thread.wait()  # Wait for the write thread to finish
        self._run_flag = False
        self.wait()  # Wait for the thread to finish

    # Function to handle data to be sent to Arduino
    def handle_data(self, data):
        # logger.debug(f"Queueing data to send to Arduino: {data}")
        self.write_queue.put(data)  # Put data in the queue

    # Slot to forward data read from Arduino to the main application
    @pyqtSlot(dict)
    def forward_arduino_data(self, data):
        # logger.debug(f"Forwarding data to main thread: {data}")
        self.arduino_data_channel_signal.emit(data)
