"""
@file bluetooth_sensor_data.py
@brief Module for collecting data from BLE SEN55 and Connected_Wood_Plank sensors.

This module handles the discovery, collection, and recording of data
from BLE SEN55 and Connected_Wood_Plank sensors.

@author [Your Name]
@date [Current Date]
@version 1.0
"""

from bleak import BleakScanner
import asyncio
import struct
import time
import pandas as pd
import config.configuration as Conf
import os
import logging
from pathlib import Path
import threading

Main_path = Path(__file__).parents[0]
# Logging configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class ConnectedBluetoothDeviceError(Exception):
    """Custom exception class for ConnectedBluetoothDevice"""
    pass

class ConnectedBluetoothDevice:
    """
    @class ConnectedBluetoothDevice
    @brief Main class for handling Bluetooth device connections and data collection.
    """
    def __init__(self, wifi_transmitter):
        """
        @brief Initialize the ConnectedBluetoothDevice object.
        @exception ConnectedBluetoothDeviceError If initialization fails.
        """
        try:
            self.ConfigClass = Conf.Config()
            self.config = self.ConfigClass.config
            self.wifi_transmitter = wifi_transmitter

            self.instance_id = 1

            self.stop_flag = False
            
            self.running = threading.Event()
            self.thread = None 
            self.latest_successful_read = time.time()
            
            self.SEN55_ports = self.ConfigClass.get_device_ports("SEN55")
            self.SEN55_mac_adress = None
            
            self.current_time = time.strftime("%Y-%m-%d %H:%M:%S")
            self.DIRECTORY = self.config['directories']['csv']
            self.SEN55_filename = self.config['filenames']['SEN55']
            # self.SEN55_path = os.path.join(Main_path,self.DIRECTORY, self.config['filenames']['SEN55'])
            self.SEN55_path = Main_path / self.DIRECTORY / self.SEN55_filename
            # self.CWP_SG_path = os.path.join(Main_path,self.DIRECTORY, self.config['filenames']['CWP_SG'])
            self.CWP_SG_path = Main_path / self.DIRECTORY / self.config['filenames']['CWP_SG']
            #self.CWP_Capa_path = os.path.join(Main_path,self.DIRECTORY, self.config['filenames']['CWP_Capa'])
            self.CWP_Capa_path = Main_path / self.DIRECTORY / self.config['filenames']['CWP_Capa']
            self.CWP_Piezos_path = Main_path / self.DIRECTORY / self.config['filenames']['CWP_Piezos']
            #self.CWP_Piezos_path = os.path.join(Main_path,self.DIRECTORY, self.config['filenames']['CWP_Piezos'])

            self.SEN55_data = []
            self.CWP_SG_data = []
            self.CWP_Capa_data = []
            self.CWP_Piezos_data = []
            self.start_time_mini_session = 0
            self.end_time_mini_session = 0
            self.nb_readings_SG = 1
            self.nb_readings_Capa = 1
            self.nb_readings_Piezo = 1

            self.time_increment = 1
        except Exception as e:
            logging.error(f"Erreur lors de l'initialisation: {str(e)}")
            raise ConnectedBluetoothDeviceError("Erreur d'initialisation")
        
    def get_latest_data(self):
        latest_data = {
            "SEN55": self.SEN55_data[-1] if self.SEN55_data else None,
            "CWP_SG": self.CWP_SG_data[-1] if self.CWP_SG_data else None,
            "CWP_Capa": self.CWP_Capa_data[-1] if self.CWP_Capa_data else None,
            "CWP_Piezos": self.CWP_Piezos_data[-1] if self.CWP_Piezos_data else None
        }
        return latest_data
    
    def get_SEN55_mac_adresses(self):
        """
        @brief Retrieves the MAC address for the SEN55 device based on the instance ID.

        This method attempts to fetch the MAC address for the SEN55 device using the instance ID.
        If the instance ID is 0, it raises a ConnectedBluetoothDeviceError indicating an invalid instance ID.
        Otherwise, it assigns the corresponding MAC address from the SEN55_ports list to the SEN55_mac_adress attribute.

        @exception ConnectedBluetoothDeviceError Raised when the instance ID is 0 or when there is an error fetching the MAC address.
        @exception Exception Logs any other exceptions that occur during the process.

        @note Ensure that the instance ID is set correctly before calling this method.

        @return None
        """
        try:
            if self.instance_id == 0:
                raise ConnectedBluetoothDeviceError("Instance Id = 0, trying to catch value from SEN55_mac_adress < 0 ")
            self.SEN55_mac_adress = self.SEN55_ports[self.instance_id - 1]
        except Exception as e:
            logging.error(f"Error while getting MAC addresses: {str(e)}")
            raise ConnectedBluetoothDeviceError("Error getting MAC addresses")
        
    def start_recording(self):
        """
        @brief Starts the recording process by initiating a thread to listen for SEN55 devices.
        
        This method checks if the recording process is not already running. If it is not, it sets the running flag,
        creates a new thread to run the `run_listen_for_sen55` method, and starts the thread. Logs an info message
        indicating that the listening process has started. If an exception occurs, it logs an error message with the
        exception details.
        
        @exception Logs an error message if an exception occurs while starting the listening process.
        """
        try:
            if not self.running.is_set():
                self.running.set()
                self.thread = threading.Thread(target=self.run_listen_for_sen55)
                self.thread.start()
                logging.info("Started listening for devices.")
        except Exception as e : 
            logging.error(f"Error while starting to listen for devices: {str(e)}")
            
    def stop_recording(self):
        """
        @brief Stops the recording process for the connected Bluetooth device.

        This method attempts to stop the recording process by performing the following steps:
        1. Checks if the recording is currently running.
        2. Saves the sensor data to a CSV file.
        3. Clears the running flag to indicate that recording has stopped.
        4. Joins the recording thread with a timeout of 5 seconds to ensure it has stopped.

        @exception Logs an error message if an exception occurs while stopping the recording process.
        """
        try:
            if self.running.is_set():
                self.sen55_data_to_csv()
                logging.info("Data saved to CSV.")
                self.running.clear()
                if self.thread:
                    self.thread.join(timeout=5)
                    logging.info("Stopped listening for devices.")
        except Exception as e : 
            logging.error(f"Error while stopping to listen for devices: {str(e)}")
        
    async def listen_for_sen55(self):
        if time.time() - self.latest_successful_read > 7:
            logging.info("No data received for 7 seconds. Stopping...")
            self.stop_recording()
            
        while self.running.is_set():

            try:
                available_devices = {device['device']: device for device in self.config['devices']}
                logging.info("Starting to listen...")

                async def detection_callback(device, advertising_data):
                    if device.name in available_devices:
                        if self.ConfigClass.get_status(device.name):
                            manufacturer_data = advertising_data.manufacturer_data
                            if manufacturer_data:
                                for _, data in manufacturer_data.items():
                                    logging.info(f"Data received from {device.name},{data}")
                                    data_size = self.ConfigClass.get_values(device.name)
                                    if len(data) >= data_size:
                                        values = struct.unpack(self.ConfigClass.get_values_string(device.name), data[:data_size])
                                        logging.debug(', '.join(str(value) for value in values))

                                        if device.name == "Connected_Wood_Plank":
                                            self.latest_successful_read = time.time()
                                            self.CWP_data_to_array(values)
                                        elif device.name == "SEN55":
                                            self.latest_successful_read = time.time()
                                            self.SEN55_data_to_array(values)
                                            
                                        if self.wifi_transmitter:
                                            latest_data = self.get_latest_data()
                                            self.wifi_transmitter.update(latest_data)

                scanner = BleakScanner(detection_callback=detection_callback)
                await scanner.start()
                await asyncio.sleep(20)  # Run for 20 seconds
                await scanner.stop()

            except Exception as e:
                logging.error(f"Error while listening for devices: {str(e)}")
                raise ConnectedBluetoothDeviceError("Error listening for devices")

    # Méthode pour exécuter la fonction asynchrone
    def run_listen_for_sen55(self):
        """
        @brief Runs the asynchronous method listen_for_sen55 using asyncio.run.
        
        This method is responsible for starting the listening process for the SEN55 sensor data.
        It uses the asyncio.run function to execute the listen_for_sen55 coroutine.
        
        @note This method blocks until listen_for_sen55 completes.
        """
        asyncio.run(self.listen_for_sen55())
    
    def SEN55_data_to_array(self, values):
        """
        @brief Process and store SEN55 sensor data.
        @param values The sensor values to process.
        @exception ConnectedBluetoothDeviceError If SEN55 data processing fails.
        """
        try:
            self.SEN55_data.append({
                "time": self.current_time,
                "Pm1p0": values[0],
                "Pm2p5": values[1],
                "Pm10": values[2],
                "Temperature": values[3],
                "Humidity": values[4],
                "Temp": values[5],
                "VOC": values[6]
            })
        except IndexError as e:
            logging.error(f"Erreur lors de l'ajout des données SEN55: {str(e)}")
            raise ConnectedBluetoothDeviceError("Données SEN55 invalides")

    def sen55_data_to_csv(self):
        """
        @brief Write SEN55 data to CSV file.
        @exception ConnectedBluetoothDeviceError If CSV writing fails.
        """
        try:
            df = pd.DataFrame(self.SEN55_data)
            base_filename = self.SEN55_filename[:-4]
            sensor_amount = self.ConfigClass.get_sensor_amount("SEN55")

            if sensor_amount > 1:
                new_filename = f"{base_filename}_{self.instance_id}.csv"
            else:
                new_filename = self.SEN55_filename

            new_filepath = Main_path / self.DIRECTORY / new_filename

            # Vérifier si le fichier existe déjà pour déterminer si nous devons inclure l'en-tête
            file_exists = os.path.isfile(new_filepath)
            print(new_filepath)

            df.to_csv(new_filepath, mode="a", header=not file_exists, index=False)
            logging.info(f"Données SEN55 enregistrées dans {new_filename}")
            self.SEN55_data.clear()  # Nettoyer les données après l'écriture
        except Exception as e:
            logging.error(f"Erreur lors de l'écriture des données SEN55 dans le CSV: {str(e)}")
            raise ConnectedBluetoothDeviceError("Erreur d'écriture CSV SEN55")

    def CWP_data_to_array(self, values):
        """
        @brief Process and store Connected_Wood_Plank sensor data.
        @param values The sensor values to process.
        @exception ConnectedBluetoothDeviceError If CWP data processing fails.
        """
        try:
            sensor_id = values[-1]

            if sensor_id == 55:
                self.nb_readings_Piezo = max(((values[1] << 8) | values[2]), 1)
                self.nb_readings_Capa = max(((values[3] << 8) | values[4]), 1)
                self.nb_readings_SG = max(values[0], 1)
            elif sensor_id in [15, 45]:
                time_value = ((values[12] << 24) | (values[13] << 16) | (values[14] << 8) | values[15])
                if sensor_id == 15:
                    self.start_time_mini_session = time_value
                else:
                    self.end_time_mini_session = time_value
                logging.info(f"{'Start' if sensor_id == 15 else 'End'} time: {time_value}")

                for i in range(3):
                    if not self.CWP_SG_data:
                        time = self.start_time_mini_session / 1000
                    else:
                        time = round((self.CWP_SG_data[-1]['Time'] +
                                      ((abs(self.end_time_mini_session - self.start_time_mini_session) / 1000) /
                                       self.nb_readings_SG)), 1)

                    start_idx = i * 4
                    capteur_values = values[start_idx:start_idx + 4]

                    data_dict = {
                        "Time": time,
                        "Strain_Gauge_1": capteur_values[0],
                        "Strain_Gauge_2": capteur_values[1],
                        "Strain_Gauge_3": capteur_values[2],
                        "Strain_Gauge_4": capteur_values[3],
                    }
                    self.CWP_SG_data.append(data_dict)
            elif sensor_id == 25:
                for i in range(4):
                    if not self.CWP_Piezos_data:
                        time = self.start_time_mini_session
                    else:
                        time = int(self.CWP_Piezos_data[-1]['Time'] +
                                   ((abs(self.end_time_mini_session - self.start_time_mini_session)) /
                                    self.nb_readings_Piezo))
                    start_idx = i * 4
                    capteur_values = values[start_idx:start_idx + 4]
                    data_dict = {
                        "Time": time,
                        "Piezo_1": capteur_values[0],
                        "Piezo_2": capteur_values[1],
                        "Piezo_3": capteur_values[2],
                        "Piezo_4": capteur_values[3],
                    }
                    self.CWP_Piezos_data.append(data_dict)
            elif sensor_id == 35:
                if not self.CWP_Capa_data:
                    time = self.start_time_mini_session / 1000
                else:
                    time = round((self.CWP_Capa_data[-1]['Time'] +
                                  ((abs(self.end_time_mini_session - self.start_time_mini_session) / 1000) /
                                   self.nb_readings_Capa)), 1)
                data_dict = {"Time": time}
                for i in range(16):
                    data_dict[f"Capa{i+1}"] = values[i]
                self.CWP_Capa_data.append(data_dict)
            else:
                logging.warning(f"ID de capteur non reconnu: {sensor_id}")
        except Exception as e:
            logging.error(f"Erreur lors du traitement des données CWP: {str(e)}")
            raise ConnectedBluetoothDeviceError("Erreur de traitement des données CWP")

    def CWP_data_to_csv(self):
        """
        @brief Write Connected_Wood_Plank data to CSV files.
        @exception ConnectedBluetoothDeviceError If CSV writing fails.
        """
        try:
            sensor_amount = self.ConfigClass.get_sensor_amount("Connected_Wood_Plank")

            for data, base_filename in [
                (self.CWP_Capa_data, "CWP_Capa_data"),
                (self.CWP_Piezos_data, "CWP_Piezos_data"),
                (self.CWP_SG_data, "CWP_SG_data")
            ]:
                if data:
                    df = pd.DataFrame(data)

                    if sensor_amount > 1:
                        new_filename = f"{base_filename}_{self.instance_id}.csv"
                    else:
                        new_filename = f"{base_filename}.csv"

                    new_path = Main_path / self.DIRECTORY / new_filename
                    df.to_csv(new_path, mode="w", header=True, index=False)
                    logging.info(f"Données {base_filename} enregistrées dans {new_filename}")
                    data.clear()

            if not any([self.CWP_Capa_data, self.CWP_Piezos_data, self.CWP_SG_data]):
                logging.info("Aucune donnée CWP à enregistrer.")
        except Exception as e:
            logging.error(f"Erreur lors de l'écriture des données CWP dans le CSV: {str(e)}")
            raise ConnectedBluetoothDeviceError("Erreur d'écriture CSV CWP")
        
    def __del__(self):
        """
        @brief Destructor method for the ConnectedBluetoothDevice class.
        
        This method is called when the instance is about to be destroyed. It ensures that the recording is stopped before the object is deleted.
        
        @note This method relies on the stop_recording method to properly release resources.
        """
        self.stop_recording()

if __name__ == "__main__":
   device = ConnectedBluetoothDevice(None)