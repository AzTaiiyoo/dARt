"""
@file SEN55_database.py
@brief A Streamlit application for visualizing SEN55 sensor data.

This module provides a user interface for loading, visualizing, and analyzing
SEN55 sensor data using Streamlit and Plotly.

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

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class SEN55DatabaseError(Exception):
    """Exception personnalisée pour SEN55Database"""
    pass

class SEN55Database:
    """
    @class SEN55Database
    @brief A class for managing and visualizing SEN55 sensor data.

    This class provides methods for loading SEN55 sensor data from a CSV file
    and creating a Streamlit interface to visualize and interact with the data.
    """

    def __init__(self):
        """
        @brief Initialize the SEN55Database object.

        Sets up the configuration and file paths for the SEN55 data.
        """
        try:
            self.ConfigClass = conf.Config()
            self.config = self.ConfigClass.config
            self.directory = self.config['directories']['database']
            self.csv_path = os.path.join(self.config['directories']['csv'], self.config['filenames']['SEN55'])
        except Exception as e:
            logging.error(f"Error initializing SEN55Database: {str(e)}")
            raise SEN55DatabaseError(f"Error initializing SEN55Database: {str(e)}")
    
    @staticmethod
    @st.cache_data
    def load_data(csv_path):
        """
        @brief Load and preprocess the SEN55 data from a CSV file.
        @param csv_path The path to the CSV file containing the SEN55 data.
        @return A pandas DataFrame containing the processed SEN55 data.
        """
        try:
            df = pd.read_csv(csv_path)

            if 'time' not in df.columns:
                st.warning("No 'time' column found in the CSV. Using row numbers as index.")
                df['time'] = range(len(df))
            else:
                try:
                    df['time'] = pd.to_datetime(df['time'])
                except ValueError:
                    st.warning("Unable to parse 'time' column as datetime. Using it as is.")
        except Exception as e:
            logging.error(f"Error loading data: {str(e)}")

        return df

    def run(self):
        """
        @brief Run the Streamlit application for SEN55 data visualization.

        This method sets up the Streamlit interface, loads the data,
        and creates interactive visualizations for the SEN55 sensor data.
        """
        st.write("""
        # SEN55 Database

        This is the SEN55 database page. You can visualize the **evolution of data** during a session.
        """)
        try:
            df = self.load_data(self.csv_path)

            st.subheader("Raw data")
            st.write(df)

            st.subheader("Data Visualization")

            columns_to_plot = st.multiselect("Select columns to plot",
                                            [col for col in df.columns if col != 'time'])

            if columns_to_plot:
                fig = px.line(df, x='time', y=columns_to_plot, title='SEN55 Data Over Time')
                st.plotly_chart(fig)

            st.subheader("Statistics")
            st.write(df.describe())

            st.subheader("Download Data")
            csv = df.to_csv(index=False)
            st.download_button(
                label="Download data as CSV",
                data=csv,
                file_name="SEN55_data.csv",
                mime="text/csv",
            )
        except Exception as e:
            st.write(f"Error running application: {str(e)}")
            logging.error(f"Error running application: {str(e)}")

def main():
    """
    @brief The main function to run the SEN55Database application.

    This function initializes and runs the SEN55Database application.
    """
    try:
        app = SEN55Database()
        app.run()
    except SEN55DatabaseError as e:
        logging.error(f"Error running SEN55Database: {str(e)}")
        st.error(f"Error running SEN55Database: {str(e)}")

if __name__ == "__main__":
    main()
