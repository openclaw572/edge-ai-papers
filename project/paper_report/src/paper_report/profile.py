from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .models import ResearchProfile


class ProfileStore:
    """管理多個使用者偏好的研究領域設定。"""

    def __init__(self, path: str | Path):
        self.path = Path(path)

    def _read(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"profiles": {}}
        data = yaml.safe_load(self.path.read_text(encoding="utf-8")) or {}
        if "profiles" not in data or data["profiles"] is None:
            data["profiles"] = {}
        return data

    def _write(self, data: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")

    def list_profiles(self) -> list[str]:
        return sorted(self._read().get("profiles", {}).keys())

    def get_profile(self, profile_id: str) -> dict[str, Any]:
        profiles = self._read().get("profiles", {})
        if profile_id not in profiles:
            raise KeyError(f"profile not found: {profile_id}")
        return profiles[profile_id]

    def add_or_update_profile(self, profile_id: str, profile_data: dict[str, Any]) -> dict[str, Any]:
        if not profile_id:
            raise ValueError("profile_id is required")
        data = self._read()
        current = dict(data.setdefault("profiles", {}).get(profile_id, {}))
        current.update(profile_data or {})
        data["profiles"][profile_id] = current
        self._write(data)
        return current

    def delete_profile(self, profile_id: str) -> None:
        data = self._read()
        data.setdefault("profiles", {}).pop(profile_id, None)
        self._write(data)


def load_yaml(path: str | Path) -> dict[str, Any]:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}


def load_research_profile(path: str | Path, profile_id: str | None = None) -> ResearchProfile:
    data = load_yaml(path)
    if "profiles" in data:
        profiles = data.get("profiles") or {}
        if profile_id is None:
            if not profiles:
                raise ValueError("no profiles found in profile store")
            profile_id = sorted(profiles.keys())[0]
        data = profiles[profile_id]
    return ResearchProfile.from_dict(data)


def save_research_profile(path: str | Path, profile: ResearchProfile) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(profile.to_dict(), allow_unicode=True, sort_keys=False), encoding="utf-8")
