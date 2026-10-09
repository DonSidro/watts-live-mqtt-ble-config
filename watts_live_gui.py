import asyncio
import queue
import threading
import traceback
import tkinter as tk
from tkinter import messagebox
from bleak import BleakScanner, BleakClient
import ttkbootstrap as tb
from ttkbootstrap.constants import *
import paho.mqtt.client as mqtt

CHARACTERISTICS = {
    "hostname": "8143af58-b9b8-47ca-911d-ad3564f10d0b",
    "port":     "c0175553-1ffd-4eb5-99ca-dc271f4ca050",
    "username": "41b6703a-0bac-46b4-a0fa-273f5bf641dc",
    "password": "a59394ed-b929-41a9-81ab-8a16eec6a28c"
}

MAX_LOG_LINES = 2000
UI_POLL_MS = 50

ble_devices = {}
mqtt_client = None
mqtt_running = False
is_busy = False
ui_queue = queue.Queue()

# ──────────────────────────────────────────────────────────────────────────────
# Utility functions
# ──────────────────────────────────────────────────────────────────────────────
def center_window(win, w=1000, h=550):
    win.update_idletasks()
    sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
    x, y = int((sw - w) / 2), int((sh - h) / 2) - 40
    win.geometry(f"{w}x{h}+{x}+{y}")

def run_on_ui(func, *args):
    # Tk is not thread-safe: BLE and MQTT threads queue their UI work here
    # and the main loop picks it up in drain_ui_queue().
    ui_queue.put((func, args))

def drain_ui_queue():
    root.after(UI_POLL_MS, drain_ui_queue)
    while True:
        try:
            func, args = ui_queue.get_nowait()
        except queue.Empty:
            break
        func(*args)

def set_busy(busy: bool):
    global is_busy
    is_busy = busy
    for w in (
        btn_scan, btn_connect, device_combo, entry_hostname, entry_port,
        entry_username, entry_password, btn_show_pw, entry_serial, btn_mqtt_toggle
    ):
        if busy:
            w.config(state=DISABLED)
        else:
            w.config(state="readonly" if w is device_combo else NORMAL)
    if busy:
        progress.start()
        status_var.set("Working…")
    else:
        progress.stop()
        status_var.set("Ready")

def log_message(msg, status=True):
    run_on_ui(append_log, msg, status)

def append_log(msg, status):
    at_bottom = log_text.yview()[1] >= 1.0
    log_text.config(state=NORMAL)
    log_text.insert(END, msg + "\n")
    overflow = int(log_text.index("end-1c").split(".")[0]) - 1 - MAX_LOG_LINES
    if overflow > 0:
        log_text.delete("1.0", f"{overflow + 1}.0")
    if at_bottom:
        log_text.see(END)
    log_text.config(state=DISABLED)
    if status and msg:
        status_var.set(msg.splitlines()[0])

def clear_logs():
    log_text.config(state=NORMAL)
    log_text.delete("1.0", END)
    log_text.config(state=DISABLED)

def copy_logs():
    root.clipboard_clear()
    root.clipboard_append(log_text.get("1.0", END).strip())
    status_var.set("Log copied to clipboard.")

def flash_invalid(widget, ms=1200):
    try:
        widget.configure(bootstyle=DANGER)
        root.after(ms, lambda: widget.configure(bootstyle=""))
    except Exception:
        widget.focus_set()

def parse_port(port_str):
    try:
        port = int(port_str)
    except ValueError:
        return None
    return port if 1 <= port <= 65535 else None

def describe_error(e):
    # some exceptions (e.g. a BLE connect timeout) carry no message
    return str(e) or type(e).__name__

# ──────────────────────────────────────────────────────────────────────────────
# BLE logic
# ──────────────────────────────────────────────────────────────────────────────
def update_device_combo(devices):
    ble_devices.clear()
    ble_devices.update(devices)
    device_combo.configure(values=list(ble_devices.keys()))
    device_var.set(next(iter(ble_devices), "No devices found"))

