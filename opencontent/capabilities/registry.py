"""Pack Registry for discovering and accessing Creative Capability Packs."""
from pathlib import Path
from typing import Dict, List, Optional, Any
import yaml

from opencontent.vault import Problem
from .manifest import PackManifest, load_manifest


class PackRegistry:
    def __init__(self):
        self._packs: Dict[str, PackManifest] = {}
        self._profiles: Dict[str, Dict[str, Any]] = {}

    def register(self, manifest: PackManifest):
        if manifest.id in self._packs:
            raise Problem(f"Duplicate capability pack id: '{manifest.id}'")
        self._packs[manifest.id] = manifest
        # Pre-load profile definitions
        self._profiles[manifest.id] = {}
        for p_id in manifest.profiles:
            p_path = manifest.root_dir / "profiles" / f"{p_id}.yaml"
            if not p_path.is_file():
                p_path = manifest.root_dir / "profiles" / f"{p_id}.yml"
            if p_path.is_file():
                try:
                    self._profiles[manifest.id][p_id] = yaml.safe_load(p_path.read_text(encoding="utf-8")) or {}
                except Exception as e:
                    raise Problem(f"Failed to load profile '{p_id}' in pack '{manifest.id}': {e}") from e

    def get_pack(self, pack_id: str) -> PackManifest:
        pack = self._packs.get(pack_id)
        if not pack:
            raise Problem(f"Capability pack '{pack_id}' not found. Available: {list(self._packs.keys())}")
        return pack

    def get_profile(self, pack_id: str, profile_id: str) -> Dict[str, Any]:
        self.get_pack(pack_id)
        profs = self._profiles.get(pack_id, {})
        if profile_id not in profs:
            raise Problem(f"Profile '{profile_id}' not found in pack '{pack_id}'. Available: {list(profs.keys())}")
        return profs[profile_id]

    def list_capabilities(self) -> List[Dict[str, Any]]:
        result = []
        for p in self._packs.values():
            result.append({
                "id": p.id,
                "name": p.name,
                "version": p.version,
                "description": p.description,
                "profiles": p.profiles,
                "tasks": p.tasks,
                "runtime": p.runtime,
                "outputs": p.outputs,
            })
        return result

    def discover(self, roots: Optional[List[Path]] = None):
        """Discover packs from trusted root directories."""
        if not roots:
            return
        for root in roots:
            r = Path(root).resolve()
            if not r.is_dir():
                continue
            # Scan child directories containing pack.yaml/yml
            for child in sorted(r.iterdir()):
                if child.is_dir() and (child / "pack.yaml").is_file() or (child / "pack.yml").is_file():
                    try:
                        manifest = load_manifest(child)
                        self.register(manifest)
                    except Exception as e:
                        raise Problem(f"Failed to register pack in '{child}': {e}") from e
