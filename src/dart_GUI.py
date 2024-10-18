"""
@brief dARt Toolkit: Core functionality for sensor activation and database visualization.

This module contains the main class and functions for the dARt Toolkit application.

@author [Your Name]
@date [Current Date]
@version 2.2
"""

import os
import time
import importlib.util
import streamlit as st
import config.configuration as Conf
import GridEyeKit as gek
import logging
from pathlib import Path

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
Main_path = Path(__file__).parents[0]

import MyoSensor.Myo as Myo
import ConnectedBluetoothDevice as cbd
import GridEyeKit as gek
import GrideyeBluetooth as geb
import ConnectedWoodPlank as cwp
from Instance_manager import InstanceManager
from config.Wifi_transmitter import Wifi_transmitter

class dARtToolkitError(Exception):
    """dARt Toolkit error class."""
    pass

class dARtToolkit:
    def __init__(self):
        try:
            self.configClass = Conf.Config()
            self.config = self.configClass.config
            
            live_devices, live = self.configClass.check_live_devices()
            
            self.wifi_transmitter = None
            if live:
                self.wifi_transmitter = Wifi_transmitter()
                
            self.device_manager = InstanceManager(self.wifi_transmitter)

            if 'session_active' not in st.session_state:
                st.session_state.session_active = False

            self.DIRECTORY = self.config["directories"]["database"]
            self.PAGE_TITLE = "dARt Toolkit"
            self.CUSTOM_CSS = """
            <style>
                padding: 0.5rem 1rem;
            }
            .custom-divider {
                border-top: 2px solid #f0f2f6;
                width: 75%;
            }
            .bottom-buttons {
                position: fixed;
                bottom: 0;
                left: 0;
                right: 0;
                padding: 10px;
                background-color: white;
            }

            h1 {
                color: black;
                margin-bottom: 1.4rem;
            }

            .stButton>button {
                background-color: white;
                color : black;
                border-radius: 10px;
                border: 1px solid blue;
                padding: 0.5rem 1rem;
                transition: all 0.3s;
                }
            </style>
            """
        except Exception as e:
            logging.error(f"Error initializing dARtToolkit: {str(e)}")
            raise dARtToolkitError("Init Error")

    def list_database_files(self):
        try:
            return [f[:-3] for f in os.listdir(os.path.join(Main_path, self.DIRECTORY)) if f.endswith('_database.py')]
        except OSError as e:
            logging.error(f"Error reading system database folder: {str(e)}")
            raise dARtToolkitError("Error reading database folder")

    def load_module(self, module_name, file_path):
        try:
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module
        except ImportError as e:
            logging.error(f"Error loading module: {module_name}: {str(e)}")
            raise dARtToolkitError(f"Error loading module: {module_name}")

    def check_activation_preconditions(self, myo, env, temp, plates):
        if st.session_state.session_active:
            st.warning("A session is already active. Stop the current session before starting a new one.")
            return False

        if not any([myo, env, temp, plates]):
            st.warning("Please, select at least one sensor.")
            return False

        for sensor in ["Myo_Sensor", "Grideye"]:
            if self.configClass.get_sensor_amount(sensor) > 1:
                st.warning(f"Multiple instances of {sensor} are not supported. Please modify config.json file.")
                return False

        for sensor in ["Myo_Sensor", "Grideye", "SEN55", "Connected_Wood_Plank"]:
            if self.configClass.get_sensor_amount(sensor) < 0:
                st.warning(f"Please, set the number of {sensor} to 0, 1 or more in the config.json file.")
                return False

        return True

    def activate_sensors(self, myo, env, temp, plates):
        if not self.check_activation_preconditions(myo, env, temp, plates):
            return

        session_holder = st.empty()
        session_holder.info("Initializing sensors...")

        activated_sensors = []
        try:
            if self.wifi_transmitter:
                self.wifi_transmitter.start()
                
            for sensor, is_active in [("Myo_Sensor", myo), ("SEN55", env), ("Grideye", temp),
                                      ("Connected_Wood_Plank", plates)]:
                if is_active:
                    sensor_count = self.configClass.get_sensor_amount(sensor) if sensor not in ("Myo_Sensor", "Grideye") or self.configClass.get_sensor_amount(sensor) <= 0 else 1
                    for i in range(1, sensor_count + 1):
                        success, sensor_id = self.device_manager.initialize_devices(sensor, is_active, i, self.wifi_transmitter)
                        if success and sensor_id:
                            activated_sensors.append(sensor_id)
                        else:
                            raise Exception(f"Failed to initialize {sensor}")

            st.session_state.session_active = True
            logging.info("Session is active")
            session_holder.empty()
        except (Exception, Myo.MyoSensorException, gek.GridEYEError, geb.GridEYEConnectionError, geb.GridEYEConfigError, cbd.ConnectedBluetoothDeviceError, cwp.ConnectedWoodPlankError) as e:
            st.error(f"An error occurred: {str(e)}")
            logging.error(f"An error occurred while initializing sensors: {str(e)}")
            self.device_manager.cleanup_on_error(activated_sensors)
            st.session_state.session_active = False
            session_holder.error("Sensor activation cancelled due to errors.")
            
    def stop_session(self):
        session_holder = st.empty()

        if not self.is_session_active():
            session_holder.warning("No session is currently active.")
            return

        session_holder.info("Stopping session...")

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
            
            session_holder.success("Session stopped ✅")
            logging.info("Session stopped successfully")
            logging.info("Sensor instances: %s", str(self.device_manager.sensor_instances))
        except Exception as e:
            session_holder.error(f"An error occurred while stopping the session: {str(e)}")
            logging.error(f"An error occurred while stopping the session: {str(e)}")

    def is_session_active(self):
        active_sensors = [device['device'] for device in self.config['devices'] if device['active']]
        return bool(active_sensors) and st.session_state.session_active

    def clean_up_session(self):
        self.device_manager.clean_up_session_instances()
        st.session_state.session_active = False

    def setup_page(self):
        try:
            st.set_page_config(page_title=self.PAGE_TITLE, layout="centered")
            st.markdown(self.CUSTOM_CSS, unsafe_allow_html=True)
        except Exception as e:
            logging.error(f"Error during the configuration of the page: {str(e)}")
            raise dARtToolkitError("Setup page configuration error")

    def setup_sidebar(self):
        try:
            st.sidebar.success("Select a database")
            database_files = ["-"] + self.list_database_files()
            return st.sidebar.selectbox("Select a database", database_files)
        except dARtToolkitError as e:
            st.sidebar.error(f"Error: {str(e)}")
            logging.error(f"Error while setting up the sidebar: {str(e)}")
            return "-"

    def main_view(self):
        st.title("Welcome to dARt Toolkit 🎨")
        st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)
        st.markdown(
            """
           Please, **select the sensors you wish to activate**.

            Once your session is finished, you can **choose a database in the sidebar**.

            For more details, you can check our [documentation](https://docs.streamlit.io/library).
            """
        )

        col1, col2 = st.columns(2)
        button_activate, button_stop = st.columns(2)  

        with col1:
            myo = st.toggle("Myo", key="myo")
            temp = st.toggle("Grid-EYE", key="temp")
            
        with col2:
            env = st.toggle("Sen55", key="env")
            plates = st.toggle("Connected_Wood_Plank", key="plates")
        
        with button_activate:
            if st.button("Activate and start", disabled= st.session_state.session_active):
                    self.activate_sensors(myo, st.session_state.env, temp, st.session_state.plates)

        with button_stop:
            if st.button("Stop session", disabled= not st.session_state.session_active):
                    self.stop_session()
                    
        with st.container():
            st.markdown('<div class="bottom-buttons"></div>', unsafe_allow_html=True)
            st.write("Here, you can select a **preset** to modify sensors data transfer speed :")

            preset1, preset2, preset3, preset4 = st.columns(4)

            for i, preset in enumerate([preset1, preset2, preset3, preset4], start=1):
                with preset:
                    if st.button(f"Preset {i}"):
                        current_preset = self.configClass.get_active_preset()
                        if current_preset == f"preset{i}":

                            try:
                                self.configClass.set_active_preset("default")
                                self.configClass.save_config()
                                st.warning("Default preset selected ✅")
                            except Exception as e:
                                st.error(f"Error while selecting default preset : {str(e)}")
                                logging.error(f"Error while selecting default preset : {str(e)}")
                        else:

                            try:
                                self.configClass.set_active_preset(f"preset{i}")
                                self.configClass.save_config()
                                st.success(f"preset {i} sélectionné ✅")
                            except Exception as e:
                                st.error(f"Error while selecting Preset {i} : {str(e)}")
                                logging.error(f"Error while selecting preset {i}: {str(e)}")

    def database_view(self, selected_database):
        try:
            module_path = os.path.join(str(Main_path), self.DIRECTORY, f"{selected_database}.py")
            db_module = self.load_module(selected_database, module_path)

            if hasattr(db_module, 'main'):
                db_module.main()
            else:
                st.error("Visualization is not defined for this module")
        except dARtToolkitError as e:
            st.error(str(e))
        except Exception as e:
            st.error(f"An error occured while displaying the database module : {str(e)}")
            logging.error(f"Error in database module display: {str(e)}")

    def run(self):
        try:
            self.configClass.correct_config()
            self.setup_page()
            selected_database = self.setup_sidebar()

            if 'current_view' not in st.session_state:
                st.session_state.current_view = 'main'

            if selected_database != "-":
                st.session_state.current_view = 'database'
                st.session_state.selected_database = selected_database
            elif st.session_state.current_view != 'main':
                st.session_state.current_view = 'main'
                st.rerun()

            if st.session_state.current_view == 'main':
                self.main_view()
            elif st.session_state.current_view == 'database':
                self.database_view(st.session_state.selected_database)
        except Exception as e:
            st.error(f"An unexpected error occured while running the page: {str(e)}")
            logging.error(f"Error in run section: {str(e)}")