def scan_ble_devices():
    if is_busy:
        return
    set_busy(True)
    def worker():
        async def scan():
            try:
                log_message("Scanning for BLE devices…")
                devices = await BleakScanner.discover()
                # Watts Live modules first, so one is preselected when present
                named = sorted(
                    (d for d in devices if d.name),
                    key=lambda d: ("watts" not in d.name.lower(), d.name.lower())
                )
                found = {f"{d.name}  [{d.address}]": d.address for d in named}
                run_on_ui(update_device_combo, found)
                log_message("Scan complete." if found else "No devices found.")
            except Exception as e:
                log_message(f"Scan failed: {describe_error(e)}")
                run_on_ui(messagebox.showerror, "Scan failed", describe_error(e))
            finally:
                run_on_ui(set_busy, False)
        asyncio.run(scan())
    threading.Thread(target=worker, daemon=True).start()

def connect_and_write():
    if is_busy:
        return
    selected = device_var.get()
    if selected not in ble_devices:
        messagebox.showerror("Invalid device", "Please select a valid BLE device (scan first).")
        return
    addr = ble_devices[selected]

    hostname = entry_hostname.get().strip()
    port_str = entry_port.get().strip()
    username = entry_username.get().strip()
    password = entry_password.get()

    if not hostname or not port_str:
        messagebox.showerror("Missing info", "Hostname and port are required.")
        if not hostname:
            flash_invalid(entry_hostname)
        if not port_str:
            flash_invalid(entry_port)
        return

    port = parse_port(port_str)
    if port is None:
        flash_invalid(entry_port)
        messagebox.showerror("Invalid port", "Port must be a number between 1 and 65535.")
        return

    if password and not username:
        flash_invalid(entry_username)
        messagebox.showerror("Missing username", "MQTT does not allow a password without a username.")
        return

    if not password and not messagebox.askyesno(
        "No password",
        "No password entered. This only works if your broker allows it.\n\n"
        "Write the configuration anyway?"
    ):
        return

    set_busy(True)
    log_message("Starting BLE write task…")

    def worker():
        async def ble_task():
            try:
                log_message(f"Connecting to {selected}…")
                async with BleakClient(addr) as client:
                    log_message("Connected. Writing values…")
                    values = {
                        CHARACTERISTICS["hostname"]: hostname.encode("utf-8"),
                        CHARACTERISTICS["port"]: port.to_bytes(2, byteorder="little"),
                        CHARACTERISTICS["username"]: username.encode("utf-8"),
                        CHARACTERISTICS["password"]: password.encode("utf-8"),
                    }
                    for uuid, val in values.items():
                        log_message(f"Writing to {uuid}…")
                        await client.write_gatt_char(uuid, val)
                    log_message("All values written successfully.")
                run_on_ui(messagebox.showinfo, "Success", "All values written.")
            except Exception as e:
                log_message(f"Write failed: {describe_error(e)}")
                log_message(traceback.format_exc(), status=False)
                run_on_ui(messagebox.showerror, "BLE Error", describe_error(e))
            finally:
                run_on_ui(set_busy, False)
        asyncio.run(ble_task())
    threading.Thread(target=worker, daemon=True).start()

# ──────────────────────────────────────────────────────────────────────────────
# MQTT logic
# ──────────────────────────────────────────────────────────────────────────────
def build_topic_from_serial():
    serial = entry_serial.get().strip()
    return f"watts/{serial}/measurement" if serial else None

# The callbacks below run on paho's network thread. The topic is handed over as
# userdata when the listener starts, so they never read from the Tk widgets.
def mqtt_on_connect(client, userdata, flags, reason_code, properties):
    if reason_code.is_failure:
        log_message(f"MQTT: Connection refused ({reason_code}).")
        return
    log_message("MQTT: Connected successfully.")
    try:
        client.subscribe(userdata, qos=0)
        log_message(f"MQTT: Subscribed to '{userdata}'.")
    except Exception as e:
        log_message(f"MQTT: Subscribe failed: {e}")

def mqtt_on_connect_fail(client, userdata):
    log_message("MQTT: Could not reach the broker, retrying…")

def mqtt_on_message(client, userdata, msg):
    try:
        payload = msg.payload.decode("utf-8", errors="replace")
    except Exception:
        payload = str(msg.payload)
    log_message(f"[{msg.topic}] {payload}", status=False)

