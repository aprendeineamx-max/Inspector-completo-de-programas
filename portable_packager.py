#!/usr/bin/env python3
"""
Utility to collect program files, registry keys, services and scheduled tasks
into a portable package that can be moved to another machine.

Usage:
    python portable_packager.py config.json --output PortableRoot

See portable_config.sample.json for a template.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List

SUCCESSFUL_ROBOCOPY_CODES = set(range(0, 8))


def expand_path(path: str) -> Path:
    """Expand environment variables and user home markers."""
    expanded = os.path.expanduser(os.path.expandvars(path.strip()))
    return Path(expanded).resolve()


def run_command(cmd: List[str], dry_run: bool = False) -> subprocess.CompletedProcess[str] | None:
    """Run command and return CompletedProcess. Raises on failures."""
    print(f"[cmd] {' '.join(cmd)}")
    if dry_run:
        return None
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore")
    if result.returncode != 0:
        raise RuntimeError(
            f"Command failed with exit code {result.returncode}:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )
    return result


def copy_directory(source: Path, destination: Path, dry_run: bool = False) -> None:
    """Copy directory recursively preserving ACLs and timestamps via robocopy."""
    destination.mkdir(parents=True, exist_ok=True)
    cmd = [
        "robocopy",
        str(source),
        str(destination),
        "/MIR",
        "/COPYALL",
        "/R:2",
        "/W:2",
        "/NFL",
        "/NDL",
        "/NP",
    ]
    print(f"[copy dir] {source} -> {destination}")
    if dry_run:
        return
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore")
    if result.returncode not in SUCCESSFUL_ROBOCOPY_CODES:
        raise RuntimeError(
            f"robocopy failed ({result.returncode}) while copying {source} -> {destination}\n"
            f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )


def copy_file(source: Path, destination: Path, dry_run: bool = False) -> None:
    """Copy single file preserving metadata."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    print(f"[copy file] {source} -> {destination}")
    if dry_run:
        return
    shutil.copy2(source, destination)


def sanitize_name(value: str) -> str:
    """Replace unsupported characters for filenames."""
    keep = []
    for char in value:
        if char.isalnum() or char in ("-", "_", "."):
            keep.append(char)
        else:
            keep.append("_")
    return "".join(keep)


