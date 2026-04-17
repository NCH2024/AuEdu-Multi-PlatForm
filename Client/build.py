import os
import shutil
import subprocess
import json
import sys

VERSION_FILE = "version.json"

# ===== LOAD VERSION =====
def load_version():
    if not os.path.exists(VERSION_FILE):
        return {"major": 0, "minor": 2, "patch": 1, "build": 1}
    with open(VERSION_FILE, "r") as f:
        return json.load(f)

# ===== SAVE VERSION =====
def save_version(v):
    with open(VERSION_FILE, "w") as f:
        json.dump(v, f)

# ===== UPDATE VERSION =====
def update_version(mode):
    v = load_version()

    if mode == 0:  # patch
        v["patch"] += 1

    elif mode == 1:  # minor
        v["minor"] += 1
        v["patch"] = 0

    elif mode == 2:  # major
        v["major"] += 1
        v["minor"] = 0
        v["patch"] = 0

    v["build"] += 1

    save_version(v)

    version_name = f'{v["major"]}.{v["minor"]}.{v["patch"]:03}'
    version_code = str(v["build"])

    return version_name, version_code

# ===== CLEAN =====
def clean():
    print("Cleaning...")
    for folder in ["build", ".flet"]:
        if os.path.exists(folder):
            shutil.rmtree(folder, ignore_errors=True)

# ===== BUILD =====
def build(version_name, version_code):
    print(f"Building APK {version_name} ({version_code})...")

    cmd = [
        "flet", "build", "apk",

        "--product", "AuEdu",
        "--org", "com.nch2024",

        "--build-version", version_name,
        "--build-number", version_code,

        "--permissions", "camera",
        "--permissions", "location",

        "--splash-color", "#ffffff",
        "--clear-cache"
    ]

    subprocess.run(cmd, check=True)

# ===== FIX INTERNET =====
def fix_manifest():
    manifest = "build/flutter/android/app/src/main/AndroidManifest.xml"

    if not os.path.exists(manifest):
        return

    with open(manifest, "r", encoding="utf-8") as f:
        content = f.read()

    if "android.permission.INTERNET" not in content:
        content = content.replace(
            "<manifest",
            '<manifest xmlns:android="http://schemas.android.com/apk/res/android">\n'
            '    <uses-permission android:name="android.permission.INTERNET"/>'
        )

        with open(manifest, "w", encoding="utf-8") as f:
            f.write(content)

# ===== MAIN =====
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python build.py [0|1|2]")
        print("0 = patch | 1 = minor | 2 = major")
        sys.exit(1)

    mode = int(sys.argv[1])

    version_name, version_code = update_version(mode)

    clean()
    build(version_name, version_code)
    fix_manifest()

    print(f"DONE Version: {version_name} ({version_code})")