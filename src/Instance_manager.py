from pathlib import Path
import logging

Main_path = Path(__file__).parents[0]
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

import config.configuration as Conf
import GridEyeKit as gek
import MyoSensor.Myo as Myo
import ConnectedBluetoothDevice as cbd
import GrideyeBluetooth as geb
import streamlit as st

class InstanceManager:
    """
    @brief Manages the initialization and cleanup of sensor instances.

    This class handles the creation, initialization, and cleanup of various sensor
    instances, including GridEye, SEN55, Myo Sensor, and Connected Wood Plank.
    """

    def __init__(self, wifi_transmitter):
        """
        @brief Initializes the InstanceManager.
        @param wifi_transmitter The WiFi transmitter object to use for sensor communication.
        """
        self.configClass = Conf.Config()
        self.config = self.configClass.config
        
        self.wifi_transmitter = wifi_transmitter
        
        if 'sensor_instances' not in st.session_state:
            st.session_state.sensor_instances = {}
        self.sensor_instances = st.session_state.sensor_instances

    def initialize_devices(self, sensor, is_active, i, wifi_transmitter):
        """
        @brief Initializes a specific sensor device.
        @param sensor The type of sensor to initialize.
        @param is_active Whether the sensor is active.
        @param i The instance number of the sensor.
        @param wifi_transmitter The WiFi transmitter object.
        @return tuple A boolean indicating success and the sensor_id if successful, or False and None if failed.
        """
        sensor_id = f"{sensor}_{i}" if i > 1 else sensor
        port = self.configClass.get_device_port(sensor_id)

        if sensor == "Grideye":
            return self.initialize_bluetooth_grideye(sensor_id, i)
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
        """
        @brief Initializes a GridEye sensor.
        @param sensor_id The unique identifier for the sensor.
        @param port The port to which the sensor is connected.
        @param i The instance number of the sensor.
        @return tuple A boolean indicating success and the sensor_id if successful, or False and None if failed.
        """
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

    def initialize_bluetooth_grideye(self, sensor_id, i):
        """
        @brief Initializes a Bluetooth GridEye sensor.
        @param sensor_id The unique identifier for the sensor.
        @param i The instance number of the sensor.
        @return tuple A boolean indicating success and the sensor_id if successful, or False and None if failed.
        """
        try:
            grideye = geb.GridEYEReader(i)
            self.sensor_instances[sensor_id] = grideye
            grideye.start_recording()
            self.configClass.set_status("Grideye", "true")
            st.success(f"{sensor_id} connecté et initialisé ✅")
            return True, sensor_id
        except Exception as e:
            st.error(f"Erreur lors de l'initialisation de {sensor_id}: {str(e)}")
            logging.error(f"Erreur lors de l'initialisation de {sensor_id}: {str(e)}")
            return False, None

    def initialize_sen55(self, sensor_id, i):
        """
        @brief Initializes a SEN55 sensor.
        @param sensor_id The unique identifier for the sensor.
        @param i The instance number of the sensor.
        @return tuple A boolean indicating success and the sensor_id if successful, or False and None if failed.
        """
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
        """
        @brief Initializes a Myo sensor.
        @param sensor_id The unique identifier for the sensor.
        @param port The port to which the sensor is connected.
        @param i The instance number of the sensor.
        @return tuple A boolean indicating success and the sensor_id if successful, or False and None if failed.
        """
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
        """
        @brief Initializes a Connected Wood Plank sensor.
        @param sensor_id The unique identifier for the sensor.
        @param i The instance number of the sensor.
        @return tuple A boolean indicating success and the sensor_id if successful, or False and None if failed.
        """
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
        """
        @brief Cleans up sensor instances in case of an error.
        @param activated_sensors A list of sensor IDs that were activated and need to be cleaned up.
        """
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
        """
        @brief Stops a GridEye sensor.
        @param sensor_id The unique identifier for the sensor.
        @param sensor_instance The instance of the GridEye sensor to stop.
        @return bool True if the sensor was successfully stopped, False otherwise.
        """
        try:
            sensor_instance.stop_recording()
            self.configClass.set_status(sensor_id, "false")
            return True
        except (Exception, gek.GridEYEError) as e:
            st.error(f"Error while stopping {sensor_id}: {str(e)}")
            logging.error(f"Error while stopping {sensor_id}: {str(e)}")
            return False
        
    def stop_grideye_bluetooth_sensor(self, sensor_id, sensor_instance):
        """
        @brief Stops a GridEye sensor.
        @param sensor_id The unique identifier for the sensor.
        @param sensor_instance The instance of the GridEye sensor to stop.
        @return bool True if the sensor was successfully stopped, False otherwise.
        """
        try:
            sensor_instance.stop_recording()
            self.configClass.set_status(sensor_id, "false")
            return True
        except (Exception, gek.GridEYEError) as e:
            st.error(f"Error while stopping {sensor_id}: {str(e)}")
            logging.error(f"Error while stopping {sensor_id}: {str(e)}")
            return False

    def stop_bluetooth_sensor(self, sensor_id, sensor_instance):
        """
        @brief Stops a Bluetooth sensor.
        @param sensor_id The unique identifier for the sensor.
        @param sensor_instance The instance of the Bluetooth sensor to stop.
        @return bool True if the sensor was successfully stopped, False otherwise.
        """
        try:
            sensor_instance.stop_recording()
            self.configClass.set_status(sensor_id, "false")
            return True
        except (Exception, cbd.ConnectedBluetoothDeviceError) as e:
            st.error(f"Error while stopping {sensor_id}: {str(e)}")
            logging.error(f"Error while stopping {sensor_id}: {str(e)}")
            return False

    def stop_myo_sensor(self, sensor_id, sensor_instance):
        """
        @brief Stops a Myo sensor.
        @param sensor_id The unique identifier for the sensor.
        @param sensor_instance The instance of the Myo sensor to stop.
        @return bool True if the sensor was successfully stopped, False otherwise.
        """
        try:
            sensor_instance.stop_myo_executable()
            self.configClass.set_status(sensor_id, "false")
            return True
        except (Exception, Myo.MyoSensorException) as e:
            st.error(f"Error while stopping {sensor_id}: {str(e)}")
            logging.error(f"Error while stopping {sensor_id}: {str(e)}")
            return False
        
    def clean_up_session_instances(self):
        """
        @brief Cleans up all sensor instances in the current session.
        """
        self.sensor_instances.clear()