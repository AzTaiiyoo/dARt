import asyncio
import struct
from bleak import BleakScanner, BleakClient
from datetime import datetime
import logging
from pathlib import Path
import threading 
import pandas as pd 

Main_Path = Path(__file__).parent.resolve()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

import config.configuration as Conf

class ConnectedWoodPlankError(Exception):
    """Custom exception class for ConnectedWoodPlank"""
    pass

class ConnectedWoodPlank:
    """
    @brief A class to manage and record data from a Connected Wood Plank device.
    
    This class handles the connection, data recording, and CSV export for a Connected Wood Plank device.
    It uses BLE (Bluetooth Low Energy) for communication and can handle multiple sensor types.
    """

    def __init__(self, instance_id, wifi_transmitter):
        """
        @brief Initialize the ConnectedWoodPlank object.
        @param instance_id An identifier for this specific instance of ConnectedWoodPlank.
        """
        try:
            self.ConfigClass = Conf.Config()
            self.config = self.ConfigClass.config
            
            self.NUM_CAPACITIVE = 16
            self.NUM_STRAIN = 4
            self.NUM_PIEZO = 4
            
            self.wifi_transmitter = wifi_transmitter
            self.instance_id = instance_id
            
            self.capacitive_data = {f"capacitive_{i}": [] for i in range(self.NUM_CAPACITIVE)}
            self.strain_data = {f"strain_{i}": [] for i in range(self.NUM_STRAIN)}
            self.piezo_data = {f"piezo_{i}": [] for i in range(self.NUM_PIEZO)}
            
            self.DIRECTORY = Main_Path / self.config['directories']['csv']
            
            self.get_connected_wood_plank_uuid()
            
            self.recording = False
            self.recording_thread = None
            self.stop_event = threading.Event()
            
        except Exception as e:
            logging.error(f"Error initializing ConnectedWoodPlank: {str(e)}")
            raise ConnectedWoodPlankError("CWP initialization error")

    def get_connected_wood_plank_uuid(self):
        """
        @brief Retrieve the UUIDs for the Connected Wood Plank device from the configuration.
        @throws ValueError if the device is not found in the configuration.
        """
        try:
            sensor_amount = self.ConfigClass.get_sensor_amount("Connected_Wood_Plank")
            
            target_device = "Connected_Wood_Plank"
            if sensor_amount > 1:
                target_device = f"Connected_Wood_Plank_{self.instance_id}"

            for device in self.config['uuid_services']:
                if device['device'].lower() == target_device.lower():
                    self.SERVICE_UUID = device['service_uuid']
                    self.CAPACITIVE_UUID = device['capacitive_uuid']
                    self.STRAIN_GAUGE_UUID = device['strain_gauge_uuid']
                    self.PIEZO_UUID = device['piezo_uuid']
                    return

            raise ValueError(f"Device '{target_device}' not found in the configuration")
        except Exception as e:
            logging.error(f"Error getting Connected Wood Plank UUIDs: {str(e)}")

    def parse_capacitive(self, sender, data):
        """
        @brief Parse incoming capacitive sensor data.
        @param sender The sender of the data.
        @param data The raw data received from the sensor.
        """
        try:
            if data[0] != ord('<') or data[-1] != ord('>'):
                logging.error("Invalid start/end symbols for capacitive data")
                return

            timestamp = datetime.now().isoformat()
            for i in range(self.NUM_CAPACITIVE):
                value = struct.unpack_from('<H', data, offset=1+i*2)[0]
                self.capacitive_data[f"capacitive_{i}"].append((timestamp, value))
            logging.info("Capacitive data received")
        except Exception as e:
            logging.error(f"Error parsing capacitive data: {str(e)}")

    def parse_strain_gauge(self, sender, data):
        """
        @brief Parse incoming strain gauge sensor data.
        @param sender The sender of the data.
        @param data The raw data received from the sensor.
        """
        try:
            if data[0] != ord('(') or data[-1] != ord(')'):
                logging.error("Invalid start/end symbols for strain gauge data")
                return

            timestamp = datetime.now().isoformat()
            for i in range(self.NUM_STRAIN):
                value = data[i+1]
                self.strain_data[f"strain_{i}"].append((timestamp, value))
            logging.info("Strain gauge data received")
        except Exception as e:
            logging.error(f"Error parsing strain gauge data: {str(e)}")

    def parse_piezo(self, sender, data):
        """
        @brief Parse incoming piezoelectric sensor data.
        @param sender The sender of the data.
        @param data The raw data received from the sensor.
        """
        try:
            if data[0] != ord('-') or data[1] != ord('>') or data[-2] != ord('<') or data[-1] != ord('-'):
                logging.error("Invalid start/end symbols for piezoelectric data")
                return

            timestamp = datetime.now().isoformat()
            for i in range(self.NUM_PIEZO):
                value = struct.unpack_from('>H', data, offset=2+i*2)[0]
                self.piezo_data[f"piezo_{i}"].append((timestamp, value))
            logging.info("Piezoelectric data received")
        except Exception as e:
            logging.error(f"Error parsing piezoelectric data: {str(e)}")

    async def run(self):
        """
        @brief Main asynchronous method to run the data collection process.
        
        This method finds the device, connects to it, and starts the notification process
        for all sensor types. It runs until the stop event is set.
        """
        try:
            device = await BleakScanner.find_device_by_filter(
                lambda d, ad: self.SERVICE_UUID.lower() in ad.service_uuids
            )

            if not device:
                logging.error(f"No device found with service UUID {self.SERVICE_UUID}")
                return

            logging.info(f"Device found: {device.name}")

            async with BleakClient(device) as client:
                logging.info(f"Connected to: {device.name}")

                await client.start_notify(self.CAPACITIVE_UUID, self.parse_capacitive)
                await client.start_notify(self.STRAIN_GAUGE_UUID, self.parse_strain_gauge)
                await client.start_notify(self.PIEZO_UUID, self.parse_piezo)

                logging.info("Notifications enabled, waiting for data...")
                
                while not self.stop_event.is_set():
                    await asyncio.sleep(1)

                await client.stop_notify(self.CAPACITIVE_UUID)
                await client.stop_notify(self.STRAIN_GAUGE_UUID)
                await client.stop_notify(self.PIEZO_UUID)
        except Exception as e:
            logging.error(f"Error in CWP data collection: {str(e)}")
            raise ConnectedWoodPlankError("CWP data collection error")

    def start_recording(self):
        """
        @brief Start the recording process.
        
        This method starts a new thread to run the asyncio loop for data collection.
        If recording is already in progress, it logs a warning.
        """
        try:
            if not self.recording:
                self.recording = True
                self.stop_event.clear()
                self.recording_thread = threading.Thread(target=self._run_asyncio_loop)
                self.recording_thread.start()
                logging.info("Recording started")
            else:
                logging.warning("Recording is already in progress")
        except Exception as e:
            logging.error(f"Error starting recording: {str(e)}")

    def stop_recording(self):
        """
        @brief Stop the recording process.
        
        This method stops the recording thread, joins it, and then calls the method
        to save the collected data to CSV files. If no recording is in progress,
        it logs a warning.
        """
        try:
            if self.recording:
                self.recording = False
                self.stop_event.set()
                self.recording_thread.join()
                self.recording_thread = None
                logging.info("Recording stopped")
                self.send_data_to_csv()
            else:
                logging.warning("No recording in progress")
        except Exception as e:
            logging.error(f"Error stopping recording: {str(e)}")
            
    def send_data_to_csv(self):
        """
        @brief Write the collected data to CSV files.
        
        This method creates separate CSV files for each type of sensor data
        (capacitive, piezo, and strain). The file names are based on the sensor type
        and include the instance_id if there are multiple sensors.
        
        @throws ConnectedWoodPlankError If there's an error writing to the CSV files.
        """
        try:
            sensor_amount = self.ConfigClass.get_sensor_amount("Connected_Wood_Plank")

            for data, base_filename in [
                (self.capacitive_data, "CWP_Capa_data"),
                (self.piezo_data, "CWP_Piezos_data"),
                (self.strain_data, "CWP_SG_data")
            ]:
                if data:
                    # Convert the dictionary to a DataFrame
                    df = pd.DataFrame({key: [value for _, value in values] for key, values in data.items()})
                    df['timestamp'] = [timestamp for timestamp, _ in list(data.values())[0]]

                    if sensor_amount > 1:
                        new_filename = f"{base_filename}_{self.instance_id}.csv"
                    else:
                        new_filename = f"{base_filename}.csv"

                    new_path = self.DIRECTORY / new_filename
                    df.to_csv(new_path, mode="w", header=True, index=False)
                    logging.info(f"Data {base_filename} saved in {new_filename}")
                    data.clear()

            if not any([self.capacitive_data, self.piezo_data, self.strain_data]):
                logging.info("No CWP data to save.")
        except Exception as e:
            logging.error(f"Error writing CWP data to CSV: {str(e)}")
            raise ConnectedWoodPlankError("CWP CSV writing error")

    def _run_asyncio_loop(self):
        """
        @brief Private method to run the asyncio loop.
        
        This method is called in a separate thread to run the asyncio event loop
        for the main data collection process.
        """
        asyncio.run(self.run())
    
# if __name__ == "__main__":
#     plank = ConnectedWoodPlank()
#     plank.asyncio.run(plank.run())

#     # Afficher un aperçu des données collectées
#     print("Données capacitives:", {k: len(v) for k, v in plank.capacitive_data.items()})
#     print("Données de jauge de contrainte:", {k: len(v) for k, v in plank.strain_data.items()})
#     print("Données piézoélectriques:", {k: len(v) for k, v in plank.piezo_data.items()})