def mqtt_on_disconnect(client, userdata, flags, reason_code, properties):
    if reason_code.is_failure:
        log_message("MQTT: Connection lost, retrying…")
    else:
        log_message("MQTT: Disconnected.")

def start_mqtt_listener():
    global mqtt_client, mqtt_running
    if mqtt_running:
        return

    host = entry_hostname.get().strip()
    port_str = entry_port.get().strip()
    user = entry_username.get().strip()
    pwd = entry_password.get()
    topic = build_topic_from_serial()

    missing = False
    if not host:
        flash_invalid(entry_hostname)
        missing = True
    if not port_str:
        flash_invalid(entry_port)
        missing = True
    if not topic:
        flash_invalid(entry_serial)
        missing = True
    if missing:
        log_message("Please enter Hostname, Port, and Serial number before starting the listener.")
        return

    port = parse_port(port_str)
    if port is None:
        flash_invalid(entry_port)
        messagebox.showerror("Invalid port", "Port must be a number between 1 and 65535.")
        return

    mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, userdata=topic)
    if user or pwd:
        mqtt_client.username_pw_set(user, pwd)

    mqtt_client.on_connect = mqtt_on_connect
    mqtt_client.on_connect_fail = mqtt_on_connect_fail
    mqtt_client.on_message = mqtt_on_message
    mqtt_client.on_disconnect = mqtt_on_disconnect

    try:
        mqtt_client.connect_async(host, port, keepalive=60)
    except Exception as e:
        log_message(f"MQTT: Connect error: {e}")
        return

    mqtt_client.loop_start()
    mqtt_running = True
    btn_mqtt_toggle.config(text="Stop Topic Listener", bootstyle=DANGER)
    log_message(f"MQTT: Connecting to {host}:{port}… (topic will be '{topic}')")

def stop_mqtt_listener():
    global mqtt_client, mqtt_running
    if not mqtt_running:
        return
    try:
        if mqtt_client is not None:
            mqtt_client.disconnect()
            mqtt_client.loop_stop()
    except Exception as e:
        log_message(f"MQTT: Error while stopping: {e}")
    finally:
        mqtt_client = None
        mqtt_running = False
        btn_mqtt_toggle.config(text="▶ Start Topic Listener", bootstyle=INFO)
        log_message("MQTT: Listener stopped.")

def toggle_mqtt():
    if mqtt_running:
        stop_mqtt_listener()
    else:
        start_mqtt_listener()

def on_close():
    stop_mqtt_listener()
    root.destroy()

# ──────────────────────────────────────────────────────────────────────────────
# UI BUILD
# ──────────────────────────────────────────────────────────────────────────────
root = tb.Window(themename="darkly")
root.title("Watts Live — MQTT BLE Config")

ICON_IMG = tk.PhotoImage(width=1, height=1)
try:
    root.iconphoto(True, ICON_IMG)
except Exception:
    pass

root.rowconfigure(1, weight=1)
root.columnconfigure(0, weight=1)

toolbar = tb.Frame(root, padding=(12, 10))
toolbar.grid(row=0, column=0, sticky="ew")
btn_scan = tb.Button(toolbar, text="Scan Devices", command=scan_ble_devices, bootstyle=INFO, width=18)
btn_scan.grid(row=0, column=0, sticky="w")

content = tb.Frame(root, padding=(16, 10, 16, 10))
content.grid(row=1, column=0, sticky="nsew")
content.columnconfigure(0, weight=2, uniform="panels")
content.columnconfigure(1, weight=3, uniform="panels")
content.rowconfigure(0, weight=1)

# Left Panel
form_card = tb.Labelframe(content, text=" Device & Credentials ", bootstyle=PRIMARY, padding=16)
form_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
form_card.columnconfigure(1, weight=1)

tb.Label(form_card, text="BLE Device").grid(row=0, column=0, sticky="w", pady=(0, 6))
device_var = tk.StringVar(value="Click ‘Scan Devices’")
device_combo = tb.Combobox(form_card, textvariable=device_var, state="readonly")
device_combo.grid(row=0, column=1, sticky="ew", padx=(8, 0), pady=(0, 6))

tb.Separator(form_card).grid(row=1, column=0, columnspan=3, sticky="ew", pady=(8, 12))

