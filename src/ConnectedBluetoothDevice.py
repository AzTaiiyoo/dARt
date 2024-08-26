"""
@file bluetooth_sensor_data.py
@brief Module for collecting data from BLE SEN55 and Connected_Wood_Plank sensors.

This module handles the discovery, collection, and recording of data
from BLE SEN55 and Connected_Wood_Plank sensors.

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
from pathlib import Path

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
    def __init__(self):
        """
        @brief Initialize the ConnectedBluetoothDevice object.
        @exception ConnectedBluetoothDeviceError If initialization fails.
        """
        try:
            self.ConfigClass = Conf.Config()
            self.config = self.ConfigClass.config

            self.instance_id = 1

            self.stop_flag = False
            self.current_time = time.strftime("%Y-%m-%d %H:%M:%S")

            self.DIRECTORY = self.config['directories']['csv']

            self.SEN55_filename = self.config['filenames']['SEN55']

            self.SEN55_path = os.path.join(Main_path,self.DIRECTORY, self.config['filenames']['SEN55'])
            self.CWP_SG_path = os.path.join(Main_path,self.DIRECTORY, self.config['filenames']['CWP_SG'])
            self.CWP_Capa_path = os.path.join(Main_path,self.DIRECTORY, self.config['filenames']['CWP_Capa'])
            self.CWP_Piezos_path = os.path.join(Main_path,self.DIRECTORY, self.config['filenames']['CWP_Piezos'])

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
                        if self.ConfigClass.get_status(name_device):
                            manufacturer_data = dev.getValueText(255)
                            if manufacturer_data:
                                data = bytes.fromhex(manufacturer_data)
                                logging.info(f"Données reçues de {name_device}")
                                data_size = self.ConfigClass.get_values(name_device)
                                if len(data) >= data_size:
                                    values = struct.unpack(self.ConfigClass.get_values_string(name_device), data[:self.ConfigClass.get_values(name_device)])
                                    logging.debug(', '.join(str(value) for value in values))

                                    if name_device == "Connected_Wood_Plank":
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
            sensor_amount = self.ConfigClass.get_sensor_amount("SEN55")

            if sensor_amount > 1:
                new_filename = f"{base_filename}_{self.instance_id}.csv"
            else:
                new_filename = self.SEN55_filename

            new_filepath = os.path.join(self.DIRECTORY, new_filename)

            # Vérifier si le fichier existe déjà pour déterminer si nous devons inclure l'en-tête
            file_exists = os.path.isfile(new_filepath)

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

                    new_path = os.path.join(self.DIRECTORY, new_filename)
                    df.to_csv(new_path, mode="w", header=True, index=False)
                    logging.info(f"Données {base_filename} enregistrées dans {new_filename}")
                    data.clear()

            if not any([self.CWP_Capa_data, self.CWP_Piezos_data, self.CWP_SG_data]):
                logging.info("Aucune donnée CWP à enregistrer.")
        except Exception as e:
            logging.error(f"Erreur lors de l'écriture des données CWP dans le CSV: {str(e)}")
            raise ConnectedBluetoothDeviceError("Erreur d'écriture CSV CWP")

if __name__ == "__main__":
    # Fonction utilitaire pour vérifier l'existence des fichiers
    # def check_file_exists(directory, filename):
    #     full_path = os.path.join(directory, filename)
    #     exists = os.path.exists(full_path)
    #     print(f"Fichier {filename}: {'Existe' if exists else 'N''existe pas'}")
    #     return exists

    # Créer trois instances de ConnectedBluetoothDevice
     device1 = ConnectedBluetoothDevice()
     device2 = ConnectedBluetoothDevice()
     device3 = ConnectedBluetoothDevice()

    # # Simuler l'ajout de données pour chaque device
    # test_data = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]

    # # Device 1
    # device1.CWP_data_to_array([*test_data, 55])  # Données de configuration
    # device1.CWP_data_to_array([*test_data, 15])  # Données SG
    # device1.CWP_data_to_array([*test_data, 25])  # Données Piezos
    # device1.CWP_data_to_array([*test_data, 35])  # Données Capa

    # # Device 2
    # device2.CWP_data_to_array([*test_data, 55])
    # device2.CWP_data_to_array([*test_data, 15])
    # device2.CWP_data_to_array([*test_data, 25])
    # device2.CWP_data_to_array([*test_data, 35])

    # # Device 3
    # device3.CWP_data_to_array([*test_data, 55])
    # device3.CWP_data_to_array([*test_data, 15])
    # device3.CWP_data_to_array([*test_data, 25])
    # device3.CWP_data_to_array([*test_data, 35])

    # # Écrire les données dans les fichiers CSV
    # device1.CWP_data_to_csv()
    # device2.CWP_data_to_csv()
    # device3.CWP_data_to_csv()

    # # Vérifier l'existence des fichiers créés
    # directory = device1.DIRECTORY  # Supposons que tous les devices utilisent le même répertoire

    # expected_files = [
    #     "CWP_Capa_data_0.csv", "CWP_Piezos_data_0.csv", "CWP_SG_data_0.csv",
    #     "CWP_Capa_data_1.csv", "CWP_Piezos_data_1.csv", "CWP_SG_data_1.csv",
    #     "CWP_Capa_data_2.csv", "CWP_Piezos_data_2.csv", "CWP_SG_data_2.csv"
    # ]

    # print("\nVérification des fichiers créés:")
    # all_files_exist = all(check_file_exists(directory, filename) for filename in expected_files)

    # if all_files_exist:
    #     print("\nTous les fichiers attendus ont été créés avec succès!")
    # else:
    #     print("\nCertains fichiers attendus n'ont pas été créés.")

    # print("\nTest terminé.")
