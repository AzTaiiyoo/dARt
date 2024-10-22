# dARt Application

## Overview

The **dARt application** is designed to interface with multiple types of sensors, including **Grideye**, **SEN55**, **Myo**, and **Wood Plank** sensors. It allows for configuring the number of sensors and enabling real-time data transfer over Wi-Fi. The system can be adjusted via the `config.json` file and operated through the application's UI.

## Table of Contents

- [Installation](#installation)
- [Configuration](#configuration)
  - [Example 1: Grideye Only](#example-1-grideye-only)
  - [Example 2: Multiple Sensors](#example-2-multiple-sensors)
- [Usage](#usage)
- [Limitations](#limitations)

## Installation

1. Clone the repository to your local machine:

   ```bash
   git clone https://github.com/AzTaiiyoo/dARt.git
   ```

2. Create a python environment:

   A python environment containing all dependencies is already provided with the repository. However, it
   might happen depending on your OS that the environment will not be working properly. If that happens,
   follow these instruction to create a custom python environment:

   ```bash
   python -m venv dependencies/name_of_your_environment
   ```

   Then activate it:

   ```bash
   source dependencies/name_of_your_environment/bin/activate // On linux/MacOS
   source dependencies/name_of_your_environment/Scripts/activate // On Windows
   ```

3. Install dependencies:
   To install the dependencies, you can either install them all at once using the requirement file such as:

   ```bash
   pip install --no-cache-dir -r requirements.txt
   ```

   Or do it manually using the _pip install_ command for each package in the requirements.txt file.

   **Warning**:
   Due to some compatibility issues from the factory Grid-EYE code, you might encounter an error a `serial`error when running the app. If that happens, you have to run the following commands:

   ```bash
   pip install serial // install serial library
   pip install pyserial // install pyserial library
   pip uninstall serial // uninstall serial library
   pip uninstall pyserial // uninstall pyserial
   pip install pyserial // install pyserial library again
   ```

   This should solve the problem.

## Configuration

Before running the application, you will need to modify the `config.json` file to set up the sensors you intend to use.

### Convention rules

The way of declaring sensors in the `config.json` file changes depending on if you wish to use one of the same type of sensors or several. You must respect this convention for the **dARt** to work as intended.

Example 1: Amount set to 1 for a sensor

```json
"ports": [
    {
      "device": "Myo_Sensor",
      "port": "53:89:D1:03:96:F7"
    },
    {
      "device": "SEN55",
      "port": "COM5"
    },
] ...
```

Example 2: Amount set to > 1 for a sensor

```json
"ports":[
  {
    "device": "Grideye_1",
    "port": "COM1"
  },
  {
    "device": "Grideye_2",
    "port": "COM2"
  },
  {
    "device": "Myo_Sensor",
    "port": "53:89:D1:03:96:F7"
  },
  {
    "device": "SEN55_1",
    "port": "53:09:C1:F3:54:F2"
  },
  {
    "device": "SEN55_2",
    "port": "54:F2:11:43:54:F2"
  },
]...

```

### Example 1: Grideye Only

To use only Grideye sensors:

1. Open the `config.json` file and navigate to the `devices` section.
2. Locate the section labeled `device: "Grideye"`.
3. Set the `amount` variable to the number of Grideye sensors you want to use (e.g., 4).
4. Set the `live` variable to `true` if you want to enable real-time data transfer via Wi-Fi.
5. Update ports section following the convention at the beginning of the config.json file or as shown below.

Example:

```json
{
  "device": "Grideye",
  "amount": 4,
  "active": true,
  "live": true
}

"ports":[
  {
    "device": "Grideye_1",
    "port": "COM1"
  },
  {
    "device": "Grideye_2",
    "port": "COM2"
  },
] ...
```

6. Save your changes and proceed to the application UI. Select the Grideye option, click start, and the system will initialize your Grideye sensors.

### Example 2: Multiple Sensors

To use multiple sensors (e.g., 2 Grideye, 1 Myo, and 5 SEN55):

1. Open the `config.json` file and edit each sensor's section in the `devices` block.
2. Set the `amount` variable for each sensor:
   - `amount: 2` for Grideye,
   - `amount: 1` for Myo,
   - `amount: 5` for SEN55.
3. If real-time data transfer is required for any of the sensors, set the `live` variable to `true` for those sensors.
4. Update ports section following the convention at the beginning of the config.json file or as shown below.

Example:

```json
{
  "device": "Grideye",
  "amount": 2,
  "active": true,
  "live": true
},
{
  "device": "Myo",
  "amount": 1,
  "active": true,
  "live": false
},
{
  "device": "SEN55",
  "amount": 5,
  "active": true,
  "live": true
}

"ports":[
  {
    "device": "Grideye_1",
    "port": "COM1"
  },
  {
    "device": "Grideye_2",
    "port": "COM2"
  },
   {
    "device": "SEN55_1",
    "port": "COM2"
  },
  {
    "device": "SEN55_2",
    "port": "COM2"
  },
] ...
```

5. In the application's UI, select the desired sensors (e.g., Grideye, Myo, and SEN55) and click start. The system will initialize the selected sensors for use.

## Usage

1. After configuring the `config.json` file, launch the application through the command using:

```bash
streamlit run src/main.py
```

2. In the UI:
   - Select the sensors you want to activate.
   - Click Start to initialize the sensors and begin data collection.
   - To stop the session, click Stop Session.
3. Data will be collected and transferred as per the configured settings.

## Limitations

Currently, the dARt application is designed to support a maximum of 1 Grideye and 1 Myo sensor at a time due to hardware limitations during development. However, the code is capable of handling multiple instances of these sensors. If you have more than one available, you can modify the following files to remove this limitation:

- `Configuration.py`
- `dart_GUI`

By adjusting these files, you can increase the number of supported **Grideye** and **Myo sensors**.

In addition, the **Myo sensor** library was built to work on Linux and MacOS. This means on Windows, the application will work for every other sensors except for the Myo. Further development using **Docker** might solve that issue.

### Rebuild MyoLinux Library

While this toolkit comes with a functional image for Raspberry Pi 3, you might encounter an "exec format error" when trying to use the Myo Armband on Linux or Mac. In such cases, rebuilding the library might resolve the issue.
Rebuilding Steps

1. Navigate to the MyoLinux source directory:

```bash
src/MyoSensor/MyoLinux/src
```

2. Remove existing CMake cache:

```bash
rm CMakeCache.txt
```

3. Rebuild the library:

```bash
cmake ..
make
make install
```

Compile with C++11 support:

```bash
g++ -std=c++11 main.cpp -o MyoApp -lmyolinux
```

### Setting Library Path

After rebuilding, you need to add the library path to your system. Open a terminal and use the appropriate command for your operating system:

Linux:

```bash
export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:path_to_src_of_MyoLinux/libmyolinux.so
```

macOS:

```bash
export DYLD_LIBRARY_PATH=$DYLD_LIBRARY_PATH:path_to_src_of_MyoLinux/libmyolinux.dylib
```

**Note**: Replace path_to_src_of_MyoLinux with the actual path to your MyoLinux src directory.
