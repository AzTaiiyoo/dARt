"""
@brief dARt Toolkit: A Streamlit application for sensor activation and database visualization.

This module provides the entry point for the dARt Toolkit application.

@author [Your Name]
@date [Current Date]
@version 2.2
"""

import streamlit as st
from dart_GUI import dARtToolkit, dARtToolkitError

def main():
    try:
        app = dARtToolkit()
        app.run()
    except dARtToolkitError as e:
        st.error(f"Critical error: {str(e)}")
    except Exception as e:
        st.error(f"An unexpected critical error occurred: {str(e)}")
        
if __name__ == "__main__":
    main()