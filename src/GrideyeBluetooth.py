import asyncio
from bleak import BleakClient
import struct
import numpy as np
from pathlib import Path
import logging
import threading
import pandas as pd
import time

Main_Path = Path(__file__).parent.resolve()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

import config.configuration as Conf

HEADER = bytes.fromhex("2a2a2a")  # Fixed header to look for

class GridEYEConfigError(Exception):
    """Exception raised for errors in the GridEYE configuration."""
    pass

class GridEYEConnectionError(Exception):
    """Exception raised for errors in the GridEYE BLE connection."""
    pass

class GridEYEDataProcessingError(Exception):
    """Exception raised for errors in processing GridEYE data."""
    pass

class GridEYEDataSavingError(Exception):
    """Exception raised for errors in saving GridEYE data."""
    pass

class GridEYEReader:
    """
    @brief A class for reading and processing data from a GridEYE sensor via Bluetooth Low Energy (BLE).
    
    This class manages the connection to a GridEYE sensor, reads temperature data,
    processes it, and saves it to a CSV file.
    """

    def __init__(self):
        """
        @brief Initialize the GridEYEReader object.
        
        Sets up configuration, Bluetooth settings, and initializes data structures.
        """
        self.ConfigClass = Conf.Config()
        self.config = self.ConfigClass.config
        
        self.init_bluetooth_config()
        
        self.csv_directory = Main_Path / self.config["directories"]["csv"]
        self.csv_filename = self.config["filenames"]["Grideye"]
        self.csv_path = self.csv_directory / self.csv_filename
        
        self.running = threading.Event()
        self.stop_event = asyncio.Event()
        self.thread = None
        
        self.buffer = bytearray() 
        self.temperatures = np.zeros((8, 8), dtype=np.float32)
        self.latest_successful_read = time.time()
        self.data_records = []
        self.instance_id = 1
        self.client = None

    def init_bluetooth_config(self):
        """
        @brief Initialize Bluetooth configuration for the GridEYE sensor.
        
        @throws GridEYEConfigError If there's an error in retrieving or setting up the Bluetooth configuration.
        """
        try:
            bluetooth_config = self.ConfigClass.get_service_uuid("Grideye")
            if bluetooth_config:
                self.DEVICE_ADDRESS = bluetooth_config['DEVICE_ADDRESS']
                self.SERVICE_UUID = bluetooth_config['SERVICE_UUID']
                self.CHARACTERISTIC_UUID = bluetooth_config['CHARACTERISTIC_UUID']
            else:
                raise GridEYEConfigError("Bluetooth configuration for GridEYE not found")
        except Exception as e:
            raise GridEYEConfigError(f"Error in Bluetooth configuration: {str(e)}")
            
    def start_recording(self):
        """
        @brief Start recording data from the GridEYE sensor.
        
        Initializes and starts a new thread for BLE communication if not already running.
        
        @throws GridEYEConnectionError If there's an error in starting the recording process.
        """
        try:
            if not self.running.is_set():
                self.running.set()
                self.stop_event.clear()
                self.thread = threading.Thread(target=self.run_ble_client_thread)
                self.thread.start()
                logging.info("Started GridEYE recording.")
        except Exception as e:
            raise GridEYEConnectionError(f"Error in starting GridEYE recording: {str(e)}")

    def stop_recording(self):
        """
        @brief Stop recording data from the GridEYE sensor.
        
        Stops the BLE communication thread and saves collected data to CSV.
        
        @throws GridEYEConnectionError If there's an error in stopping the recording process.
        """
        try:
            if self.running.is_set():
                self.running.clear()
                self.stop_event.set()
                if self.client:
                    asyncio.run_coroutine_threadsafe(self.client.disconnect(), asyncio.get_event_loop())
                if self.thread:
                    self.thread.join(timeout=10)
                self.send_data_to_csv()
                logging.info("Stopped GridEYE recording.")
        except Exception as e:
            raise GridEYEConnectionError(f"Error in stopping GridEYE recording: {str(e)}")

    async def run_ble_client(self):
        """
        @brief Asynchronous method to run the BLE client and handle data reception.
        
        Manages the BLE connection, data notification, and reconnection attempts.
        """
        def notification_handler(sender, data):
            self.process_data(data)
            self.latest_successful_read = time.time()

        while self.running.is_set() and not self.stop_event.is_set():
            try:
                async with BleakClient(self.DEVICE_ADDRESS, timeout=10) as client:
                    self.client = client
                    logging.info(f"Connected to {self.DEVICE_ADDRESS}")
                    await client.start_notify(self.CHARACTERISTIC_UUID, notification_handler)

                    while self.running.is_set() and not self.stop_event.is_set():
                        await asyncio.sleep(1)
                        if time.time() - self.latest_successful_read > 7:
                            logging.info("No data received for 7 seconds. Reconnecting...")
                            break

                    await client.stop_notify(self.CHARACTERISTIC_UUID)
            except asyncio.CancelledError:
                logging.info("BLE client task cancelled.")
                break
            except Exception as e:
                logging.error(f"Error in BLE connection: {e}")
                if not self.running.is_set() or self.stop_event.is_set():
                    break
                await asyncio.sleep(5)  # Wait before trying to reconnect

        logging.info("BLE client loop ended.")

    def run_ble_client_thread(self):
        """
        @brief Run the BLE client in a separate thread.
        
        Creates a new event loop for the BLE client to run asynchronously.
        """
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self.run_ble_client())
        finally:
            loop.close()
            
    def process_data(self, data):
        """
        @brief Process the received data from the GridEYE sensor.
        
        Parses the received data and extracts temperature frames.
        
        @param data The raw data received from the GridEYE sensor.
        @throws GridEYEDataProcessingError If there's an error in processing the data.
        """
        try:
            self.buffer.extend(data)
            while True:
                header_index = self.buffer.find(HEADER)
                if header_index == -1:
                    break

                frame_start = header_index + len(HEADER) + 2
                if len(self.buffer) - frame_start < 128:
                    break

                frame_data = self.buffer[frame_start:frame_start + 128]
                
                end_marker = self.buffer[frame_start + 128:frame_start + 130]
                if end_marker == bytes.fromhex("0d0a"):
                    self.parse_frame(frame_data)
                    self.add_data_record()

                self.buffer = self.buffer[frame_start + 128 + 2:]
        except Exception as e:
            raise GridEYEDataProcessingError(f"Error in processing GridEYE data: {str(e)}")

    def parse_frame(self, frame_data):
        """
        @brief Parse a single frame of temperature data.
        
        Converts raw frame data into a temperature matrix.
        
        @param frame_data The raw frame data to be parsed.
        """
        for i in range(8):
            for j in range(8):
                index = (i * 8 + j) * 2
                raw_temp = frame_data[index:index + 2]
                temp = struct.unpack('<h', raw_temp)[0]
                celsius_temp = temp * 0.25
                self.temperatures[i][j] = celsius_temp
        self.display_temperatures()

    def display_temperatures(self):
        """
        @brief Display the current temperature matrix for debugging purposes.
        
        Logs the temperature matrix and corner temperatures.
        """
        logging.debug("\nTemperatures (°C):")
        for i, row in enumerate(self.temperatures):
            logging.debug(f"Row {i}: " + " ".join(f"{temp:6.2f}" for temp in row))
        logging.debug("\nCorner temperatures:")
        logging.debug(f"Top-left: {self.temperatures[0, 0]:6.2f}  Top-right: {self.temperatures[0, 7]:6.2f}")
        logging.debug(f"Bottom-left: {self.temperatures[7, 0]:6.2f}  Bottom-right: {self.temperatures[7, 7]:6.2f}")

    def add_data_record(self):
        """
        @brief Add a new data record to the collection.
        
        Creates a record with current timestamp and temperature data.
        """
        record = {
            'timestamp': time.strftime("%Y-%m-%d %H:%M:%S"),
            'temperatures': self.temperatures.flatten().tolist()
        }
        self.data_records.append(record)

    def send_data_to_csv(self):
        """
        @brief Save collected data records to a CSV file.
        
        @throws GridEYEDataSavingError If there's an error in saving the data to CSV.
        """
        if not self.data_records:
            logging.warning("No data to save")
            return

        try:
            df = pd.DataFrame(self.data_records)
            base_filename = self.csv_filename[:-4]
            sensor_amount = self.ConfigClass.get_sensor_amount("Grideye")

            if sensor_amount > 1:
                new_filename = f"{base_filename}_{self.instance_id}.csv"
            else:
                new_filename = self.csv_filename
                
            new_filepath = self.csv_directory / new_filename
            df.to_csv(new_filepath, index=False)
            logging.info(f"Data saved to {new_filename}")
            self.data_records.clear()
        except Exception as e:
            raise GridEYEDataSavingError(f"Error in saving GridEYE data to CSV: {str(e)}")