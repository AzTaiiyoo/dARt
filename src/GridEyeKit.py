import sys
from webbrowser import Error

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
    pass

class ConnectionError(GridEYEError):
    pass

class DataReadError(GridEYEError):
    pass

class GridEYEKit:
    def __init__(self, port):
        self.port = port
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

    def connect(self):
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
        if not self.ser or not self.ser.is_open:
            self.connection_error = True
            logging.error("Serial port is not open")
            return False  
        
        if time.time() - self.last_successful_read > 5:
            self.connection_error = True
            logging.error("No data received for 5 seconds")
            return False  
        
        return True

    def get_data(self):
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

    def _process_data(self, data):
        tarr = np.zeros((8, 8))
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

    def serial_readline(self, eol='***', bytes_timeout=300):
        length = len(eol)
        line = bytearray()

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
    
    def start_recording(self):
        if not self.is_connected:
            self.connection_error = True
            raise ConnectionError("Device is not connected")
        
        self.is_recording = True
        self.stop_thread.clear()
        self.data_thread = threading.Thread(target=self.update_data)
        self.data_thread.start()
        logging.info("Started recording GridEYE data")

    def stop_recording(self):
        self.is_recording = False
        if self.data_thread:
            self.stop_thread.set()
            self.data_thread.join()
        if self.is_connected:
            self.disconnect()
        logging.info("Stopped recording GridEYE data")

    def update_data(self):
        while not self.stop_thread.is_set() and self.is_recording:
            if not self.check_connection():
                time.sleep(1)  
                continue

            try:
                data = self.get_data()
                if data:
                    self.data_records.append(data)
                time.sleep(0.1)  
            except Exception as e:
                logging.error(f"Error collecting data: {e}")
                self.connection_error = True
                time.sleep(1)  
            
    def send_data_to_csv(self):
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
                
            new_filepath = os.path.join(self.csv_directory, new_filename)
            df.to_csv(new_filepath, index=False)
            print(f"Data saved to {new_filename}")
            self.data_records.clear()
        except IOError as e:
            print(f"Error writing data to CSV file: {e}")
            print(self.csv_directory, new_filepath)
            
            
    def run_session(self):
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

