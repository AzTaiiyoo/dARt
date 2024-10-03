from pathlib import Path
import logging

Main_path = Path(__file__).parents[0]
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

import config.configuration as Conf
import GridEyeKit as gek
import MyoSensor.Myo as Myo
import ConnectedBluetoothDevice as cbd
import streamlit as st

class InstanceManager:
    def __init__(self, wifi_transmitter):
        self.configClass = Conf.Config()
        self.config = self.configClass.config
        
        self.wifi_transmitter = wifi_transmitter
        
        if 'sensor_instances' not in st.session_state:
            st.session_state.sensor_instances = {}
        self.sensor_instances = st.session_state.sensor_instances

    def initialize_devices(self, sensor, is_active, i, wifi_transmitter):
        sensor_id = f"{sensor}_{i}" if i > 1 else sensor
        port = self.configClass.get_device_port(sensor_id)

        if sensor == "Grideye":
            return self.initialize_grideye(sensor_id, port, i)
        elif sensor == "SEN55":
            return self.initialize_sen55(sensor_id, i)
        elif sensor == "Myo_Sensor":
            return self.initialize_myo_sensor(sensor_id, port, i)
        elif sensor == "Connected_Wood_Plank":
            return self.initialize_connected_wood_plank(sensor_id, i)
        else:
            st.error(f"Unknown sensor: {sensor}")
            return False, None

    def initialize_grideye(self, sensor_id, port, i):
        try:
            grideye = gek.GridEYEKit(port, self.wifi_transmitter)
            if grideye.connect():
                self.sensor_instances[sensor_id] = grideye
                grideye.start_recording()
                grideye.instance_id = i
                self.configClass.set_status("Grideye", "true")
                st.success(f"{sensor_id} initialized & connected ✅")
                return True, sensor_id
            else:
                raise Exception(f"Error while initializing {sensor_id}. Please verify the connection.")
        except (gek.GridEYEError, Exception) as e:
            st.error(f"Error while initializing {sensor_id}: {str(e)}")
            return False, None

    def initialize_sen55(self, sensor_id, i):
        try:
            sen55 = cbd.ConnectedBluetoothDevice(self.wifi_transmitter)
            self.sensor_instances[sensor_id] = sen55
            self.configClass.set_status("SEN55", "true")
            sen55.instance_id = i
            sen55.start_recording()
            st.success(f"{sensor_id} connecté et initialisé ✅")
            return True, sensor_id
        except Exception as e:
            st.error(f"Erreur lors de l'initialisation de {sensor_id}: {str(e)}")
            logging.error(f"Erreur lors de l'initialisation de {sensor_id}: {str(e)}")
            return False, None

    def initialize_myo_sensor(self, sensor_id, port, i):
        try:
            MyoSensor = Myo.MyoSensor(port)
            MyoSensor.launch_myo_executable()
            MyoSensor.instance_id = i
            self.sensor_instances[sensor_id] = MyoSensor
            self.configClass.set_status("Myo_Sensor", "true")
            st.success(f"{sensor_id} connecté et initialisé ✅")
            return True, sensor_id
        except Exception as e:
            st.error(f"Error while initializing {sensor_id}: {str(e)}")
            logging.error(f"Error while initializing {sensor_id}: {str(e)}")
            return False, None

    def initialize_connected_wood_plank(self, sensor_id, i):
        try:
            connected_wood_plank = cbd.ConnectedBluetoothDevice(self.wifi_transmitter)
            self.sensor_instances[sensor_id] = connected_wood_plank
            connected_wood_plank.instance_id = i
            self.configClass.set_status("Connected_Wood_Plank", "true")
            connected_wood_plank.start_recording()
            st.success(f"{sensor_id} connecté et initialisé ✅")
            return True, sensor_id
        except Exception as e:
            st.error(f"Erreur lors de l'initialisation de {sensor_id}: {str(e)}")
            logging.error(f"Erreur lors de l'initialisation de {sensor_id}: {str(e)}")
            return False, None

    def cleanup_on_error(self, activated_sensors):
        for sensor_id in activated_sensors:
            try:
                sensor_instance = self.sensor_instances.pop(sensor_id, None)
                if isinstance(sensor_instance, gek.GridEYEKit):
                    sensor_instance.stop_recording()
                    self.configClass.set_status(sensor_id, "false")
                if isinstance(sensor_instance, cbd.ConnectedBluetoothDevice):
                    sensor_instance.stop_flag = True
                    self.configClass.set_status(sensor_id, "false")
                elif isinstance(sensor_instance, Myo.MyoSensor):
                    sensor_instance.stop_myo_executable()
                self.configClass.set_status(sensor_id.split('_')[0], "false")
            except Exception as deactivation_error:
                logging.error(f"Error deactivating {sensor_id}: {str(deactivation_error)}")

    def stop_grideye_sensor(self, sensor_id, sensor_instance):
        try:
            sensor_instance.stop_recording()
            self.configClass.set_status(sensor_id, "false")
            return True
        except (Exception, gek.GridEYEError) as e:
            st.error(f"Error while stopping {sensor_id}: {str(e)}")
            logging.error(f"Error while stopping {sensor_id}: {str(e)}")
            return False

    def stop_bluetooth_sensor(self, sensor_id, sensor_instance):
        try:
            sensor_instance.stop_recording()
            self.configClass.set_status(sensor_id, "false")
            return True
        except (Exception, cbd.ConnectedBluetoothDeviceError) as e:
            st.error(f"Error while stopping {sensor_id}: {str(e)}")
            logging.error(f"Error while stopping {sensor_id}: {str(e)}")
            return False

    def stop_myo_sensor(self, sensor_id, sensor_instance):
        try:
            sensor_instance.stop_myo_executable()
            self.configClass.set_status(sensor_id, "false")
            return True
        except (Exception, Myo.MyoSensorException) as e:
            st.error(f"Error while stopping {sensor_id}: {str(e)}")
            logging.error(f"Error while stopping {sensor_id}: {str(e)}")
            return False
        
    def clean_up_session_instances(self):
        self.sensor_instances.clear()