def export_registry(key: str, destination: Path, dry_run: bool = False) -> None:
    """Export registry key using reg.exe."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["reg", "export", key, str(destination), "/y"]
    run_command(cmd, dry_run=dry_run)


def capture_service(service_name: str, destination_dir: Path, dry_run: bool = False) -> None:
    """Capture service configuration via sc.exe."""
    destination_dir.mkdir(parents=True, exist_ok=True)
    target = destination_dir / f"{sanitize_name(service_name)}.txt"
    cmd = ["sc.exe", "qc", service_name]
    result = run_command(cmd, dry_run=dry_run)
    description = None
    if not dry_run:
        description_result = subprocess.run(
            ["sc.exe", "qdescription", service_name],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
        )
        description = description_result.stdout if description_result.returncode == 0 else ""
    if dry_run:
        return
    with target.open("w", encoding="utf-8") as handle:
        handle.write(result.stdout if result else "")
        handle.write("\n")
        if description:
            handle.write(description)


def capture_scheduled_task(task_name: str, destination_dir: Path, dry_run: bool = False) -> None:
    """Export scheduled task definition."""
    destination_dir.mkdir(parents=True, exist_ok=True)
    sanitized = sanitize_name(task_name.strip("\\/"))
    target = destination_dir / f"{sanitized}.xml"
    cmd = ["schtasks", "/query", "/tn", task_name, "/xml"]
    result = run_command(cmd, dry_run=dry_run)
    if dry_run:
        return
    with target.open("w", encoding="utf-8") as handle:
        handle.write(result.stdout if result else "")


def copy_shortcut(source: Path, destination_dir: Path, dry_run: bool = False) -> None:
    """Copy shortcut or auxiliary file."""
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination = destination_dir / source.name
    copy_file(source, destination, dry_run=dry_run)


def load_config(config_path: Path) -> Dict[str, Any]:
    with config_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def validate_paths(items: Iterable[str], what: str) -> None:
    missing = []
    for path in items:
        p = expand_path(path)
        if not p.exists():
            missing.append(str(p))
    if missing:
        joined = "\n".join(missing)
        raise FileNotFoundError(f"The following {what} were not found:\n{joined}")


def create_manifest(output_dir: Path, payload: Dict[str, Any], dry_run: bool) -> None:
    manifest = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "payload": payload,
    }
    target = output_dir / "manifest.json"
    print(f"[manifest] {target}")
    if dry_run:
        return
    with target.open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2)


def determine_destination_base(entry: Dict[str, Any]) -> str:
    target = entry.get("target") or Path(entry["path"]).name
    lower_target = target.lower()
    if "localappdata" in lower_target or "\\appdata\\local" in lower_target or "appdata\\local" in lower_target:
        return "%LocalAppData%"
    if "appdata" in lower_target:
        return "%AppData%"
    if entry.get("type") == "program":
        return "%ProgramFiles%"
    return "%ProgramData%"


def restore_target_suffix(entry: Dict[str, Any]) -> str:
    target = entry.get("target") or Path(entry["path"]).name
    lower_target = target.lower()
    if "localappdata" in lower_target:
        parts = target.split("\\")
        if parts and parts[0].lower() == "localappdata":
            return "\\".join(parts[1:]) or "."
    if lower_target.startswith("appdata\\local\\"):
        parts = target.split("\\")
        # drop AppData and Local
        return "\\".join(parts[2:]) or "."
    if ("\\appdata\\" in lower_target or lower_target.startswith("appdata\\")) and target.lower().startswith("appdata\\"):
        return target.split("\\", 1)[1]
    return target


def write_restore_stub(output_dir: Path, payload: Dict[str, Any], dry_run: bool) -> None:
    restore_cmd = output_dir / "Restore_Template.cmd"
    lines: List[str] = []
    lines.append("@echo off")
    lines.append("setlocal")
    lines.append(f"echo === Restore template for {payload.get('app_name', 'PortableApp')} ===")
    lines.append("echo Customize the commands below before running on the target machine.")
    lines.append("")

    directories: List[Dict[str, Any]] = payload.get("directories", [])
    if directories:
        lines.append("REM === Copy directory trees ===")
        lines.append("REM Remove 'REM ' prefix once destinations look correct.")
        for entry in directories:
            source_root = "ProgramFiles" if entry.get("type") == "program" else "ProgramData"
            target_rel = entry.get("target") or Path(entry["path"]).name
            dest_base = determine_destination_base(entry)
            dest_suffix = restore_target_suffix(entry)
            source_desc = f"%~dp0{source_root}\\{target_rel}"
            dest_desc = f"{dest_base}\\{dest_suffix}"
            lines.append(
                f'REM robocopy "{source_desc}" "{dest_desc}" /MIR /COPYALL /R:2 /W:2 /NFL /NDL /NP'
            )
        lines.append("")

    registry_keys: List[str] = payload.get("registry_keys", [])
    if registry_keys:
        lines.append("REM === Import registry snapshots ===")
        for key in registry_keys:
            file_name = sanitize_name(key) + ".reg"
            lines.append(f'REM reg import "%~dp0Registry\\{file_name}"')
        lines.append("")

    services: List[str] = payload.get("services", [])
    if services:
        lines.append("REM === Recreate services ===")
        for service in services:
            file_name = sanitize_name(service) + ".txt"
            lines.append(f'REM type "%~dp0Services\\{file_name}"')
            lines.append("REM sc create ... (fill in based on captured configuration)")
        lines.append("")

    tasks: List[str] = payload.get("scheduled_tasks", [])
    if tasks:
        lines.append("REM === Recreate scheduled tasks ===")
        for task in tasks:
            file_name = sanitize_name(task.strip("\\/")) + ".xml"
            lines.append(f'REM schtasks /create /tn "{task}" /xml "%~dp0Tasks\\{file_name}" /f')
        lines.append("")

    lines.append("echo Template complete. Remove REM lines after customizing.")
    lines.append("pause")
    contents = "\r\n".join(lines) + "\r\n"
    print(f"[restore stub] {restore_cmd}")
    if dry_run:
        return
    restore_cmd.write_text(contents, encoding="utf-8")


def main(config_path: Path, output_dir: Path, dry_run: bool = False) -> None:
    config = load_config(config_path)
    app_name = config.get("app_name", "PortableApp")
    directories = config.get("directories", [])
    files = config.get("files", [])
    registry_keys = config.get("registry_keys", [])
    services = config.get("services", [])
    tasks = config.get("scheduled_tasks", [])
    shortcuts = config.get("shortcuts", [])

    output_dir = output_dir.resolve()
    print(f"[info] Packaging '{app_name}' into {output_dir}")
    if not dry_run and output_dir.exists() and any(output_dir.iterdir()):
        raise FileExistsError(f"Output directory '{output_dir}' is not empty. Provide an empty path or remove contents.")
    output_dir.mkdir(parents=True, exist_ok=True)

    validate_paths([item["path"] for item in directories if "path" in item], "directories")
    validate_paths(files, "files")
    validate_paths(shortcuts, "shortcuts")

    payload = {
        "app_name": app_name,
        "directories": directories,
        "files": files,
        "registry_keys": registry_keys,
        "services": services,
        "scheduled_tasks": tasks,
        "shortcuts": shortcuts,
    }

    prog_files_dir = output_dir / "ProgramFiles"
    data_dir = output_dir / "ProgramData"
    registry_dir = output_dir / "Registry"
    services_dir = output_dir / "Services"
    tasks_dir = output_dir / "Tasks"
    shortcuts_dir = output_dir / "Shortcuts"

    for entry in directories:
        source = expand_path(entry["path"])
        target_rel = Path(entry.get("target", source.name))
        target_root = data_dir if entry.get("type") == "data" else prog_files_dir
        destination = (target_root / target_rel).resolve()
        copy_directory(source, destination, dry_run=dry_run)

    for file_path in files:
        source = expand_path(file_path)
        destination = prog_files_dir / source.name
        copy_file(source, destination, dry_run=dry_run)

    for key in registry_keys:
        safe_name = sanitize_name(key)
        destination = registry_dir / f"{safe_name}.reg"
        export_registry(key, destination, dry_run=dry_run)

    for service_name in services:
        capture_service(service_name, services_dir, dry_run=dry_run)

    for task_name in tasks:
        capture_scheduled_task(task_name, tasks_dir, dry_run=dry_run)

    for shortcut_path in shortcuts:
        source = expand_path(shortcut_path)
        copy_shortcut(source, shortcuts_dir, dry_run=dry_run)

    create_manifest(output_dir, payload, dry_run=dry_run)
    write_restore_stub(output_dir, payload, dry_run=dry_run)
    print("[done] Portable package created.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Package installed program data into portable folder.")
    parser.add_argument("config", type=Path, help="Path to JSON config (see portable_config.sample.json).")
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Destination folder for the portable package (must be empty).",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print commands without copying/exporting.")
    args = parser.parse_args()
    try:
        main(args.config, args.output, dry_run=args.dry_run)
    except Exception as exc:  # pragma: no cover - utility script
        print(f"[error] {exc}", file=sys.stderr)
        sys.exit(1)
