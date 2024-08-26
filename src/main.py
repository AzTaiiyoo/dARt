"""
@brief dARt Toolkit: A Streamlit application for sensor activation and database visualization.

This module provides a user interface for activating various sensors and
visualizing data from selected databases.

@author [Your Name]
@date [Current Date]
@version 2.1
"""

import os
import time
import importlib.util
import streamlit as st
import config.configuration as Conf
import GridEyeKit as gek
import logging
from pathlib import Path
import sys
# import ConnectedBluetoothDevice as cbd

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
Main_path = Path(__file__).parents[0]

class dARtToolkitError(Exception):
    """Exception personnalisée pour dARtToolkit"""
    pass

class dARtToolkit:
    def __init__(self):
        try:
            self.configClass = Conf.Config()
            self.config = self.configClass.config
            
            self.sensor_instances = {}
            
            self.DIRECTORY = self.config["directories"]["database"]
            
            self.PAGE_TITLE = "dARt Toolkit"
            self.CUSTOM_CSS = """
            <style>
            .stSidebar .stSuccess {
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

    def activate_sensors(self, myo, env, temp, plates):
        session_holder = st.empty()

        if not any([myo, env, temp, plates]):
            session_holder.warning("Please, select at least one sensor.")
            return

        session_holder.info("Initialisation du capteur...")
        time.sleep(2)

        try:
            for sensor, is_active in [("Myo", myo), ("SEN55", env), ("Grideye", temp),
                                      ("Connected_Wood_Plank", plates)]:
                if is_active:
                    sensor_count = self.configClass.get_sensor_amount(sensor)
                    for i in range(1, sensor_count + 1):
                        sensor_id = f"{sensor}_{i}" if i > 1 else sensor
                        port = self.configClass.get_device_port(sensor_id)
                        if sensor == "Grideye":
                            try:
                                grideye = gek.GridEYEKit(port)
                                if grideye.connect():
                                    self.sensor_instances[sensor_id] = grideye
                                    grideye.start_recording()
                                    grideye.instance_id = i
                                    self.configClass.set_status(sensor, "true")
                                    st.success(f"{sensor_id} connecté et initialisé ✅")
                                else:
                                    st.error(f"Échec de la connexion à {sensor_id}. Veuillez vérifier la connexion.")
                            except gek.GridEYEError as e:
                                st.error(f"Erreur lors de l'initialisation de {sensor_id}: {str(e)}")
                        # if sensor == "Connected_Wood_Plank":
                        #     try:
                        #         connected_wood_plank = cbd.ConnectedBluetoothDevice()
                        #         self.sensor_instances[sensor_id] = connected_wood_plank
                        #         connected_wood_plank.instance_id = i
                        #         self.configClass.set_status(sensor, "true")
                        #         connected_wood_plank.listen_for_sen55()
                        #         st.success(f"{sensor_id} connecté et initialisé ✅")
                        #     except (cbd.BTLEException, cbd.ConnectedBluetoothDeviceError) as e:
                        #         st.error(f"Erreur lors de l'initialisation de {sensor_id}: {str(e)}")
                        #         logging.error(f"Erreur lors de l'initialisation de {sensor_id}: {str(e)}")
                        # if sensor == "SEN55":
                        #     try:
                        #         sen55 =cbd.ConnectedBluetoothDevice()
                        #         self.sensor_instances[sensor_id] = sen55
                        #         self.configClass.set_status(sensor, "true")
                        #         sen55.instance_id = i
                        #         sen55.listen_for_sen55()
                        #         st.success(f"{sensor_id} connecté et initialisé ✅")
                        #     except (cbd.BTLEException, cbd.ConnectedBluetoothDeviceError) as e:
                        #         st.error(f"Erreur lors de l'initialisation de {sensor_id}: {str(e)}")
                        #         logging.error(f"Erreur lors de l'initialisation de {sensor_id}: {str(e)}")
                        else:
                            st.error(f"Capteur inconnu: {sensor}")
        except Exception as e:
            st.error(f"Une erreur inattendue s'est produite: {str(e)}")
            logging.error(f"Une erreur inattendue s'est produite lors de l'initialisation des capteurs: {str(e)}")

        session_holder.empty()

    def stop_session(self):
        session_holder = st.empty()
        session_holder.info("Arrêt de la session...")
        active_sensors = [device['device'] for device in self.config['devices'] if device['active']]
        
        if not active_sensors: 
            session_holder.warning("No session is currently active.")
            return
        
        try:
            for sensor_id, sensor_instance in self.sensor_instances.items():
                if isinstance(sensor_instance, gek.GridEYEKit):
                    sensor_instance.stop_recording()
                    sensor_instance.close()
                    self.configClass.set_status(sensor_id, "false")
                # if isinstance(sensor_instance, cbd.ConnectedBluetoothDevice):
                #     sensor_instance.stop_flag = True
                #     self.configClass.set_status(sensor_id, "false")
            self.sensor_instances.clear()
            time.sleep(2)
            session_holder.success("Session arrêtée ✅")
        except Exception as e:
            session_holder.error(f"Erreur lors de l'arrêt de la session: {str(e)}")
            logging.error(f"Erreur lors de l'arrêt de la session: {str(e)}")

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
            return st.sidebar.selectbox("Sélectionnez une base de données", database_files)
        except dARtToolkitError as e:
            st.sidebar.error(f"Error: {str(e)}")
            logging.error(f"Error while setting up the sidebar: {str(e)}")
            return "-"

    def main_view(self):
        st.title("Bienvenue sur dARt Toolkit 🎨")
        st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)
        st.markdown(
            """
            Veuillez **sélectionner les capteurs que vous souhaitez activer**.

            Une fois votre session terminée, vous pouvez **choisir une base de données dans la barre latérale**.

            Pour plus de détails, consultez notre [documentation](https://docs.streamlit.io/library).
            """
        )

        col1, col2 = st.columns(2)

        with col1:
            myo = st.toggle("Myo", key="myo")
            temp = st.toggle("Grid-EYE", key="temp")
            if st.button("Activer les paramètres sélectionnés"):
                self.activate_sensors(myo, st.session_state.env, temp, st.session_state.plates)

        with col2:
            env = st.toggle("Sen55", key="env")
            plates = st.toggle("Connected_Wood_Plank", key="plates")
            if st.button("Arrêter la session"):
                self.stop_session()

        with st.container():
            st.markdown('<div class="bottom-buttons"></div>', unsafe_allow_html=True)
            st.write("Ici, vous pouvez sélectionner un **préréglage** pour la vitesse de transfert des données :")

            preset1, preset2, preset3, preset4 = st.columns(4)

            for i, preset in enumerate([preset1, preset2, preset3, preset4], start=1):
                with preset:
                    if st.button(f"Préréglage {i}"):
                        if self.configClass.get_active_preset() == "default":
                            try:
                                self.configClass.set_active_preset(f"preset{i}")
                                self.configClass.save_config()
                                st.success(f"Préréglage {i} sélectionné ✅")
                            except Exception as e:
                                st.error(f"Error while selecting preset configuration: {str(e)}")
                                logging.error(f"Preset selection error: {str(e)}")
                        else:
                            self.configClass.set_active_preset("default")

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
            st.error(f"An unexpected error occured whiler running the page: {str(e)}")
            logging.error(f"Error in run section: {str(e)}")

if __name__ == "__main__":
    try:
        app = dARtToolkit()
        app.run()
    except dARtToolkitError as e:
        st.error(f"Critical error: {str(e)}")
        logging.critical(f"Critical error in main section: {str(e)}")
    except Exception as e:
        st.error(f"An unexpected critical error occured: {str(e)}")
        logging.critical(f"An unexpected critical error occured: {str(e)}")