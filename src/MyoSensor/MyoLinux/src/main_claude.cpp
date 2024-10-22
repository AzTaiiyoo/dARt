#include "myoclient.h"
#include "serial.h"
#include <fstream>
#include <iomanip>
#include <ctime>
#include <chrono>
#include <thread>
#include <csignal>

using namespace myolinux;

volatile sig_atomic_t stop = 0;

void signal_handler(int signal) {
    stop = 1;
}

int main()
{
    // Set up signal handler for graceful shutdown
    std::signal(SIGINT, signal_handler);

    myo::Client client(Serial{"/dev/ttyACM0", 115200});
    
    // Autoconnect to the first Myo device
    client.connect();
    if (!client.connected()) {
        return 1;
    }

    // Generate a unique filename with timestamp
    auto t = std::time(nullptr);
    auto tm = *std::localtime(&t);
    std::ostringstream oss;
    oss << "myo_data_" << std::put_time(&tm, "%Y%m%d_%H%M%S") << ".csv";
    std::string filename = oss.str();

    // Open CSV file
    std::ofstream csv_file(filename, std::ios::app);
    
    
    // Write CSV header
    csv_file << "Timestamp,EMG1,EMG2,EMG3,EMG4,EMG5,EMG6,EMG7,EMG8,";
    csv_file << "OrientationW,OrientationX,OrientationY,OrientationZ,";
    csv_file << "AccX,AccY,AccZ,";
    csv_file << "GyroX,GyroY,GyroZ" << std::endl;

    // Set sleep mode
    client.setSleepMode(myo::SleepMode::NeverSleep);

    // Read EMG and IMU
    client.setMode(myo::EmgMode::SendEmg, myo::ImuMode::SendData, myo::ClassifierMode::Disabled);

    std::array<int, 8> emg_data;
    myo::OrientationSample ori_data;
    myo::AccelerometerSample acc_data;
    myo::GyroscopeSample gyr_data;

    client.onEmg([&emg_data](myo::EmgSample sample)
    {
        for (std::size_t i = 0; i < 8; i++) {
            emg_data[i] = static_cast<int>(sample[i]);
        }
    });

    client.onImu([&ori_data, &acc_data, &gyr_data](myo::OrientationSample ori, myo::AccelerometerSample acc, myo::GyroscopeSample gyr)
    {
        ori_data = ori;
        acc_data = acc;
        gyr_data = gyr;
    });

    auto last_write_time = std::chrono::steady_clock::now();

    while (!stop) {
        client.listen();

        auto current_time = std::chrono::steady_clock::now();
        if (std::chrono::duration_cast<std::chrono::milliseconds>(current_time - last_write_time).count() >= 10) {
            // Get current timestamp
            auto now = std::chrono::system_clock::now();
            auto now_ms = std::chrono::time_point_cast<std::chrono::milliseconds>(now);
            auto value = now_ms.time_since_epoch();
            long long timestamp = value.count();

            // Write data to CSV
            csv_file << timestamp << ",";
            for (int j = 0; j < 8; j++) {
                csv_file << emg_data[j] << ",";
            }
            csv_file << ori_data[0] << "," << ori_data[1] << "," << ori_data[2] << "," << ori_data[3] << ",";
            csv_file << acc_data[0] << "," << acc_data[1] << "," << acc_data[2] << ",";
            csv_file << gyr_data[0] << "," << gyr_data[1] << "," << gyr_data[2] << std::endl;

            last_write_time = current_time;
        }

        // Small delay to prevent CPU overload
        std::this_thread::sleep_for(std::chrono::milliseconds(1));
    }

    csv_file.close();
    client.disconnect();

    std::cout << "Program terminated gracefully." << std::endl;

    return 0;
}
