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


# Handles reading from and writing to the Arduino.
class ArduinoWorker(QObject):
    # Signal to send data read from Arduino to the main application
    arduino_data_channel_signal = pyqtSignal(dict)

    def __init__(self, serial_port, queue):
        super().__init__()
        self.serial_port = serial_port  # Serial port for communication with Arduino
        self.queue = queue  # Queue for handling data to be sent to Arduino
        self.running = True  # Flag to control the reading loop

    # Function to continuously read data from Arduino
    def read_arduino(self):
        while self.running:
            try:
                # Read a line from the serial port and decode it
                payload = self.serial_port.readline().decode("utf-8")
                if payload:
                    # Parse the JSON data
                    data = json.loads(payload)
                    # Emit the signal with the received data
                    self.arduino_data_channel_signal.emit(data)
            except Exception as e:
                logger.critical(f"Error reading Arduino: {e}")

    # Function to continuously handle data to be sent to Arduino
    def handle_data(self):
        while self.running:
            if not self.queue.empty():
                data = self.queue.get()  # Get data from the queue
                try:
                    # Convert data to JSON format and send to Arduino
                    payload = json.dumps(data)
                    self.serial_port.write(bytes(payload, 'utf-8'))
                    self.serial_port.flush()
                except Exception as e:
                    logger.critical(f"Error writing to Arduino: {e}")


# Manages the ArduinoWorker in a separate thread.
class ArduinoThread(QThread):
    # Signal to send data read from Arduino to the main application
    arduino_data_channel_signal = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self.queue = Queue()  # Queue for handling data to be sent to Arduino
        self.__serial = None
        self.__initialize_serial()  # Initialize the serial port

        if self.__serial:
            # Worker object to handle serial communication
            self.worker = ArduinoWorker(self.__serial, self.queue)
            self.worker_thread = QThread()  # Separate thread for the worker
            # Move worker to the separate thread
            self.worker.moveToThread(self.worker_thread)
            self.worker.arduino_data_channel_signal.connect(
                self.forward_arduino_data)  # Connect worker signal to forwarding slot
            # Start reading from Arduino when thread starts
            self.worker_thread.started.connect(self.worker.read_arduino)
            self.worker_thread.start()  # Start the worker thread

            self.write_timer = QTimer()  # Timer to periodically handle data writing
            # Connect timer to data handling function
            self.write_timer.timeout.connect(self.worker.handle_data)
            # Start the timer with a 100ms interval
            self.write_timer.start(100)

        logger.info("Arduino thread ready!")

    # Function to initialize the serial port
    def __initialize_serial(self):
        port_filter = None
        available_ports = self.__list_ports()  # List available ports

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
            logger.debug(f"Available ports: {filtered_ports}")
            # Initialize serial connection
            self.__serial = serial.Serial(
                port=port, baudrate=9600, timeout=.1, dsrdtr=True)
            logger.debug(f"Serial: {self.__serial}")

    # Function to list available serial ports
    def __list_ports(self):
        return [port.device for port in list(ports.comports())]

    # Function to stop the worker and thread
    def stop(self):
        if self.worker:
            self.worker.running = False  # Stop the worker loop
        self.worker_thread.quit()  # Quit the worker thread
        self.worker_thread.wait()  # Wait for the thread to finish
        self.write_timer.stop()  # Stop the timer
        self._run_flag = False
        self.wait()  # Wait for the thread to finish

    # Handles data to be sent to Arduino
    def handle_data(self, data):
        self.queue.put(data)  # Add data to queue for processing

    # Slot to forward data read from Arduino to the main application
    @pyqtSlot(dict)
    def forward_arduino_data(self, data):
        logger.debug(f"Forwarding data to main thread: {data}")
        self.arduino_data_channel_signal.emit(
            data)  # Emit the signal with the data
