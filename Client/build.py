import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


REQUIRED_FLET_VERSION = "0.85.0"

APP_DIR = Path(__file__).resolve().parent
VERSION_FILE = APP_DIR / "version.json"
PYPROJECT_FILE = APP_DIR / "pyproject.toml"
DIST_DIR = APP_DIR / "dist"

PROJECT_NAME = "auedu"
PRODUCT_NAME = "AuEdu"
ARTIFACT_NAME = "AuEdu"
DESCRIPTION = "AuEdu attendance client"
ORG_NAME = "com.nch2024"
ANDROID_BUNDLE_ID = "com.nch2024.auedu"
COMPANY_NAME = "NCH2024"
COPYRIGHT = "Copyright (C) 2026 NCH2024"
SPLASH_COLOR = "#ffffff"

TARGETS = ("apk", "windows")
VERSION_MODES = {
    "0": "patch",
    "1": "minor",
    "2": "major",
    "patch": "patch",
    "minor": "minor",
    "major": "major",
}


def load_version():
    if VERSION_FILE.exists():
        with VERSION_FILE.open("r", encoding="utf-8") as file:
            return json.load(file)
    return {"major": 0, "minor": 1, "patch": 0, "build": 0}


def save_version(version):
    with VERSION_FILE.open("w", encoding="utf-8") as file:
        json.dump(version, file, indent=4)


def save_pyproject_version(version_name, version_code):
    if not PYPROJECT_FILE.exists():
        return

    lines = PYPROJECT_FILE.read_text(encoding="utf-8").splitlines()
    section = None
    updated = []

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            section = stripped
        elif section == "[project]" and stripped.startswith("version ="):
            line = f'version = "{version_name}"'
        elif section == "[tool.flet.android]" and stripped.startswith("version_code ="):
            line = f"version_code = {version_code}"
        elif section == "[tool.flet.android]" and stripped.startswith("version_name ="):
            line = f'version_name = "{version_name}"'

        updated.append(line)

    PYPROJECT_FILE.write_text("\n".join(updated) + "\n", encoding="utf-8")


def bump_version(version, mode):
    version = dict(version)
    if mode == "major":
        version["major"] += 1
        version["minor"] = 0
        version["patch"] = 0
    elif mode == "minor":
        version["minor"] += 1
        version["patch"] = 0
    elif mode == "patch":
        version["patch"] += 1
    else:
        raise ValueError(f"Unsupported version mode: {mode}")

    version["build"] += 1
    return version


def version_values(version):
    version_name = f"{version['major']}.{version['minor']}.{version['patch']}"
    version_code = str(version["build"])
    return version_name, version_code


import os
import stat


def remove_readonly(func, path, excinfo):
    os.chmod(path, stat.S_IWRITE)
    func(path)


def clean(targets):
    paths = [APP_DIR / "build", APP_DIR / ".flet"]
    paths.extend(DIST_DIR / target for target in targets)

    for path in paths:
        if path.exists():
            shutil.rmtree(path, onerror=remove_readonly)
            print(f"Removed {path}")


def run_command(command, cwd=APP_DIR, dry_run=False):
    display = " ".join(f'"{part}"' if " " in part else part for part in command)
    if dry_run:
        print(display)
        return

    print(display)
    import os
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    subprocess.run(command, cwd=cwd, check=True, env=env)


