#!/usr/bin/env python3
"""
Convert an Uninstall Tool "Traced Data" XML export (or any XML listing with path attributes)
into a portable_packager configuration JSON.

Usage:
    python trace_xml_to_config.py traced.xml --output config.json

The script attempts to infer which entries should become directories vs.
single files and labels directories as "program" (under Program Files) or
 "data" (AppData/ProgramData).
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Dict, Iterable, List, Set, Tuple
import xml.etree.ElementTree as ET


PROGRAM_ROOTS = [Path(os.environ.get("ProgramFiles", "C:\\Program Files")), Path(os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)"))]
DATA_ROOTS = [
    Path(os.environ.get("ProgramData", "C:\\ProgramData")),
    Path(os.environ.get("APPDATA", "")) if os.environ.get("APPDATA") else None,
    Path(os.environ.get("LOCALAPPDATA", "")) if os.environ.get("LOCALAPPDATA") else None,
]
DATA_ROOTS = [p for p in DATA_ROOTS if p]


def normalize_path(value: str) -> str:
    value = value.strip().strip('"').replace("/", "\\")
    if value.endswith(":"):
        value += "\\"
    return value


def collect_paths(root: ET.Element) -> Tuple[Set[str], Set[str], Set[str], Set[str]]:
    file_paths: Set[str] = set()
    registry_keys: Set[str] = set()
    services: Set[str] = set()
    tasks: Set[str] = set()
    for elem in root.iter():
        for attr in ("Path", "path", "Location", "location", "Target", "target"):
            value = elem.attrib.get(attr)
            if not value:
                continue
            norm = normalize_path(value)
            if norm.upper().startswith("HK"):
                registry_keys.add(norm)
            elif norm.startswith("\\") and not norm[1:].startswith("\\"):
                tasks.add(norm)
            elif ":" in norm or norm.startswith("\\\\"):
                file_paths.add(norm)
        name_value = elem.attrib.get("Name") or elem.attrib.get("name")
        if name_value and elem.tag.lower().startswith("service"):
            services.add(name_value.strip())
        if elem.tag.lower().startswith("task") and name_value:
            tasks.add(name_value.strip())
    return file_paths, registry_keys, services, tasks


def is_subpath(child: str, parent: str) -> bool:
    child_norm = child.rstrip("\\").lower()
    parent_norm = parent.rstrip("\\").lower()
    return child_norm == parent_norm or child_norm.startswith(parent_norm + "\\")


def reduce_paths(paths: Iterable[str]) -> List[str]:
    result: List[str] = []
    for path in sorted(set(paths), key=lambda p: len(p)):
        if not any(is_subpath(path, existing) for existing in result):
            result.append(path)
    return result


def categorize_directory(path: str) -> str:
    lower = path.lower()
    for root in PROGRAM_ROOTS:
        if lower.startswith(str(root).lower()):
            return "program"
    if "\\appdata\\" in lower or "\\programdata\\" in lower:
        return "data"
    return "data"


def is_within_known_root(path: Path) -> bool:
    lower = str(path).lower()
    for root in PROGRAM_ROOTS + DATA_ROOTS:
        if lower.startswith(str(root).lower()):
            return True
    for token in ("\\appdata\\", "\\programdata\\"):
        if token in lower:
            return True
    return False


def pick_directories_and_files(paths: Iterable[str]) -> Tuple[List[Dict[str, str]], List[str]]:
    directory_map: Dict[str, Dict[str, str]] = {}
    files: List[str] = []

    for raw_path in reduce_paths(paths):
        path_obj = Path(raw_path)
        if is_within_known_root(path_obj):
            if path_obj.suffix and not raw_path.endswith("\\"):
                candidate = path_obj.parent
            else:
                candidate = path_obj
            candidate_str = str(candidate)
            if candidate_str not in directory_map:
                directory_map[candidate_str] = {
                    "path": candidate_str,
                    "target": candidate.name or candidate_str.replace(":", ""),
                    "type": categorize_directory(candidate_str),
                }
        else:
            files.append(raw_path)

    directories = [directory_map[key] for key in sorted(directory_map.keys(), key=len)]
    return directories, files


def build_config(xml_path: Path, app_name: str | None) -> Dict[str, object]:
    tree = ET.parse(xml_path)
    root = tree.getroot()
    file_paths, registry_keys, services, tasks = collect_paths(root)
    directories, files = pick_directories_and_files(file_paths)
    config = {
        "app_name": app_name or xml_path.stem,
        "directories": directories,
        "files": files,
        "registry_keys": sorted(registry_keys),
        "services": sorted(services),
        "scheduled_tasks": sorted(tasks),
        "shortcuts": [],
    }
    return config


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert traced XML to portable config.")
    parser.add_argument("xml", type=Path, help="XML exported from Uninstall Tool (Traced Data).")
    parser.add_argument("--output", "-o", type=Path, required=True, help="Output JSON config path.")
    parser.add_argument("--app-name", help="Override app name (defaults to XML filename).")
    args = parser.parse_args()
    config = build_config(args.xml, args.app_name)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as handle:
        json.dump(config, handle, indent=2)
    print(f"[done] Wrote {args.output}")


if __name__ == "__main__":
    main()
