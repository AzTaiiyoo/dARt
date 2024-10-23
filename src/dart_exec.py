import logging
from pathlib import Path


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
Main_path = Path(__file__).parents[0]

import config.configuration as Conf
import MyoSensor.Myo as Myo
import ConnectedBluetoothDevice as cbd
import GridEyeKit as gek
import GrideyeBluetooth as geb
import ConnectedWoodPlank as cwp
from Instance_manager import InstanceManager
from config.Wifi_transmitter import Wifi_transmitter

class dARtEXE:
    def __init__(self):
        self.ConfigClass = Conf.Config()
        self.config = self.ConfigClass.config
        
        live_devices, live = self.ConfigClass.check_live_devices()
            
        self.wifi_transmitter = None
        if live:
            self.wifi_transmitter = Wifi_transmitter()
            
        self.device_manager = InstanceManager(self.wifi_transmitter)
        
    def check_activation_preconditions(self):
        for sensor in ["Myo_Sensor", "Grideye"]:
            if self.ConfigClass.get_sensor_amount(sensor) > 1:
                logging.error(f"The amount of {sensor} sensors must be 1 or less.")
                return False

        for sensor in ["Myo_Sensor", "Grideye", "SEN55", "Connected_Wood_Plank"]:
            if self.ConfigClass.get_sensor_amount(sensor) < 0:
                logging.error(f"The amount of {sensor} sensors must be 0 or more.")
                return False

    def activate_sensors(self):
        if self.check_activation_preconditions():
            return
        activated_sensors = []
        try:
            if self.wifi_transmitter:
                self.wifi_transmitter.start()
                
            for sensor in ["Myo_Sensor", "Grideye", "SEN55", "Connected_Wood_Plank"]:
                    sensor_count = self.ConfigClass.get_sensor_amount(sensor) if sensor not in ("Myo_Sensor", "Grideye") or self.ConfigClass.get_sensor_amount(sensor) <= 0 else 1
                    for i in range(1, sensor_count + 1):
                        success, sensor_id = self.device_manager.initialize_devices(sensor, True, i, self.wifi_transmitter)
                        if success and sensor_id:
                            activated_sensors.append(sensor_id)
                        else:
                            raise Exception(f"Failed to initialize {sensor}")
                        
            logging.info("Session is active")
        except (Exception, Myo.MyoSensorException, gek.GridEYEError, geb.GridEYEConnectionError, geb.GridEYEConfigError, cbd.ConnectedBluetoothDeviceError, cwp.ConnectedWoodPlankError) as e:
            logging.error(f"An error occurred while initializing sensors: {str(e)}")
            self.device_manager.cleanup_on_error(activated_sensors)
            
    def stop_session(self):
        if not self.is_session_active():
            logging.info("No session is currently active.")
            return

        logging.info(f"Sensor instances before stopping the session: {self.device_manager.sensor_instances}")

        try:
            for sensor_id, sensor_instance in self.device_manager.sensor_instances.items():
                if isinstance(sensor_instance, gek.GridEYEKit):
                    self.device_manager.stop_grideye_sensor(sensor_id, sensor_instance)
                elif isinstance(sensor_instance, cbd.ConnectedBluetoothDevice):
                    self.device_manager.stop_bluetooth_sensor(sensor_id, sensor_instance)
                elif isinstance(sensor_instance, cwp.ConnectedWoodPlank):
                    self.device_manager.stop_connected_wood_plank(sensor_id, sensor_instance)
                elif isinstance(sensor_instance, Myo.MyoSensor):
                    self.device_manager.stop_myo_sensor(sensor_id, sensor_instance)
                elif isinstance(sensor_instance, geb.GridEYEReader):
                    self.device_manager.stop_grideye_bluetooth_sensor(sensor_id, sensor_instance)
                else:
                    logging.warning(f"Unknown sensor type for {sensor_id}")

            self.clean_up_session()
            
            logging.info("Session stopped successfully")
            logging.info("Sensor instances: %s", str(self.device_manager.sensor_instances))
        except Exception as e:
            logging.error(f"An error occurred while stopping the session: {str(e)}")
    
    def is_session_active(self):
        active_sensors = [device['device'] for device in self.config['devices'] if device['active']]
        return bool(active_sensors) 

    def clean_up_session(self):
        self.device_manager.clean_up_session_instances()

    