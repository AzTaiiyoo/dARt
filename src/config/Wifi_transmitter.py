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
        self.sock = None
        
        self.latest_data = None
        self.previous_data = None
        
        self.running = threading.Event()
        self.thread = None
        
    def init_wifi_config(self):
        wifi_config = self.configClass.get_wifi_configuration()
        if wifi_config:
            self.Broadcast_IP = wifi_config['Broadcast_IP']
            self.Port = wifi_config['Port']
            self.Min_interval = wifi_config['Min_interval']
            self.Max_interval = wifi_config['Max_interval']
        
    def init_socket(self):
        if self.sock is None:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        
    def send_data(self, data):
        if self.sock:
            message = json.dumps(data).encode('utf-8')
            self.sock.sendto(message, (self.Broadcast_IP, self.Port))
        
    def start(self):
        if not self.running.is_set():
            self.init_socket()
            self.running.set()
            self.thread = threading.Thread(target=self.run)
            self.thread.start()
            logging.info("Wifi transmitter started.")
    
    def stop(self):
        if self.running.is_set():
            self.running.clear()
            if self.thread:
                self.thread.join(timeout=5)  # Wait up to 5 seconds for the thread to finish
            if self.sock:
                self.sock.close()
                self.sock = None
            logging.info("Wifi transmitter stopped.")
 
    def update(self, data):
        self.latest_data = data
        
    def __del__(self):
        self.stop()
        
    def run(self):
        while self.running.is_set():
            try:
                if self.latest_data != self.previous_data:
                    self.send_data(self.latest_data)
                    self.previous_data = self.latest_data
                time.sleep(self.Min_interval)
            except Exception as e:
                logging.error(f"Error in Wifi transmitter thread: {e}")
                # Optionally break the loop if a critical error occurs
                # break

# if __name__ == "__main__":
#     wifi = Wifi_transmitter()
#     try:
#         wifi.start()
#         # Simulate running for a while
#         time.sleep(30)
#     finally:
#         wifi.stop()