def command_output(command):
    try:
        result = subprocess.run(
            command,
            cwd=APP_DIR,
            check=True,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None
    return result.stdout.strip() or result.stderr.strip()


def parse_version_text(text):
    for token in text.replace("\n", " ").split():
        candidate = token.strip("vV,;:()[]")
        parts = candidate.split(".")
        if len(parts) == 3 and all(part.isdigit() for part in parts):
            return candidate
    return text.strip()


def find_flet_command():
    venv_flet = Path(sys.executable).parent / "flet"
    if sys.platform == "win32":
        venv_flet_bin = Path(sys.executable).parent / "flet.exe"
    else:
        venv_flet_bin = venv_flet

    candidates = []
    if venv_flet_bin.exists():
        candidates.append([str(venv_flet_bin)])
    candidates.extend(([sys.executable, "-m", "flet"], ["flet"]))

    for command in candidates:
        output = command_output([*command, "--version"])
        if output:
            return list(command), parse_version_text(output)
    return None, None


def ensure_flet_version(allow_mismatch=False, dry_run=False):
    if dry_run:
        return [sys.executable, "-m", "flet"]

    command, version = find_flet_command()
    if not command:
        raise RuntimeError(
            "Flet CLI was not found. Install the client dependencies first:\n"
            "  python -m pip install -r requirements.txt"
        )

    if version != REQUIRED_FLET_VERSION and not allow_mismatch:
        raise RuntimeError(
            f"Flet {REQUIRED_FLET_VERSION} is required, but found {version}.\n"
            "Use --allow-flet-version-mismatch only if you intentionally want to build with this version."
        )

    return command


def build_command(target, version_name, version_code, flet_command, clear_cache, skip_flutter_doctor):
    command = [
        *flet_command,
        "build",
        target,
        str(APP_DIR),
        "--project",
        PROJECT_NAME,
        "--product",
        PRODUCT_NAME,
        "--artifact",
        ARTIFACT_NAME,
        "--description",
        DESCRIPTION,
        "--build-version",
        version_name,
        "--build-number",
        version_code,
        "--module-name",
        "main",
        "--output",
        str(DIST_DIR / target),
        "--no-rich-output",
        "--yes",
    ]

    if clear_cache:
        command.append("--clear-cache")
    if skip_flutter_doctor:
        command.append("--skip-flutter-doctor")

    if target == "apk":
        command.extend(
            [
                "--org",
                ORG_NAME,
                "--bundle-id",
                ANDROID_BUNDLE_ID,
                "--splash-color",
                SPLASH_COLOR,
                "--permissions",
                "camera",
                "location",
                "--android-permissions",
                "android.permission.INTERNET=true",
            ]
        )
    elif target == "windows":
        command.extend(
            [
                "--company",
                COMPANY_NAME,
                "--copyright",
                COPYRIGHT,
            ]
        )
    else:
        raise ValueError(f"Unsupported build target: {target}")

    return command


def fix_android_manifest():
    manifest_path = APP_DIR / "build" / "flutter" / "android" / "app" / "src" / "main" / "AndroidManifest.xml"
    if not manifest_path.exists():
        return

    content = manifest_path.read_text(encoding="utf-8")
    permission = '<uses-permission android:name="android.permission.INTERNET"/>'
    if "android.permission.INTERNET" in content:
        return

    manifest_start = content.find("<manifest")
    manifest_end = content.find(">", manifest_start)
    if manifest_start == -1 or manifest_end == -1:
        return

    content = content[: manifest_end + 1] + f"\n    {permission}" + content[manifest_end + 1 :]
    manifest_path.write_text(content, encoding="utf-8")
    print("Ensured Android INTERNET permission.")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Build AuEdu with Flet 0.85.0.",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python build.py 0\n"
            "  python build.py patch windows\n"
            "  python build.py minor all\n"
            "  python build.py --no-version-bump windows\n"
            "  python build.py patch windows --dry-run"
        ),
    )
    parser.add_argument(
        "items",
        nargs="*",
        metavar="mode/target",
        help="Optional version bump and target. Modes: 0/patch, 1/minor, 2/major. Targets: apk, windows, all.",
    )
    parser.add_argument(
        "--no-version-bump",
        action="store_true",
        help="Use the current version.json values without incrementing them.",
    )
    parser.add_argument(
        "--no-clean",
        action="store_true",
        help="Do not remove previous local Flet build output before building.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the Flet build command without changing files or building.",
    )
    parser.add_argument(
        "--allow-flet-version-mismatch",
        action="store_true",
        help=f"Allow building with a Flet CLI version other than {REQUIRED_FLET_VERSION}.",
    )
    parser.add_argument(
        "--skip-flutter-doctor",
        action="store_true",
        help="Pass --skip-flutter-doctor to Flet.",
    )
    parser.add_argument(
        "--keep-flet-cache",
        action="store_true",
        help="Do not pass --clear-cache to Flet.",
    )
    args = parser.parse_args()
    mode = "patch"
    target = "apk"
    has_mode = False
    has_target = False

    for item in args.items:
        if item in VERSION_MODES:
            if has_mode:
                parser.error("Only one version mode can be provided.")
            mode = VERSION_MODES[item]
            has_mode = True
        elif item in (*TARGETS, "all"):
            if has_target:
                parser.error("Only one build target can be provided.")
            target = item
            has_target = True
        else:
            parser.error(f"Unsupported argument: {item}")

    args.mode = mode
    args.target = target
    del args.items
    return args


def main():
    args = parse_args()

    selected_targets = list(TARGETS) if args.target == "all" else [args.target]
    current_version = load_version()
    mode = args.mode

    if args.no_version_bump:
        next_version = current_version
    else:
        next_version = bump_version(current_version, mode)

    version_name, version_code = version_values(next_version)
    print(f"Build version: {version_name} ({version_code})")

    flet_command = ensure_flet_version(
        allow_mismatch=args.allow_flet_version_mismatch,
        dry_run=args.dry_run,
    )

    if not args.no_clean and not args.dry_run:
        clean(selected_targets)

    for target in selected_targets:
        command = build_command(
            target=target,
            version_name=version_name,
            version_code=version_code,
            flet_command=flet_command,
            clear_cache=not args.keep_flet_cache,
            skip_flutter_doctor=args.skip_flutter_doctor,
        )
        run_command(command, dry_run=args.dry_run)
        if target == "apk" and not args.dry_run:
            fix_android_manifest()

    if args.dry_run:
        print("Dry run completed. version.json was not changed.")
    else:
        if not args.no_version_bump:
            save_version(next_version)
            save_pyproject_version(version_name, version_code)
        print("Build completed.")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"Build failed: {error}", file=sys.stderr)
        sys.exit(1)
