import json
import os
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
directory = Path(__file__).parent.resolve()

class Config:
    """
    @class Config
    @brief Class to manage the application's configuration.

    This class handles loading, modifying, and saving the configuration
    stored in a JSON file.
    """

    def __init__(self):
        """
        @brief Initializes an instance of the Config class.

        Loads the configuration file upon initialization.
        """
        self.config_path = os.path.join(directory, 'config.json')
        self.config = self.load_config()
        
    def correct_config(self):
        """
        @brief Corrects the configuration by calling multiple correction methods.
        
        This method calls set_grideye_myo_amount_to_one() and reset_sensor_amount(),
        then saves the corrected configuration.
        """
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
        @brief Resets the number of sensors for all devices if negative.
        @return bool True if at least one device was reset, False otherwise.
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
        @brief Loads the configuration from the JSON file.
        @return dict The loaded configuration.
        """
        with open(self.config_path, 'r') as config_file:
            return json.load(config_file)

    def get_device_port(self, device_name):
        """
        @brief Retrieves the port associated with a device.
        @param device_name str The name of the device.
        @return str|None The port of the device or None if not found.
        """
        for device in self.config['ports']:
            if device['device'].lower() == device_name.lower():
                return device['port']
        return None
    
    def get_device_ports(self, device_name):
        """
        @brief Retrieves the ports associated with a device.
        @param device_name str The name of the device.
        @return list A list of the device's ports or an empty list if none are found.
        """
        ports = []
        for device in self.config['ports']:
            if device['device'].lower().startswith(device_name.lower()):
                ports.append(device['port'])
                return ports

    def get_available_devices(self):
        """
        @brief Retrieves the list of active devices.
        @return list[str] The list of active device names.
        """
        devices = []
        for device in self.config['devices']:
            if device['active']:
                devices.append(device['device'])
        return devices

    def get_values(self, device_name):
        """
        @brief Retrieves the number of values associated with a device.
        @param device_name str The name of the device.
        @return int The number of values or 0 if the device is not found.
        """
        for device in self.config['devices']:
            if device['device'].lower() == device_name.lower():
                return device['values']
        return 0

    def get_values_string(self, device_name):
        """
        @brief Retrieves the value format string of a device.
        @param device_name str The name of the device.
        @return str The format string or "0" if the device is not found.
        """
        for device in self.config['devices']:
            if device['device'].lower() == device_name.lower():
                return device['values_string']
        return "0"

    def get_sensor_amount(self,device_name):
        """
        @brief Retrieves the number of sensors for a device.
        @param device_name str The name of the device.
        @return int The number of sensors or 0 if the device is not found.
        """
        for device in self.config['devices']:
            if device['device'].lower() == device_name.lower():
                return device['amount']
        return 0
    
    def set_sensor_amount(self, device_name, amount):
        """
        @brief Sets the number of sensors for a device.
        @param device_name str The name of the device.
        @param amount int The number of sensors.
        @return bool True if the number of sensors was successfully modified, False otherwise.
        """
        for device in self.config['devices']:
            if device['device'].lower() == device_name.lower():
                device['ammount'] = amount
                self.save_config()
                return True
        return False

    def get_status(self, device_name):
        """
        @brief Retrieves the activation status of a device.
        @param device_name str The name of the device.
        @return bool|None The activation status or None if the device is not found.
        """
        for device in self.config['devices']:
            if device['device'].lower() == device_name.lower():
                return device['active']
        return None

    def set_status(self, device_name, status):
        """
        @brief Sets the activation status of a device.
        @param device_name str The name of the device.
        @param status bool The new activation status.
        @return bool True if the status was successfully modified, False otherwise.
        """
        for device in self.config['devices']:
            if device['device'].lower() == device_name.lower():
                device['active'] = status
                self.save_config()
                return True
        return False

    def get_active_preset(self):
        """
        @brief Retrieves the active preset.
        @return str The name of the active preset.
        """
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
        """
        @brief Checks for devices in "live" mode.
        @return tuple A tuple containing a list of devices in "live" mode and a boolean indicating if any "live" devices were found.
        """
        live_devices = []
        try:
            for device in self.config['devices']:
                if device['live'] == "true":
                    live_devices.append(device['device'])
            if live_devices:
                return live_devices, True
            else:
                return None, False
        except Exception as e:
            logging.error(f"Error while checking live devices: {e}")
            return None, False
    
    def get_wifi_configuration(self):
        """
        @brief Retrieves the WiFi configuration.
        @return dict|None A dictionary containing the WiFi configuration or None in case of an error.
        """
        try:
            wifi_conf = {"Broadcast_IP": self.config["Wifi_settings"]["Broadcast_IP"],
                        "Port": self.config["Wifi_settings"]["Port"],
                        "Min_interval": self.config["Wifi_settings"]["Min_interval"],
                        "Max_interval": self.config["Wifi_settings"]["Max_interval"],}
            return wifi_conf
        except Exception as e:
            logging.error(f"Error while retrieving the wifi configuration: {e}")
            return None
        
    def get_service_uuid(self, device_name):
        """
        @brief Récupère l'UUID du service pour un appareil donné.
        @param device_name str Le nom de l'appareil.
        @return str|None L'UUID du service ou None si l'appareil n'est pas trouvé.
        """
        for device in self.config['uuid_services']:
            if device['device'].lower() == device_name.lower():
                uuid_config = {"DEVICE_ADDRESS": device['DEVICE_ADDRESS'],
                               "SERVICE_UUID": device['SERVICE_UUID'],
                               "CHARACTERISTIC_UUID": device['CHARACTERISTIC_UUID']}
                return uuid_config
            
    def save_config(self):
        """
        @brief Saves the configuration to the JSON file.
        @return bool True if the save was successful.
        """
        with open(self.config_path, 'w') as config_file:
            json.dump(self.config, config_file, indent=4)
        return True