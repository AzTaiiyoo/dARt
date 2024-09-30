import json
import os
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
directory = Path(__file__).parent.resolve()

class Config:
    """
    @class Config
    @brief Classe pour gérer la configuration de l'application.

    Cette classe gère le chargement, la modification et la sauvegarde de la configuration
    stockée dans un fichier JSON.
    """

    def __init__(self):
        """
        @brief Initialise une instance de la classe Config.

        Charge le fichier de configuration lors de l'initialisation.
        """
        self.config_path = os.path.join(directory, 'config.json')
        self.config = self.load_config()
        
    def correct_config(self):
        self.set_grideye_myo_amount_to_one()
        self.reset_sensor_amount()
        self.save_config()
    
    def set_grideye_myo_amount_to_one(self):
        """
        @brief Sets the amount of grideye and myo sensors to one if greater than one.
        @return bool True if any amount was changed and the config file was saved, False otherwise.
        """
        try:
            changed = False
            for device in self.config['devices']:
                if device['device'].lower() == "Myo_Sensor" or "Grideye":
                    if device['amount'] > 1:
                        device['amount'] = 1
                        changed = True
            if changed:
                self.save_config()
            return changed
        except Exception as e:
            logging.error(f"Error while setting the amount of grideye and myo sensors to one: {e}")
            return False
        
    def reset_sensor_amount(self):
        """
        @brief Réinitialise le nombre de capteurs de tous les appareils si négatif.
        @return bool True si au moins un appareil a été réinitialisé, False sinon.
        """
        try:
            reset_occurred = False
            for device in self.config['devices']:
                if device['amount'] < 0:
                    device['amount'] = 0
                    reset_occurred = True
            
            if reset_occurred:
                self.save_config()
            
            return reset_occurred
        except Exception as e:
            logging.error(f"Error while resetting the amount of sensors: {e}")
            return False
                
    def get_devices(self):
        """
        @brief Retrieves the list of devices from the configuration.
        @return A list of devices.
        @details This function iterates over the 'devices' section of the configuration and retrieves the 'device' value for each entry. The list of devices is then returned.
        @note Make sure that the 'config' attribute is properly initialized before calling this function.
        """
        
        devices = []
        for device in self.config['devices']:
            devices.append(device['device'])
            return devices
            
    def load_config(self):
        """
        @brief Charge la configuration depuis le fichier JSON.
        @return dict La configuration chargée.
        """
        with open(self.config_path, 'r') as config_file:
            return json.load(config_file)

    def get_device_port(self, device_name):
        """
        @brief Récupère le port associé à un appareil.
        @param device_name str Le nom de l'appareil.
        @return str|None Le port de l'appareil ou None s'il n'est pas trouvé.
        """
        for device in self.config['ports']:
            if device['device'].lower() == device_name.lower():
                return device['port']
        return None

    def get_available_devices(self):
        """
        @brief Récupère la liste des appareils actifs.
        @return list[str] La liste des noms des appareils actifs.
        """
        devices = []
        for device in self.config['devices']:
            if device['active']:
                devices.append(device['device'])
        return devices

    def get_values(self, device_name):
        """
        @brief Récupère le nombre de valeurs associées à un appareil.
        @param device_name str Le nom de l'appareil.
        @return int Le nombre de valeurs ou 0 si l'appareil n'est pas trouvé.
        """
        for device in self.config['devices']:
            if device['device'].lower() == device_name.lower():
                return device['values']
        return 0

    def get_values_string(self, device_name):
        """
        @brief Récupère la chaîne de format des valeurs d'un appareil.
        @param device_name str Le nom de l'appareil.
        @return str La chaîne de format ou 0 si l'appareil n'est pas trouvé.
        """
        for device in self.config['devices']:
            if device['device'].lower() == device_name.lower():
                return device['values_string']
        return "0"

    def get_sensor_amount(self,device_name):
        """
        @brief Récupère le nombre de capteurs d'un appareil.
        @param device_name str Le nom de l'appareil.
        @return int Le nombre de capteurs ou 0 si l'appareil n'est pas trouvé.
        """
        for device in self.config['devices']:
            if device['device'].lower() == device_name.lower():
                return device['amount']
        return 0
    
    def set_sensor_amount(self, device_name, amount):
        """
        @brief Définit le nombre de capteurs d'un appareil.
        @param device_name str Le nom de l'appareil.
        @param amount int Le nombre de capteurs.
        @return bool True si le nombre de capteurs a été modifié avec succès, False sinon.
        """
        for device in self.config['devices']:
            if device['device'].lower() == device_name.lower():
                device['ammount'] = amount
                self.save_config()
                return True
        return False

    def get_status(self, device_name):
        """
        @brief Récupère le statut d'activation d'un appareil.
        @param device_name str Le nom de l'appareil.
        @return bool|None Le statut d'activation ou None si l'appareil n'est pas trouvé.
        """
        for device in self.config['devices']:
            if device['device'].lower() == device_name.lower():
                return device['active']
        return None

    def set_status(self, device_name, status):
        """
        @brief Définit le statut d'activation d'un appareil.
        @param device_name str Le nom de l'appareil.
        @param status bool Le nouveau statut d'activation.
        @return bool True si le statut a été modifié avec succès, False sinon.
        """
        for device in self.config['devices']:
            if device['device'].lower() == device_name.lower():
                device['active'] = status
                self.save_config()
                return True
        return False

    def get_active_preset(self):
        return self.config['active_preset']['value']

    def set_active_preset(self, preset_name):
            """
            @brief Set the active preset if it exists in the configuration.

            @param preset_name The name of the preset to set as active.
            @raises ValueError If the preset name doesn't exist in the configuration.
            """
            preset_names = [preset['name'] for preset in self.config['presets']]

            if preset_name not in preset_names:
                raise ValueError(f"Preset '{preset_name}' does not exist. Available presets are: {', '.join(preset_names)}")

            self.config['active_preset']['value'] = preset_name
            self.save_config()
            print(f"Active preset set to '{preset_name}'")

    def check_live_devices(self):
        live_devices = []
        try : 
            for device in self.config['devices']:
                live_devices.append(device['device']) if device['live'] else None
            if live_devices.not_empty():
                return live_devices, True
        except Exception as e:
            logging.error(f"Error while checking live devices: {e}")
            return None, False
    
    def get_wifi_configuration(self):
        try:
            wifi_conf = {"Broadcast_IP": self.config["Wifi_settings"]["Broadcast_IP"],
                        "Port": self.config["Wifi_settings"]["Port"],
                        "Min_interval": self.config["Wifi_settings"]["Min_interval"],
                        "Max_interval": self.config["Wifi_settings"]["Max_interval"],}
            return wifi_conf
        except Exception as e:
            logging.error(f"Error while retrieving the wifi configuration: {e}")
            return None
    
    def save_config(self):
        """
        @brief Sauvegarde la configuration dans le fichier JSON.
        @return bool True si la sauvegarde a réussi.
        """
        with open(self.config_path, 'w') as config_file:
            json.dump(self.config, config_file, indent=4)
        return True
    