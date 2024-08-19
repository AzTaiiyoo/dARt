"""
@file bluetooth_sensor_data.py
@brief Module for collecting data from BLE SEN55 and ConnectedWoodPlank sensors.

This module handles the discovery, collection, and recording of data
from BLE SEN55 and ConnectedWoodPlank sensors.

@author [Your Name]
@date [Current Date]
@version 1.0
"""

from bluepy.btle import Scanner, DefaultDelegate, BTLEException
import struct
import time
import pandas as pd
import config.configuration as Conf
import os
import logging

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

    def __init__(self):
        """
        @brief Initialize the ConnectedBluetoothDevice object.
        @exception ConnectedBluetoothDeviceError If initialization fails.
        """
        try:
            self.Config = Conf.Config()
            self.config = self.Config.config

            self.stop_flag = False
            self.current_time = time.strftime("%Y-%m-%d %H:%M:%S")

            self.DIRECTORY = self.config['directories']['csv']
            self.SEN55_filename = self.config['filenames']['SEN55']

            self.SEN55_path = os.path.join(self.DIRECTORY, self.config['filenames']['SEN55'])
            self.CWP_SG_path = os.path.join(self.DIRECTORY, self.config['filenames']['CWP_SG'])
            self.CWP_Capa_path = os.path.join(self.DIRECTORY, self.config['filenames']['CWP_Capa'])
            self.CWP_Piezos_path = os.path.join(self.DIRECTORY, self.config['filenames']['CWP_Piezos'])

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

    class ScanDelegate(DefaultDelegate):
        """
        @class ScanDelegate
        @brief Delegate class for handling Bluetooth device discovery events.
        """

        def __init__(self):
            """
            @brief Initialize the ScanDelegate object.
            """
            DefaultDelegate.__init__(self)

        def handleDiscovery(self, dev, isNewDev, isNewData):
            """
            @brief Handle the discovery of Bluetooth devices.
            @param dev The discovered device.
            @param isNewDev True if the device is newly discovered.
            @param isNewData True if new data is available for the device.
            """
            if isNewDev:
                logging.info(f"Nouvel appareil découvert: {dev.addr}")
            elif isNewData:
                logging.info(f"Nouvelles données reçues de {dev.addr}")

    def listen_for_sen55(self):
        """
        @brief Listen for BLE advertisements from SEN55 and wood sensors.
        @exception ConnectedBluetoothDeviceError If device listening fails.
        """
        try:
            available_devices = {device['name']: device for device in self.config['devices']}
            scanner = Scanner().withDelegate(self.ScanDelegate())
            logging.info("Écoute des annonces BLE de SEN55 et wood...")

            start_time = time.time()
            while time.time() - start_time < 20:
                try:
                    devices = scanner.scan(0.005)
                    devices = [f for f in devices if len(f.getScanData()) >= 2]
                    tab = [function for function in devices if (function.getScanData()[1][2] in available_devices.keys())]
                    devices = [f for f in devices if len(f.getScanData()) == 3]
                    tab += [function for function in devices if (function.getScanData()[2][2] in available_devices.keys())]

                    for dev in tab:
                        name_device = dev.getScanData()[-1][-1]
                        if self.Config.get_status(name_device):
                            manufacturer_data = dev.getValueText(255)
                            if manufacturer_data:
                                data = bytes.fromhex(manufacturer_data)
                                logging.info(f"Données reçues de {name_device}")
                                data_size = self.Config.get_values(name_device)
                                if len(data) >= data_size:
                                    values = struct.unpack(self.Config.get_values_string(name_device), data[:self.Config.get_values(name_device)])
                                    logging.debug(', '.join(str(value) for value in values))

                                    if name_device == "ConnectedWoodPlanck":
                                        self.CWP_data_to_array(values)
                                    elif name_device == "SEN55":
                                        self.SEN55_data_to_array(values)
                except BTLEException as e:
                    logging.error(f"Erreur Bluetooth: {str(e)}")
                except struct.error as e:
                    logging.error(f"Erreur de décodage des données: {str(e)}")
        except Exception as e:
            logging.error(f"Erreur lors de l'écoute des appareils: {str(e)}")
            raise ConnectedBluetoothDeviceError("Erreur d'écoute des appareils")

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
            existing_files = [f for f in os.listdir(self.DIRECTORY) if f.startswith(base_filename)]
            if existing_files and self.Config.get_sensor_amount("SEN55") != 1:
                numbers = [int(f.split('_')[-1].split('.')[0]) for f in existing_files if f.split('_')[-1].split('.')[0].isdigit()]
                if numbers:
                    last_number = max(numbers)
                    new_number = last_number + 1
                else:
                    new_number = 1
                new_filename = f"{base_filename}_{new_number}.csv"
            else:
                new_filename = self.SEN55_filename
            new_filepath = os.path.join(self.DIRECTORY, new_filename)
            df.to_csv(self.SEN55_path, mode="a", header=False, index=False)
        except Exception as e:
            logging.error(f"Erreur lors de l'écriture des données SEN55 dans le CSV: {str(e)}")
            raise ConnectedBluetoothDeviceError("Erreur d'écriture CSV SEN55")

    def CWP_data_to_array(self, values):
        """
        @brief Process and store ConnectedWoodPlank sensor data.
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
        @brief Write ConnectedWoodPlank data to CSV files.
        @exception ConnectedBluetoothDeviceError If CSV writing fails.
        """
        try:
            no_data = 0
            for data, path in [
                (self.CWP_Capa_data, self.CWP_Capa_path),
                (self.CWP_Piezos_data, self.CWP_Piezos_path),
                (self.CWP_SG_data, self.CWP_SG_path)
            ]:
                if data:
                    df = pd.DataFrame(data)
                    df.to_csv(path, mode="a", header=not pd.io.common.file_exists(path), index=False)
                    data.clear()
                    no_data = 1
            if no_data == 0:
                logging.info("Aucune donnée CWP à enregistrer.")
        except Exception as e:
            logging.error(f"Erreur lors de l'écriture des données CWP dans le CSV: {str(e)}")
            raise ConnectedBluetoothDeviceError("Erreur d'écriture CSV CWP")

if __name__ == "__main__":
    device = ConnectedBluetoothDevice()
    device.listen_for_sen55()
    # device.CWP_data_to_array([6,0,3,0,12,0,0,0,0,0,0,0,0,0,0,0,55])
    # device.CWP_data_to_array([0,1,2,3,0,5,6,7,0,9,10,11,0,1,134,160,15])
    # device.CWP_data_to_array([0,1,2,3,0,30,6,7,0,35,10,11,0,2,134,160,45])
    # device.CWP_data_to_array([0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,35])
    # device.CWP_data_to_array([0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,25])
    # device.CWP_data_to_array([0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,35])
    # device.CWP_data_to_array([0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,25])
    # device.CWP_data_to_array([0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,35])
    # device.CWP_data_to_array([0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,25])
    # device.CWP_data_to_csv()
