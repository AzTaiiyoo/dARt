"""
@brief dARt Toolkit: A Streamlit application for sensor activation and database visualization.

This module provides the entry point for the dARt Toolkit application.

@author [Your Name]
@date [Current Date]
@version 2.2
"""

import streamlit as st
from dart_GUI import dARtToolkit, dARtToolkitError
import config.configuration as Conf
import config.Wifi_transmitter as Wifi

def main():
    try:
        config = Conf.Config()
        devices, live = config.check_live_devices()
        
        if live & devices.not_empty():
            wifi_socket = Wifi.Wifi_transmitter()
            
        app = dARtToolkit()
        app.run()
    except dARtToolkitError as e:
        st.error(f"Critical error: {str(e)}")
    except Exception as e:
        st.error(f"An unexpected critical error occurred: {str(e)}")
        
if __name__ == "__main__":
    main()