# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for the macOS .app bundle.
# Requires PyInstaller >= 6.0 (a.zipfiles / a.zipped_data were dropped in 6.x).
#   pyinstaller --noconfirm watts_live_gui.spec

a = Analysis(
    ['watts_live_gui.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=['ttkbootstrap', 'ttkbootstrap.constants'],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    exclude_binaries=True,
    name='WattsLiveConfig',
    debug=False,
    strip=False,
    upx=False,
    console=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name='WattsLiveConfig',
)

app = BUNDLE(
    coll,
    name='WattsLiveConfig.app',
    bundle_identifier='com.watts.liveconfig',
    info_plist={
        # macOS 11+ terminates any process that touches CoreBluetooth without
        # these strings, so BLE scanning fails silently if they are missing.
        'NSBluetoothAlwaysUsageDescription':
            'Needed to configure the Watts Live module over Bluetooth.',
        'NSBluetoothPeripheralUsageDescription':
            'Needed to configure the Watts Live module over Bluetooth.',
        'LSMinimumSystemVersion': '11.0',
        'NSHighResolutionCapable': True,
    },
)
