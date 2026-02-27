"""
FreeYourHand - py2app 打包設定
生成 FreeYourHand.app 獨立應用程式。
"""

from setuptools import setup

APP = ["main.py"]
DATA_FILES = []
OPTIONS = {
    "argv_emulation": False,
    "iconfile": None,  # TODO: Add .icns icon file
    "plist": {
        "CFBundleName": "FreeYourHand",
        "CFBundleDisplayName": "FreeYourHand",
        "CFBundleIdentifier": "com.freeyourhand.app",
        "CFBundleVersion": "1.0.0",
        "CFBundleShortVersionString": "1.0.0",
        "LSMinimumSystemVersion": "12.0",
        "LSUIElement": True,  # Menu bar app (no dock icon)
        "NSMicrophoneUsageDescription": (
            "FreeYourHand needs microphone access for voice input."
        ),
        "NSAppleEventsUsageDescription": (
            "FreeYourHand needs automation access to simulate "
            "keyboard input (Cmd+V paste)."
        ),
    },
    "packages": [
        "app",
        "PyQt6",
        "pynput",
        "mlx_whisper",
        "google",
        "pyaudio",
    ],
    "includes": [
        "app.core",
        "app.ui",
        "app.utils",
    ],
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
