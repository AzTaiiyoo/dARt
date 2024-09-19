import sys
#print("Python version:", sys.version)
#print("Python path:", sys.path)

import serial
#print("Serial version:", serial.__version__)
#print("Serial path:", serial.__file__)
#print("Serial contents:", dir(serial))

from serial import Serial, SerialException

# Le reste des imports
import struct
import numpy as np
import threading
from queue import Queue
import glob
from time import sleep
from datetime import datetime
import pandas as pd
import config.configuration as Conf
import os
import logging
from pathlib import Path

# Logging configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
Main_path = Path(__file__).parents[0]

class GridEYEError(Exception):
    """Base exception for GridEYE errors."""
    pass

class ConnectionError(GridEYEError):
    """Exception raised for connection errors."""
    pass

class DataReadError(GridEYEError):
    """Exception raised for data reading errors."""
    pass

class GridEYEKit:
    """
    @brief Main class for interacting with the Grid-EYE sensor.
    """

    def __init__(self, port):
        """
        @brief Initialize the GridEYEKit instance.
        @param port The serial port to connect to the Grid-EYE sensor.
        @throws ConnectionError If unable to initialize the serial port.
        """
        self.instance_id = 1 
        
        self._connected = False
        self.stop_flag = False
        
        self.ConfigClass = Conf.Config()
        self.config = self.ConfigClass.config
        self.port = port
        self.csv_directory = self.config["directories"]["csv"]
        self.csv_filename = self.config["filenames"]["Grideye"]
        self.csv_path = os.path.join(Main_path,self.csv_directory, self.csv_filename)

        try:
            self.ser = Serial(
                port=self.port,
                baudrate=9600,
                timeout=0.5,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                bytesize=serial.EIGHTBITS
            )
        except serial.SerialException as e:
            raise ConnectionError(f"Error initializing serial port: {e}")

        self.tarr_queue = Queue(1)
        self.thermistor_queue = Queue(1)
        self.multiplier_tarr = 0.25
        self.multiplier_th = 0.0125
        self._error = 0

        self.data_records = []
        self.running = False
        self.recording_thread = None
        self.lock = threading.Lock()

        if not self.connect():
            raise ConnectionError("Unable to connect to Eval Kit")
        threading.Thread(target=self._connected_thread).start()

    def connect(self):
        """
        @brief Attempt to connect to the Grid-EYE sensor.
        @return bool True if connection is successful, False otherwise.
        @throws ConnectionError If unable to open the serial port.
        """
        if self.ser.isOpen():
            self.ser.close()

        try:
            self._list_serial_ports()
        except EnvironmentError as e:
            raise ConnectionError(f"Error listing serial ports: {e}")

        try:
            self.ser = serial.Serial(port=self.port, baudrate=9600, timeout=0.5)
            for _ in range(5):
                if self.serial_readline(bytes_timeout=300):
                    self._connected = True
                    return True
        except serial.SerialException as e:
            raise ConnectionError(f"Error opening port {self.port}: {e}")

        self._connected = False
        return False

    def _list_serial_ports(self):
        """
        @brief List available serial ports.
        @return list List of available serial ports.
        @throws EnvironmentError If the platform is not supported.
        """
        if sys.platform.startswith('win'):
            ports = ['COM' + str(i + 1) for i in range(256)]
        elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
            ports = glob.glob('/dev/tty[A-Za-z]*')
        elif sys.platform.startswith('darwin'):
            ports = glob.glob('/dev/tty.*')
        else:
            raise EnvironmentError('Unsupported platform')

        result = []
        for port in ports:
            try:
                s = serial.Serial(port)
                s.close()
                result.append(port)
            except (OSError, serial.SerialException):
                pass
        return result

    def _get_GridEye_data(self):
        """
        @brief Retrieve data from the Grid-EYE sensor.
        @return tuple (thermistor, tarr) where thermistor is the thermistor temperature
                and tarr is an 8x8 numpy array of temperatures.
        @throws DataReadError If there's an error reading or decoding the data.
        """
        if self.stop_flag:
            return None, None

        tarr = np.zeros((8, 8))
        thermistor = 0
        try:
            data = self.serial_readline()
            if len(data) >= 135:
                self._error = 0
                if data[1] & 0b00001000 != 0:
                    data[1] &= 0b00000111
                    thermistor = -struct.unpack('<h', data[0:2])[0] * self.multiplier_th
                else:
                    thermistor = struct.unpack('<h', data[0:2])[0] * self.multiplier_th

                for i in range(2, 130, 2):
                    raw_temp = data[i:i+2]
                    temp_value = struct.unpack('<h', raw_temp)[0]
                    temperature = temp_value * self.multiplier_tarr

                    row = (i - 2) // 16
                    col = ((i - 2) // 2) % 8
                    tarr[row, col] = temperature
            else:
                self._error += 1
                raise DataReadError("Incomplete data received")
        except serial.SerialException as e:
            raise DataReadError(f"Serial read error: {e}")
        except struct.error as e:
            raise DataReadError(f"Data decoding error: {e}")

        return thermistor, tarr

    def _connected_thread(self):
        """
        @brief Background thread for continuous sensor data reading.
        """
        while True:
            if self._connected:
                try:
                    data = self._get_GridEye_data()
                    if self.tarr_queue.full():
                        self.tarr_queue.get()
                    self.tarr_queue.put(data[1])

                    if self.thermistor_queue.full():
                        self.thermistor_queue.get()
                    self.thermistor_queue.put(data[0])

                    if self._error > 5:
                        raise ConnectionError("Too many consecutive errors, disconnecting")
                except (DataReadError, ConnectionError) as e:
                    logging.error(f"Error in connection thread: {e}")
                    self._connected = False
                    self._error = 0

    def get_thermistor(self):
        """
        @brief Retrieve the thermistor temperature.
        @return float Thermistor temperature.
        @throws DataReadError If there's a timeout reading the thermistor data.
        """
        try:
            return self.thermistor_queue.get(True, 1)
        except Queue.Empty:
            raise DataReadError("Timeout reading thermistor")

    def get_temperatures(self):
        """
        @brief Retrieve the temperature array.
        @return numpy.ndarray 8x8 array of temperatures.
        @throws DataReadError If there's a timeout reading the temperature data.
        """
        try:
            return self.tarr_queue.get(True, 1)
        except Queue.Empty:
            raise DataReadError("Timeout reading temperatures")

    def get_raw(self):
        """
        @brief Retrieve raw sensor data.
        @return bytes Raw sensor data.
        @throws DataReadError If there's an error reading the raw data.
        """
        try:
            return self.serial_readline()
        except serial.SerialException as e:
            raise DataReadError(f"Error reading raw data: {e}")

    def close(self):
        """
        @brief Close the connection to the sensor.
        """
        self._connected = False
        try:
            self.ser.close()
        except serial.SerialException as e:
            logging.error(f"Error closing serial port: {e}")

    def serial_readline(self, eol='***', bytes_timeout=300):
        """
        @brief Read a line of serial data up to a specified end-of-line character.
        @param eol End-of-line character(s).
        @param bytes_timeout Maximum number of bytes to read before timeout.
        @return bytearray Data read.
        @throws DataReadError If there's an error reading from the serial port.
        """
        length = len(eol)
        line = bytearray()

        try:
            while True:
                c = self.ser.read(1)
                if c:
                    line += c
                    if line[-length:] == eol.encode():
                        break
                    if len(line) > bytes_timeout:
                        return line
                else:
                    break
        except serial.SerialException as e:
            raise DataReadError(f"Serial read error: {e}")

        return line

    def start_recording(self):
        """
        @brief Start recording data.
        """
        self.running = True
        if self.config['active_preset']['value'] == "default":
            interval = 1
        else:
            interval = self.config[f"{self.config['active_preset']['value']}"]["Grideye_speed"]
        self.recording_thread = threading.Thread(target=self.record_data, args=(interval,))
        self.recording_thread.start()

    def stop_recording(self):
        """
        @brief Stop recording data and save it.
        """
        self.running = False
        if self.recording_thread:
            self.recording_thread.join()
        self.sendDataToCSV()

    def record_data(self, interval):
        """
        @brief Record sensor data at regular intervals.
        @param interval Interval between each recording in seconds.
        """
        while self.running:
            with self.lock:
                try:
                    thermistor, tarr = self._get_GridEye_data()
                    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    record = {
                        'timestamp': timestamp,
                        'thermistor': thermistor,
                        'temperatures': tarr.flatten().tolist()
                    }
                    self.data_records.append(record)
                    logging.info(f"Recorded data at {timestamp}: {record}")
                except (DataReadError, ConnectionError) as e:
                    logging.error(f"Error recording data: {e}")
            sleep(float(interval))

    def sendDataToCSV(self):
        """
        @brief Send recorded data to a CSV file.
        """
        print("Entering sendDataToCSV function")
        if not self.data_records:
            return

        records = []
        for record in self.data_records:
            row = {'timestamp': record['timestamp'], 'thermistor': record['thermistor']}
            for i, temp in enumerate(record['temperatures']):
                row[f'temp-{i+1}'] = temp
            records.append(row)

        df = pd.DataFrame(records)
        try:
            base_filename = self.csv_filename[:-4]
            sensor_amount = self.ConfigClass.get_sensor_amount("Grideye")

            if sensor_amount > 1:
                new_filename = f"{base_filename}_{self.instance_id}.csv"
            else:
                new_filename = self.csv_filename

            new_filepath = os.path.join(self.csv_directory, new_filename)
            df.to_csv(new_filepath, index=False)
            print(f"Data saved to {new_filename}")
        except IOError as e:
            print(f"Error writing data to CSV file: {e}")
            
if __name__ == "__main__":
    try:
        port = "/dev/tty.usbmodem11101"  # This should be replaced with the actual port
        grid_eye = GridEYEKit(port)
        grid_eye.start_recording()
    except Exception as e:
        logging.error(f"Error initializing Grid-EYE sensor: {e}")
        raise GridEYEError("Init Error")