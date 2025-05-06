import asyncio
import tkinter as tk
from tkinter import messagebox, ttk
from bleak import BleakScanner, BleakClient
import threading

CHARACTERISTICS = {
    "hostname": "8143af58-b9b8-47ca-911d-ad3564f10d0b",
    "port":     "c0175553-1ffd-4eb5-99ca-dc271f4ca050",
    "username": "41b6703a-0bac-46b4-a0fa-273f5bf641dc",
    "password": "a59394ed-b929-41a9-81ab-8a16eec6a28c"
}

ble_devices = {}

def log_message(msg):
    def append():
        log_text.config(state='normal')
        log_text.insert(tk.END, msg + '\n')
        log_text.see(tk.END)
        log_text.config(state='disabled')
    root.after(0, append)

def scan_ble_devices():
    async def scan():
        log_message("Scanning for BLE devices...")
        devices = await BleakScanner.discover()
        ble_devices.clear()
        for d in devices:
            if d.name:
                label = f"{d.name} [{d.address}]"
                ble_devices[label] = d.address
        update_device_dropdown()
        log_message("Scan complete. Found devices: " + ", ".join(ble_devices.keys()) if ble_devices else "No devices found.")

    threading.Thread(target=lambda: asyncio.run(scan()), daemon=True).start()

def update_device_dropdown():
    device_menu["menu"].delete(0, "end")
    for label in ble_devices:
        device_menu["menu"].add_command(label=label, command=tk._setit(device_var, label))
    if ble_devices:
        device_var.set(list(ble_devices.keys())[0])
    else:
        device_var.set("No devices found")

def connect_and_write():
    selected = device_var.get()
    if selected not in ble_devices:
        messagebox.showerror("Error", "Please select a valid BLE device.")
        return

    hostname = entry_hostname.get().strip()
    port_str = entry_port.get().strip()
    username = entry_username.get().strip()
    password = entry_password.get().strip()

    if not all([hostname, port_str, username, password]):
        messagebox.showerror("Input Error", "All fields are required.")
        return

    try:
        port = int(port_str)
    except ValueError:
        messagebox.showerror("Input Error", "Port must be a number.")
        return

    btn_connect.config(state='disabled')
    progress.start()
    log_message("Starting BLE write task...")

    def write_task():
        async def ble_task():
            try:
                log_message(f"Connecting to {selected}...")
                async with BleakClient(ble_devices[selected]) as client:
                    log_message("Connected. Writing values...")
                    values = {
                        CHARACTERISTICS["hostname"]: hostname.encode('utf-8'),
                        CHARACTERISTICS["port"]: port.to_bytes(2, byteorder='little'),
                        CHARACTERISTICS["username"]: username.encode('utf-8'),
                        CHARACTERISTICS["password"]: password.encode('utf-8')
                    }
                    for uuid, val in values.items():
                        log_message(f"Writing to {uuid}...")
                        await client.write_gatt_char(uuid, val)
                    log_message("All values written successfully.")
                root.after(0, lambda: messagebox.showinfo("Success", "All values written."))
            except Exception as e:
                log_message(f"Error: {str(e)}")
                root.after(0, lambda: messagebox.showerror("BLE Error", str(e)))
            finally:
                root.after(0, lambda: (
                    progress.stop(),
                    btn_connect.config(state='normal')
                ))

        asyncio.run(ble_task())

    threading.Thread(target=write_task, daemon=True).start()

# GUI layout
root = tk.Tk()
root.title("Watts Live MQTT BLE Config")

tk.Label(root, text="BLE Device:").grid(row=0, column=0, sticky="e")
device_var = tk.StringVar(root)
device_var.set("Click 'Scan Devices'")
device_menu = tk.OptionMenu(root, device_var, "Click 'Scan Devices'")
device_menu.grid(row=0, column=1, sticky="ew")

tk.Button(root, text="🔍 Scan Devices", command=scan_ble_devices).grid(row=0, column=2, padx=5)

tk.Label(root, text="Hostname:").grid(row=1, column=0, sticky="e")
entry_hostname = tk.Entry(root, width=30)
entry_hostname.grid(row=1, column=1, columnspan=2)

tk.Label(root, text="Port:").grid(row=2, column=0, sticky="e")
entry_port = tk.Entry(root, width=30)
entry_port.grid(row=2, column=1, columnspan=2)

tk.Label(root, text="Username:").grid(row=3, column=0, sticky="e")
entry_username = tk.Entry(root, width=30)
entry_username.grid(row=3, column=1, columnspan=2)

tk.Label(root, text="Password:").grid(row=4, column=0, sticky="e")
entry_password = tk.Entry(root, width=30, show="*")
entry_password.grid(row=4, column=1, columnspan=2)

btn_connect = tk.Button(root, text="Connect & Write", command=connect_and_write)
btn_connect.grid(row=5, column=0, columnspan=3, pady=10)

progress = ttk.Progressbar(root, mode='indeterminate')
progress.grid(row=6, column=0, columnspan=3, pady=(0, 5), sticky="ew")

# Log window
log_text = tk.Text(root, height=10, width=60, state='disabled', wrap='word', bg="#f4f4f4")
log_text.grid(row=7, column=0, columnspan=3, padx=5, pady=5, sticky="nsew")

root.grid_rowconfigure(7, weight=1)
root.grid_columnconfigure(1, weight=1)

root.mainloop()
