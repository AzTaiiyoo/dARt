"""
@file wifi_transmitter.py
@brief Module for WiFi data transmission in a sensor network system.
@author [Your Name]
@date [Current Date]
"""

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
    """
    @class Wifi_transmitter
    @brief A class for transmitting sensor data over WiFi using UDP broadcast.

    This class manages the WiFi connection, data transmission, and provides
    methods to start and stop the transmission process.
    """

    def __init__(self):
        """
        @brief Initialize the Wifi_transmitter object.
        @exception Exception If initialization fails.
        """
        try:
            self.configClass = Conf.Config()
            self.config = self.configClass.config
            
            self.init_wifi_config()
            self.sock = None
            
            self.latest_data = None
            self.previous_data = None
            
            self.running = threading.Event()
            self.thread = None
        except Exception as e:
            logging.error(f"Error initializing Wifi_transmitter: {e}")
        
    def init_wifi_config(self):
        """
        @brief Initialize WiFi configuration from the config file.
        @exception Exception If WiFi configuration fails.
        """
        try:
            wifi_config = self.configClass.get_wifi_configuration()
            if wifi_config:
                self.Broadcast_IP = wifi_config['Broadcast_IP']
                self.Port = wifi_config['Port']
                self.Min_interval = wifi_config['Min_interval']
                self.Max_interval = wifi_config['Max_interval']
            else:
                logging.error("Failed to get WiFi configuration")
        except Exception as e:
            logging.error(f"Error in init_wifi_config: {e}")
        
    def init_socket(self):
        """
        @brief Initialize the UDP socket for broadcasting.
        @exception Exception If socket initialization fails.
        """
        try:
            if self.sock is None:
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        except Exception as e:
            logging.error(f"Error initializing socket: {e}")
        
    def send_data(self, data):
        """
        @brief Send data over the UDP socket.
        @param data The data to be sent.
        @exception Exception If sending data fails.
        """
        try:
            if self.sock:
                message = json.dumps(data).encode('utf-8')
                self.sock.sendto(message, (self.Broadcast_IP, self.Port))
            else:
                logging.error("Socket not initialized, unable to send data")
        except Exception as e:
            logging.error(f"Error sending data: {e}")
        
    def start(self):
        """
        @brief Start the WiFi transmitter thread.
        @exception Exception If starting the transmitter fails.
        """
        try:
            if not self.running.is_set():
                self.init_socket()
                self.running.set()
                self.thread = threading.Thread(target=self.run)
                self.thread.start()
                logging.info("Wifi transmitter started.")
        except Exception as e:
            logging.error(f"Error starting Wifi transmitter: {e}")
    
    def stop(self):
        """
        @brief Stop the WiFi transmitter thread and close the socket.
        @exception Exception If stopping the transmitter fails.
        """
        try:
            if self.running.is_set():
                self.running.clear()
                if self.thread:
                    self.thread.join(timeout=3)  # Wait up to 3 seconds for the thread to finish
                if self.sock:
                    self.sock.close()
                    self.sock = None
                logging.info("Wifi transmitter stopped.")
        except Exception as e:
            logging.error(f"Error stopping Wifi transmitter: {e}")
 
    def update(self, data):
        """
        @brief Update the latest data to be transmitted.
        @param data The new data to be set as the latest data.
        @exception Exception If updating data fails.
        """
        try:
            self.latest_data = data
        except Exception as e:
            logging.error(f"Error updating data: {e}")
        
    def __del__(self):
        """
        @brief Destructor to ensure the WiFi transmitter is stopped.
        @exception Exception If destructor operations fail.
        """
        try:
            self.stop()
        except Exception as e:
            logging.error(f"Error in __del__ method: {e}")
        
    def run(self):
        """
        @brief Main loop for the WiFi transmitter thread.
        
        This method runs in a separate thread, continuously checking for new data
        and sending it over the WiFi connection at specified intervals.
        @exception Exception If an error occurs during thread execution.
        """
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