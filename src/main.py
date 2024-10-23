"""
@brief dARt Toolkit: Application for sensor activation with optional GUI interface.

This module provides the entry point for the dARt application, allowing users to choose
between GUI and command-line interfaces.

@author [Your Name]
@date [Current Date]
@version 2.3
"""

import streamlit as st
from dart_GUI import dARtToolkit, dARtToolkitError
from dart_exec import dARtEXE
import config.configuration as Conf
import config.Wifi_transmitter as Wifi
import threading
import queue
import logging
import sys
import subprocess
import os
import signal

def handle_user_input(user_input_queue):
    """Continuously monitor for user input to end the session."""
    while True:
        user_input = input().strip().lower()
        if user_input == "end":
            user_input_queue.put("end")
            break

def run_command_line_interface():
    """Run the application in command-line mode."""
    try:
        app = dARtEXE()
        
        user_input_queue = queue.Queue()
        input_thread = threading.Thread(
            target=handle_user_input, 
            args=(user_input_queue,),
            daemon=True
        )
        input_thread.start()
        
        logging.info("Session started. Type 'end' at any time to stop the session.")
        
        app.activate_sensors()
        
        while True:
            try:
                if not user_input_queue.empty():
                    command = user_input_queue.get()
                    if command == "end":
                        app.stop_session()
                        logging.info("Session ended by user")
                        break
            except Exception as e:
                logging.error(f"Error in main loop: {str(e)}")
                break
                
    except Exception as e:
        logging.error(f"An unexpected error occurred: {str(e)}")
    finally:
        sys.exit(0)

def handle_exit(signum, frame):
    """Handle exit signals gracefully."""
    logging.info("Shutting down gracefully...")
    sys.exit(0)

def launch_streamlit():
    """Launch the Streamlit interface using subprocess."""
    try:
        # Configurer le gestionnaire de signal pour Ctrl+C
        signal.signal(signal.SIGINT, handle_exit)
        signal.signal(signal.SIGTERM, handle_exit)

        script_path = os.path.abspath(__file__)
        process = subprocess.Popen(['streamlit', 'run', script_path, '--', '--streamlit_mode'])
        
        try:
            process.wait()
        except KeyboardInterrupt:
            logging.info("Received keyboard interrupt, shutting down gracefully...")
            if process.poll() is None:  # Si le processus est toujours en cours
                process.terminate()  # Envoyer SIGTERM
                try:
                    process.wait(timeout=3)  # Attendre 3 secondes pour la terminaison
                except subprocess.TimeoutExpired:
                    process.kill()  # Forcer la fermeture si nécessaire
            sys.exit(0)
        
    except Exception as e:
        logging.error(f"Failed to launch Streamlit: {str(e)}")
        sys.exit(1)

def run_streamlit_app():
    """Run the Streamlit application."""
    try:
        config = Conf.Config()
        devices, live = config.check_live_devices()
        
        app = dARtToolkit()
        app.run()
    except dARtToolkitError as e:
        st.error(f"Critical error: {str(e)}")
    except Exception as e:
        st.error(f"An unexpected critical error occurred: {str(e)}")

def main():
    """Main entry point of the application."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Check if running in Streamlit mode
    if len(sys.argv) > 1 and sys.argv[1] == '--streamlit_mode':
        run_streamlit_app()
        return
    
    # Ask user for interface preference
    while True:
        choice = input("Do you wish to use the interface? (Yes/No): ").strip().lower()
        if choice in ['yes', 'no']:
            break
        print("Please enter either 'Yes' or 'No'")
    
    if choice == 'yes':
        launch_streamlit()
    else:
        run_command_line_interface()

if __name__ == "__main__":
    main()