tb.Label(form_card, text="Hostname").grid(row=2, column=0, sticky="w", pady=6)
entry_hostname = tb.Entry(form_card)
entry_hostname.grid(row=2, column=1, sticky="ew", pady=6)

tb.Label(form_card, text="Port").grid(row=3, column=0, sticky="w", pady=6)
entry_port = tb.Entry(form_card)
entry_port.grid(row=3, column=1, sticky="ew", pady=6)

tb.Label(form_card, text="Username").grid(row=4, column=0, sticky="w", pady=6)
entry_username = tb.Entry(form_card)
entry_username.grid(row=4, column=1, sticky="ew", pady=6)

tb.Label(form_card, text="Password").grid(row=5, column=0, sticky="w", pady=6)
pw_visible = tk.BooleanVar(value=False)
def toggle_pw():
    pw_visible.set(not pw_visible.get())
    if pw_visible.get():
        entry_password.configure(show="")
        btn_show_pw.configure(text="Hide")
    else:
        entry_password.configure(show="•")
        btn_show_pw.configure(text="Show")
entry_password = tb.Entry(form_card, show="•")
entry_password.grid(row=5, column=1, sticky="ew", pady=6)
btn_show_pw = tb.Button(
    form_card,
    text="Show",
    command=toggle_pw,
    bootstyle=SECONDARY
)
btn_show_pw.grid(row=5, column=2, padx=(8, 0), pady=6, sticky="e")

tb.Separator(form_card).grid(row=6, column=0, columnspan=3, sticky="ew", pady=(10, 12))

tb.Label(form_card, text="Serial").grid(row=7, column=0, sticky="w", pady=6)
entry_serial = tb.Entry(form_card)
entry_serial.grid(row=7, column=1, sticky="ew", pady=6)

btn_mqtt_toggle = tb.Button(form_card, text="Start Topic Listener", command=toggle_mqtt, bootstyle=INFO)
btn_mqtt_toggle.grid(row=8, column=0, columnspan=3, sticky="ew", pady=(6, 4))

btn_connect = tb.Button(form_card, text="Connect & Write (Ctrl+Enter)",
                        command=connect_and_write, bootstyle=SUCCESS)
btn_connect.grid(row=9, column=0, columnspan=3, sticky="ew", pady=(12, 8))
progress = tb.Progressbar(form_card, mode="indeterminate", bootstyle="info-striped")
progress.grid(row=10, column=0, columnspan=3, sticky="ew")

# Right Panel (Logs)
log_card = tb.Labelframe(content, text=" Activity Log ", bootstyle=INFO, padding=12)
log_card.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
log_card.columnconfigure(0, weight=1)
log_card.rowconfigure(1, weight=1)

log_text = tk.Text(log_card, height=18, width=40, wrap="word", state=DISABLED, relief="flat")
log_text.grid(row=1, column=0, sticky="nsew", pady=(6, 8))
log_scroll = tb.Scrollbar(log_card, command=log_text.yview)
log_scroll.grid(row=1, column=1, sticky="ns", pady=(6, 8))
log_text.configure(yscrollcommand=log_scroll.set)

log_actions = tb.Frame(log_card)
log_actions.grid(row=2, column=0, columnspan=2, sticky="ew")
tb.Button(log_actions, text="Clear", command=clear_logs, bootstyle=SECONDARY)\
    .grid(row=0, column=0, sticky="w", padx=(0, 6))
tb.Button(log_actions, text="Copy", command=copy_logs, bootstyle=OUTLINE)\
    .grid(row=0, column=2, sticky="e")

status = tb.Frame(root, padding=(14, 6))
status.grid(row=2, column=0, sticky="ew")
status_var = tk.StringVar(value="Ready")
tb.Label(status, textvariable=status_var, bootstyle=SECONDARY).grid(row=0, column=0, sticky="w")

root.bind("<Control-Return>", lambda e: connect_and_write())
root.bind("<Control-r>", lambda e: scan_ble_devices())
root.protocol("WM_DELETE_WINDOW", on_close)

center_window(root, 1000, 550)
drain_ui_queue()
root.after(300, scan_ble_devices)
root.mainloop()
