# ⚡ Watts Live MQTT BLE Config

A cross-platform desktop tool to configure **Watts Live** IoT devices over **Bluetooth Low Energy (BLE)** and monitor **MQTT messages** in real time.

This app allows you to scan for BLE-enabled Watts Live devices, enter MQTT connection credentials, write them to the device, and optionally connect to your MQTT broker to view live measurement messages.

---

## ✨ Features

- 🔍 Scan for nearby **BLE devices** (e.g., “Watts Live”)
- 🔗 Connect and write **MQTT configuration** to the device:
  - Hostname  
  - Port  
  - Username  
  - Password
- ⚙️ Subscribe to an MQTT topic automatically:
  - Uses a **Serial Number** entered by the user  
  - Topic format: `watts/<serial_number>/measurement`
- 🧩 Built-in **Activity Log** to display:
  - BLE connection status  
  - Write progress  
  - Live MQTT messages
- 🖥️ **Modern, dark-themed GUI** built with [ttkbootstrap](https://github.com/israel-dryer/ttkbootstrap)
- ✅ Input validation with real-time feedback and friendly error highlights
- 🪶 Cross-platform (Windows, macOS, Linux)

---

## 🖥️ Desktop GUI Version (Python)

### Requirements

- Python **3.8+**
- BLE-compatible adapter (Bluetooth 4.0+)
- MQTT broker (for listener feature)
- OS: Windows, macOS, or Linux

---

### 🔧 Installation & Usage

```bash
# Clone the repository
git clone https://github.com/DonSidro/watts-live-mqtt-ble-config.git
cd watts-live-mqtt-ble-config

# Install dependencies
pip install -r requirements.txt

# Run the GUI app
python watts_live_gui.py
```

---

## 📦 requirements.txt

```
bleak>=0.22.0
paho-mqtt>=1.6.1
ttkbootstrap>=1.10.1
```

---

## 🚀 Building a Standalone App

You can bundle this app into a standalone `.exe` (Windows) or `.app` (macOS) using [PyInstaller](https://pyinstaller.org/):

```bash
pip install pyinstaller
pyinstaller --noconfirm --onefile --windowed watts_live_gui.py
```

Optionally include an app icon:

```bash
pyinstaller --onefile --windowed --icon=watts_live.ico watts_live_gui.py
```

After building, the executable will appear in the `dist/` folder.

---

## 🔐 BLE Permissions & Notes

### Windows
- Ensure **Bluetooth is enabled**
- Run as administrator if BLE access is restricted

### macOS / Linux
- Bluetooth permissions may require approval via system dialog

---

## 🧠 Technical BLE Info

### Service UUID
```
a2e1ea9b-01e8-4fe5-9b99-35e9cb44d4b6
```

### Characteristic Map

| Field     | Characteristic UUID                             | Format                |
|------------|--------------------------------------------------|------------------------|
| Hostname  | 8143af58-b9b8-47ca-911d-ad3564f10d0b             | UTF-8 string           |
| Port      | c0175553-1ffd-4eb5-99ca-dc271f4ca050             | uint16 (Little Endian) |
| Username  | 41b6703a-0bac-46b4-a0fa-273f5bf641dc             | UTF-8 string           |
| Password  | a59394ed-b929-41a9-81ab-8a16eec6a28c             | UTF-8 string           |

---

## 📡 MQTT Listener Example

| Field | Example |
|-------|----------|
| **Hostname** | `mqtt.myserver.com` |
| **Port** | `1883` |
| **Username** | `admin` |
| **Password** | `secret` |
| **Serial number** | `ABC1234` |
| **Resulting topic** | `watts/ABC1234/measurement` |

Messages from this topic appear live in the **Activity Log** panel.

---

## 📸 Screenshots

### Main App
![Main](images/main.png)

### Activity Log
![Activity Log](images/log.png)

### Activity Log with MQTT Messages
![MQTT](images/mqtt.png)

---

## 📁 Project Structure

```
watts-live-mqtt-ble-config/
├── watts_live_gui.py      # Python GUI app
├── README.md              # This file
├── requirements.txt       # Python dependencies
├── images/                # Screenshots
└── LICENSE
```

---

## 🤖 Development & Contribution

If you’d like to improve the app:

```bash
# Install dependencies
pip install -r requirements.txt

# Run in development mode
python watts_live_gui.py
```

Pull requests and feature improvements are always welcome! 🙌

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).

---

## 👤 Author & Credits

Created by **[Sidon (DonSidro)]**  
Powered by [Bleak](https://github.com/hbldh/bleak), [ttkbootstrap](https://github.com/israel-dryer/ttkbootstrap), and [Paho-MQTT](https://www.eclipse.org/paho/).
