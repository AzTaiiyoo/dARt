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
   git clone https://github.com/your-repo/dARt.git
   ```

## Configuration

Before running the application, you will need to modify the `config.json` file to set up the sensors you intend to use.

### Example 1: Grideye Only

To use only Grideye sensors:

1. Open the `config.json` file and navigate to the `devices` section.
2. Locate the section labeled `device: "Grideye"`.
3. Set the `amount` variable to the number of Grideye sensors you want to use (e.g., 4).
4. Set the `live` variable to `true` if you want to enable real-time data transfer via Wi-Fi.

Example:

```json
{
  "device": "Grideye",
  "amount": 4,
  "active": true,
  "live": true
}
```

5. Save your changes and proceed to the application UI. Select the Grideye option, click start, and the system will initialize your Grideye sensors.

### Example 2: Multiple Sensors

To use multiple sensors (e.g., 2 Grideye, 1 Myo, and 5 SEN55):

1. Open the `config.json` file and edit each sensor's section in the `devices` block.
2. Set the `amount` variable for each sensor:
   - `amount: 2` for Grideye,
   - `amount: 1` for Myo,
   - `amount: 5` for SEN55.
3. If real-time data transfer is required for any of the sensors, set the `live` variable to `true` for those sensors.

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
```

4. In the application's UI, select the desired sensors (e.g., Grideye, Myo, and SEN55) and click start. The system will initialize the selected sensors for use.

## Usage

1. After configuring the `config.json` file, launch the application through the command line or executable.
2. In the UI:
   - Select the sensors you want to activate.
   - Click Start to initialize the sensors and begin data collection.
   - To stop the session, click Stop Session.
3. Data will be collected and transferred as per the configured settings.

## Limitations

Currently, the dARt application is designed to support a maximum of 1 Grideye and 1 Myo sensor at a time due to hardware limitations during development. However, the code is capable of handling multiple instances of these sensors. If you have more than one available, you can modify the following files to remove this limitation:

- `Configuration.py`
- `dart_GUI`

By adjusting these files, you can increase the number of supported Grideye and Myo sensors.
