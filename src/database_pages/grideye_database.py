"""
@file grideye_database.py
@brief A Streamlit application for visualizing Grid-EYE sensor data.

This module provides a user interface for loading, filtering, and visualizing
Grid-EYE sensor data using Streamlit and Plotly.

@author [Your Name]
@date [Current Date]
@version 1.0
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import os
import config.configuration as conf
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

Main_path = Path(__file__).parents[1]

class GridEyeDatabaseError(Exception):
    """Exception personnalisée pour GridEyeDatabase"""
    pass

class GridEyeDatabase:
    """
    @class GridEyeDatabase
    @brief A class for managing and visualizing Grid-EYE sensor data.

    This class provides methods for loading Grid-EYE sensor data from a CSV file
    and creating a Streamlit interface to visualize and interact with the data.
    """

    def __init__(self):
        """
        @brief Initialize the GridEyeDatabase object.

        Sets up the configuration and file paths for the Grid-EYE data.
        """
        try:
            self.ConfigClass = conf.Config()
            self.config = self.ConfigClass.config
            self.directory = self.config['directories']['database']
            self.csv_path = os.path.join(Main_path, self.config['directories']['csv'], self.config['filenames']['Grideye'])
        except Exception as e:
            logging.error(f"Error initializing GridEyeDatabase: {str(e)}")
            raise GridEyeDatabaseError(f"Error initializing GridEyeDatabase: {str(e)}")

    @staticmethod
    @st.cache_data
    def load_data(csv_path):
        """
        @brief Load and preprocess the Grid-EYE data from a CSV file.
        @param csv_path The path to the CSV file containing the Grid-EYE data.
        @return A pandas DataFrame containing the processed Grid-EYE data.
        """
        try:
            df = pd.read_csv(csv_path, parse_dates=['timestamp'])
            df['avg_temp'] = df.iloc[:, 2:].mean(axis=1)  # Calculate average temperature
            return df
        except Exception as e:
            logging.error(f"Error loading data: {str(e)}")
            return None

    def run(self):
        """
        @brief Run the Streamlit application for Grid-EYE data visualization.

        This method sets up the Streamlit interface, loads the data,
        and creates interactive visualizations for the Grid-EYE sensor data.
        """
        st.write("""
        # Grid-EYE Database

        This is the Grid-EYE database page. You can visualize the **evolution of data** during a session.
        """)
        try:
            df = self.load_data(self.csv_path)

            start_date = st.date_input("Start date", df['timestamp'].min().date())
            end_date = st.date_input("End date", df['timestamp'].max().date())

            filtered_df = df[(df['timestamp'].dt.date >= start_date) & (df['timestamp'].dt.date <= end_date)]

            st.subheader("Temperature Evolution Over Time")
            fig = px.line(filtered_df, x='timestamp', y=['thermistor', 'avg_temp'],
                          labels={'value': 'Temperature', 'variable': 'Sensor'},
                          title='Thermistor and Average Cell Temperature Over Time')
            st.plotly_chart(fig, use_container_width=True)

            if st.checkbox("Show raw data"):
                st.subheader("Raw data")
                st.write(filtered_df)

            if st.button("Download filtered data as CSV"):
                csv = filtered_df.to_csv(index=False)
                st.download_button(
                    label="Download CSV",
                    data=csv,
                    file_name="filtered_miu_data.csv",
                    mime="text/csv",
                )
        except Exception as e:
            st.write(f"Error running application: {str(e)}")
            logging.error(f"Error running application: {str(e)}")

def main():
    """
    @brief The main function to run the GridEyeDatabase application.

    This function initializes and runs the GridEyeDatabase application.
    """
    try:
        app = GridEyeDatabase()
        app.run()
    except GridEyeDatabaseError as e:
        logging.error(f"Error running GridEyeDatabase: {str(e)}")
        st.error(f"Error running GridEyeDatabase: {str(e)}")

if __name__ == "__main__":
    main()