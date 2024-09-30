import socket 
from pathlib import Path
import json
import time
import threading
import logging

Main_Path = Path(__file__).parents[0]
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

import config.configuration as Conf


class Wifi_transmitter:
    def __init__(self):
        self.configClass = Conf.Config()
        self.config = self.configClass.config
        
        self.init_wifi_config()
        self.init_socket()
        
        self.running = False
        self.thread = None
    
    def init_wifi_config(self):
        wifi_config = self.configClass.get_wifi_configuration()
        if wifi_config:
            self.Broadcast_IP = wifi_config['Broadcast_IP']
            self.Port = wifi_config['Port']
            self.Min_interval = wifi_config['Min_interval']
            self.Max_interval = wifi_config['Max_interval']
        
    def init_socket(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        
    def send_data(self, data):
        message = json.dumps(data).encode('utf-8')
        self.sock.sendto(message, (self.Broadcast_IP, self.Port))
        
    def start(self):
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self.run)
            self.thread.start()
            logging.info("Wifi transmitter started.")
    
    def stop(self):
        if self.running & self.thread:
            self.running = False
            self.thread.join()
            if self.sock:
                self.sock.close()
            logging.info("Wifi transmitter stopped.")
            
    def __del__(self):
        self.stop()
        
    def run(self):
        while self.running:
            data = self.collect_sensor_data()
            self.send_data(data)
            time.sleep(self.Min_interval)