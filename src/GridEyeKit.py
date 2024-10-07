import sys
from webbrowser import Error
import serial
from serial import Serial, SerialException
import struct
import numpy as np
import threading
from queue import Queue
import glob
import time 
from datetime import datetime
import pandas as pd
import config.configuration as Conf
import os
import logging
from pathlib import Path
import threading

sys.path.append(str(Path(__file__).parent))
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
Main_path = Path(__file__).parents[0]

class GridEYEError(Exception):
    """
    @brief Base exception for the Grideye.
    """
    pass

class ConnectionError(GridEYEError):
    """
    @brief Exception raised for connection errors.
    """
    pass

class DataReadError(GridEYEError):
    """
    @brief Exception for data reading errors.
    """
    pass

class GridEYEKit:
    """
    @brief Main class to manage the GridEYE kit.
    
    This class handles the connection, data reading, and recording
    of data from the GridEYE sensor.
    """

    def __init__(self, port, wifi_transmitter):
        """
        @brief Initializes an instance of GridEYEKit.
        @param port The serial port to use for the connection.
        @param wifi_transmitter The WiFi transmission object to use.
        """
        try:
            self.port = port
            self.wifi_transmitter = wifi_transmitter
            
            self.configClass = Conf.Config()
            self.config = self.configClass.config
            
            self.csv_directory = Main_path / self.config["directories"]["csv"]
            self.csv_filename = self.config["filenames"]["Grideye"]
            self.csv_path = self.csv_directory / self.csv_filename

            self.ser = None
            self.data_records = []
            self.multiplier_tarr = 0.25
            self.multiplier_th = 0.0125
            
            self.instance_id = 1
            
            self.is_connected = False
            self.connection_error = False
            self.last_successful_read = time.time()

            self.data_thread = None
            self.stop_thread = threading.Event()
        except Exception as e: 
            logging.error(f"Error initializing GridEYEKit: {e}")
            raise GridEYEError("Failed to initialize GridEYEKit")

    def connect(self):
        """
        @brief Establishes a serial connection with the device.
        @return bool True if the connection succeeds, False otherwise.
        """
        try:
            self.ser = serial.Serial(
                port=self.port,
                baudrate=9600,
                timeout=0.5,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                bytesize=serial.EIGHTBITS
            )
            logging.info(f"Connected to port {self.port}")
            self.is_connected = True
            return True
        except serial.SerialException as e:
            logging.error(f"Error connecting to port {self.port}: {e}")
            self.connection_error = True
            return False

    def disconnect(self):
        """
        @brief Disconnects the device and saves the data.
        @return bool True if the disconnection succeeds, False otherwise.
        """
        try:
            if self.is_connected:
                self.send_data_to_csv()
                if self.ser and self.ser.is_open:
                    self.ser.flush()
                    self.ser.close()
                    self.is_connected = False
                logging.info("Disconnected from serial port")
                return True
            else :
                logging.info("Already disconnected")
                self.connection_error = True
                return False
        except (serial.SerialException, Exception) as e:
            self.connection_error = True
            logging.error(f"Error disconnecting from port {self.port}: {e}") if SerialException else logging.error(f"Error disconnecting: {e}")
            return False

    def check_connection(self):
        """
        @brief Checks the connection status.
        @return bool True if the connection is active, False otherwise.
        """
        try:
            if not self.ser or not self.ser.is_open:
                self.connection_error = True
                logging.error("Serial port is not open")
                return False  
            
            if time.time() - self.last_successful_read > 5:
                self.connection_error = True
                logging.error("No data received for 5 seconds")
                return False  
        except serial.SerialException as e:
            self.connection_error = True
            logging.error(f"Serial port error: {e}")
            return False
        
        return True

    def get_data(self):
        """
        @brief Reads and processes data from the sensor.
        @return dict A dictionary containing the processed data or None in case of error.
        """
        if not self.check_connection():
            return None
        
        try:
            data = self.serial_readline()
            if len(data) >= 135:
                self.last_successful_read = time.time()
                self.connection_error = False
                thermistor, tarr = self._process_data(data)
                return {
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'thermistor': thermistor,
                    'temperatures': tarr.flatten().tolist()
                }
            else:
                logging.warning(f"Incomplete data received: {len(data)} bytes")
                return None
        except serial.SerialException as e:
            self.connection_error = True
            logging.error(f"Serial read error: {e}")
            return None
        except struct.error as e:
            logging.error(f"Data decoding error: {e}")
            return None
    
    def get_latest_data(self):
        """
        @brief Retrieves the latest recorded data.
        @return dict The latest recorded data or None if no data is available.
        """
        try:
            if self.data_records:
                logging.info (f"Latest data: {self.data_records[-1]}")
                return self.data_records[-1]
            return None 
        except Exception as e:
            logging.error(f"Error getting latest data: {e}")

    def _process_data(self, data):
        """
        @brief Processes raw sensor data.
        @param data The raw data to process.
        @return tuple A tuple containing the thermistor value and a temperature array.
        """
        tarr = np.zeros((8, 8))
        try : 
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

            return thermistor, tarr
        except Exception as e:
            logging.error(f"Error processing data: {e}")
            return None, None

    def serial_readline(self, eol='***', bytes_timeout=300):
        """
        @brief Reads a line of data from the serial port.
        @param eol The end-of-line marker.
        @param bytes_timeout The maximum number of bytes to read before timeout.
        @return bytearray The read data.
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

            return line
        except serial.SerialException as e:
            logging.error(f"Serial read error: {e}")
            return line
    
    def start_recording(self):
        """
        @brief Starts recording data.
        @throws ConnectionError if the device is not connected.
        """
        try:
            if not self.is_connected:
                self.connection_error = True
                raise ConnectionError("Device is not connected")
            
            self.is_recording = True
            self.stop_thread.clear()
            self.data_thread = threading.Thread(target=self.update_data)
            self.data_thread.start()
            logging.info("Started recording GridEYE data")
        except ConnectionError as e:
            logging.error(f"Error starting recording: {e}")
            raise ConnectionError("Failed to start recording")
        
    def stop_recording(self):
        """
        @brief Stops recording data and disconnects the device.
        """
        self.is_recording = False
        if self.data_thread:
            self.stop_thread.set()
            self.data_thread.join()
        if self.is_connected:
            self.disconnect()
        logging.info("Stopped recording GridEYE data")

    def update_data(self):
        """
        @brief Method executed in a separate thread to continuously update data.
        """
        while not self.stop_thread.is_set() and self.is_recording:
            if not self.check_connection():
                time.sleep(1)  
                continue

            try:
                data = self.get_data()
                if data:
                    self.data_records.append(data)
                    if self.wifi_transmitter:
                        self.wifi_transmitter.update(self.get_latest_data())
                time.sleep(0.1)  
            except Exception as e:
                logging.error(f"Error collecting data: {e}")
                self.connection_error = True
                time.sleep(1)  
            
    def send_data_to_csv(self):
        """
        @brief Saves the collected data to a CSV file.
        """
        if not self.data_records:
            logging.warning("No data to save")
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
            sensor_amount = self.configClass.get_sensor_amount("Grideye")

            if sensor_amount > 1:
                new_filename = f"{base_filename}_{self.instance_id}.csv"
            else:
                new_filename = self.csv_filename
                
            new_filepath = self.csv_directory / new_filename
            df.to_csv(new_filepath, index=False)
            print(f"Data saved to {new_filename}")
            self.data_records.clear()
        except IOError as e:
            print(f"Error writing data to CSV file: {e}")
            print(self.csv_directory, new_filepath)
            
    def run_session(self):
        """
        @brief Executes a complete data recording session.
        @throws ConnectionError if the connection to the device fails.
        """
        if not self.connect():
            raise ConnectionError("Failed to connect to the device")

        try:
            self.start_recording()
            self.record_data()
        except KeyboardInterrupt:
            logging.info("Recording interrupted by user")
        finally:
            self.stop_recording()
            self.send_data_to_csv()
            self.disconnect()