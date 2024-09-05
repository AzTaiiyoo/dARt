from pathlib import Path
import logging
import psutil
import signal
import subprocess
import time 
import streamlit as st
import os
import sys

# Définir les chemins
Main_path = Path(__file__).parent
Parent_path = Main_path.parent  # Ceci pointe vers le dossier 'src'
sys.path.append(str(Parent_path))

# Importer la configuration
import config.configuration as Conf

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class MyoSensorException(Exception):
    pass

class MyoSensor:
    def __init__(self):
        try:
            
            self.ClassDeConfiguration = Conf.Config()
            self.config = self.ClassDeConfiguration.config
            
            self.csv_dir = self.ClassDeConfiguration.config['directories']['csv']
            self.csv_path = Parent_path / self.csv_dir
            
            self.myo_process = None
            
            self.instance_id  = 1
        except Exception as e:
            logging.error(f"Error in MyoSensor __init__ {e}")
            st.error(f"Error in MyoSensor __init__ {e}")
            raise MyoSensorException(f"Error in MyoSensor __init__ {e}")
        
    def launch_myo_executable(self):
        try:
            # Récupérer le chemin du répertoire de sortie CSV depuis config.json
            # csv_dir = self.configClass.config['directories']['csv']
            # self.csv_path = os.path.join(Main_path, csv_dir)
            print(f"base_dir : {Main_path}")
            print(f"self.csv_path : {self.csv_path}")
            
            # Assurez-vous que le répertoire existe, sinon créez-le
            os.makedirs(self.csv_path, exist_ok=True)
            
            # Chemin vers l'exécutable Myo (chemin relatif par rapport au script)
            executable_path = os.path.join(Main_path, "MyoLinux/src/MyoApp")
            print(f"executable_path: {executable_path}")
            print(f"Permissions executables : {os.access(executable_path, os.X_OK)}")
            print(f"Permissions ecriture repertoire : {os.access(os.path.dirname(self.csv_path),os.W_OK)}")
            
            # Lancer l'exécutable avec seulement le chemin du fichier CSV
            self.myo_process = subprocess.Popen([executable_path, self.csv_path], preexec_fn=os.setsid)
            logging.info(f"Myo executable launched with PID: {self.myo_process.pid}")
            
            # Mettre à jour le statut du capteur dans la configuration
            self.configClass.set_status('MYO_Sensor', True)
            
        except Exception as e:
            st.error(f"Erreur lors du lancement de l'exécutable Myo : {str(e)}")
            logging.error(f"Erreur lors du lancement de l'exécutable Myo : {str(e)}")
            
    def stop_myo_executable(self):
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
            
if __name__ == "__main__":
    print (Parent_path)
    