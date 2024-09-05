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
import subprocess
import psutil
import signal
# import ConnectedBluetoothDevice as cbd

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
Main_path = Path(__file__).parents[0]


class Config:
    def __init__(self):
        with open('config/config.json', 'r') as config_file:
            self.config = json.load(config_file)

    def get_csv_output_directory(self):
        return self.config.get('csv_output_directory', 'default/path/to/csv/output')
        
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
            self.myo_process = None
        except Exception as e:
            logging.error(f"Error initializing dARtToolkit: {str(e)}")
            raise dARtToolkitError("Init Error")
        self.myo_process = None
    def launch_myo_executable(self):
        try:
            # Récupérer le chemin du répertoire de sortie CSV depuis config.json
            csv_dir = self.configClass.config['directories']['csv']
            output_directory = os.path.join(Main_path, csv_dir)
            print(f"base_dir : {Main_path}")
            print(f"output_directory : {output_directory}")
            
            # Assurez-vous que le répertoire existe, sinon créez-le
            os.makedirs(output_directory, exist_ok=True)
            
            # Chemin vers l'exécutable Myo (chemin relatif par rapport au script)
            executable_path = os.path.join(Main_path, "MyoLinux/src/MyoApp")
            print(f"executable_path: {executable_path}")
            print(f"Permissions executables : {os.access(executable_path, os.X_OK)}")
            print(f"Permissions ecriture repertoire : {os.access(os.path.dirname(output_directory),os.W_OK)}")
            
            # Lancer l'exécutable avec seulement le chemin du fichier CSV
            self.myo_process = subprocess.Popen([executable_path, output_directory], preexec_fn=os.setsid)
            st.success(f"Exécutable Myo lancé avec succès. Données enregistrées dans : {output_directory}")

            # Lisez la sortie en temps réel
            for line in self.myo_process.stdout:
                line = line.strip()
                if "Connected to Myo" in line:
                    message_placeholder.success("Myo connecté avec succès!")
                elif "Error" in line:
                    message_placeholder.error(f"Erreur Myo: {line}")
                else:
                    message_placeholder.text(f"Myo: {line}")
            
            # Mettre à jour le statut du capteur dans la configuration
            self.configClass.set_status('MYO_Sensor', True)
            
        except Exception as e:
            st.error(f"Erreur lors du lancement de l'exécutable Myo : {str(e)}")
            logging.error(f"Erreur lors du lancement de l'exécutable Myo : {str(e)}")

    def activate_sensors(self, myo, env, temp, plates):
        session_holder = st.empty()

        if not any([myo, env, temp, plates]):
            session_holder.warning("Please, select at least one sensor.")
            return

        session_holder.info("Initialisation du capteur...")
        time.sleep(2)
        
        try:
            if myo:
                self.launch_myo_executable()
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
                        #         connected_wood_plank.listen_for_sen55()
                        #         self.configClass.set_status(sensor, "true")
                        #         st.success(f"{sensor_id} connecté et initialisé ✅")
                        #     except (cbd.BTLEException, cbd.ConnectedBluetoothDeviceError) as e:
                        #         st.error(f"Erreur lors de l'initialisation de {sensor_id}: {str(e)}")
                        #         logging.error(f"Erreur lors de l'initialisation de {sensor_id}: {str(e)}")
                        # if sensor == "SEN55":
                        #     try:
                        #         sen55 =cbd.ConnectedBluetoothDevice()
                        #         self.sensor_instances[sensor_id] = sen55
                        #         sen55.listen_for_sen55()
                        #         self.configClass.set_status(sensor, "true")
                        #         st.success(f"{sensor_id} connecté et initialisé ✅")
                        #     except (cbd.BTLEException, cbd.ConnectedBluetoothDeviceError) as e:
                        #         st.error(f"Erreur lors de l'initialisation de {sensor_id}: {str(e)}")
                        #         logging.error(f"Erreur lors de l'initialisation de {sensor_id}: {str(e)}")
                        # else:
                        #     st.success(f"{sensor_id} activé ✅")
        except Exception as e:
            st.error(f"Une erreur inattendue s'est produite: {str(e)}")
            logging.error(f"Une erreur inattendue s'est produite lors de l'initialisation des capteurs: {str(e)}")

        session_holder.empty()

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


    def stop_session(self):
        session_holder = st.empty()
        session_holder.info("Arrêt de la session...")
        try:
            print(f"DEUS VULTTTTTTT ?????")
            # Arrêt de l'exécutable Myo
            # Vérifier si le processus Myo existe
            myo_process_exists = False
            for process in psutil.process_iter(['pid', 'name']):
                if "MyoApp" in process.info['name']:
                    myo_process_exists = True
                    pid = process.info['pid']
                    break

            if myo_process_exists:
                # Arrêter le processus Myo
                print(f"DEUS VULTTTTTTT")
                os.kill(pid, signal.SIGINT)
                print(f"LA de;ocratie a ete repamdue ")
                
                # Attendre que le processus se termine
                for _ in range(5):  # Attendre jusqu'à 5 secondes
                    if not psutil.pid_exists(pid):
                        break
                    time.sleep(1)
                
                # Si le processus n'est toujours pas terminé, le forcer
                if psutil.pid_exists(pid):
                    os.kill(pid, signal.SIGKILL)
                
                self.myo_process = None
                self.configClass.set_status('MYO_Sensor', False)
                st.success("Exécutable Myo arrêté avec succès.")
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
