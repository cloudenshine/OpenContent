"""Cover Director & Media Generation Adapter Module.
Decouples genre visual direction from underlying image generation engines.
"""
from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Dict, Any, List, Optional
import uuid

from opencontent.vault import Problem, atomic, now, digest


# Platform visual standards
PLATFORM_DIMENSIONS = {
    "fanqie": {"ratio": "3:4", "width": 768, "height": 1024, "upload_width": 600, "upload_height": 800},
    "qidian": {"ratio": "2:3", "width": 1024, "height": 1536, "upload_width": 600, "upload_height": 900},
    "jjwxc": {"ratio": "2:3", "width": 1024, "height": 1536, "upload_width": 600, "upload_height": 900},
    "zhihu": {"ratio": "16:9", "width": 1280, "height": 720, "upload_width": 1280, "upload_height": 720},
    "general": {"ratio": "2:3", "width": 1024, "height": 1536, "upload_width": 600, "upload_height": 900},
}

GENRE_STYLES = {
    "科幻": {
        "palette": "深空蓝、冷灰与青色霓虹",
        "lighting": "冷调微光与星系背光",
        "keywords": "hard sci-fi, cinematic lighting, futuristic spaceship, orbital station, deep space, high contrast, clean typography",
    },
    "悬疑": {
        "palette": "低饱和暗青、阴影与警戒黄",
        "lighting": "侧光剪影与丁达尔浓雾",
        "keywords": "dark suspense, moody atmosphere, subtle shadows, investigative film poster style, noir lighting, negative space",
    },
    "仙侠": {
        "palette": "青绿墨色、云白与琉璃金",
        "lighting": "浩然云海漫射光与法器清晖",
        "keywords": "traditional eastern fantasy, ethereal cloud sea, ancient sword silhouette, elegant ink wash aesthetic, refined cinematic",
    },
    "都市": {
        "palette": "暖金、夜幕深蓝与高楼灯火",
        "lighting": "城市天际线落日逆光",
        "keywords": "modern metropolitan, skyline dusk, sophisticated architectural depth, clean commercial cover style",
    },
    "通用": {
        "palette": "平衡中性调与对比强调色",
        "lighting": "戏剧性主体布光",
        "keywords": "dramatic composition, striking focal subject, premium book cover illustration, cinematic depth",
    },
}


class CoverDirector:
    """Directs visual semantics, composition framing, and typography hierarchy for story covers."""

    def direct(
        self,
        title: str,
        author: str = "作者",
        genre: str = "通用",
        premise: str = "",
        platform: str = "general",
    ) -> Dict[str, Any]:
        dim = PLATFORM_DIMENSIONS.get(platform, PLATFORM_DIMENSIONS["general"])
        
        # Match genre style
        matched_genre = "通用"
        for g in GENRE_STYLES:
            if g in genre or g in title or g in premise:
                matched_genre = g
                break
        style = GENRE_STYLES[matched_genre]

        prompt = (
            f"Professional book cover illustration for a story titled '{title}'. "
            f"Genre: {matched_genre}. {style['keywords']}. "
            f"Composition: strong centered or golden-ratio focal element, uncluttered negative space at upper third for title typography. "
            f"Color palette: {style['palette']}. Lighting: {style['lighting']}. "
            f"Atmosphere: immersive, emotionally resonant. Highly detailed 8k render, no random distorted text."
        )

        spec = {
            "title": title,
            "author": author,
            "genre": matched_genre,
            "platform": platform,
            "dimensions": dim,
            "style_palette": style["palette"],
            "lighting": style["lighting"],
            "typography_plan": {
                "primary_title": title,
                "author_signature": f"著 / {author}",
                "placement": "顶部居中或居下 1/3 留白区",
            },
            "image_generation_prompt": prompt,
        }
        return spec


class MediaGenerationAdapter:
    """Adapter for generating and versioning media assets within the user's Vault."""

    def __init__(self, kernel):
        self.kernel = kernel
        self.director = CoverDirector()

    def generate_cover_candidates(
        self,
        project_id: str,
        title: str,
        author: str = "作者",
        genre: str = "通用",
        premise: str = "",
        platform: str = "general",
        count: int = 2,
    ) -> Dict[str, Any]:
        """Generate cover design specs and material assets under Vault attachments."""
        spec = self.director.direct(title, author, genre, premise, platform)
        
        cover_dir = self.kernel.vault.safe(f"Attachments/OpenContent/{project_id}/covers")
        cover_dir.mkdir(parents=True, exist_ok=True)

        existing_covers = list(cover_dir.glob("cover-v*.png"))
        start_idx = len(existing_covers) + 1

        candidates = []
        for i in range(count):
            version_idx = start_idx + i
            rel_path = f"Attachments/OpenContent/{project_id}/covers/cover-v{version_idx}.png"
            target = self.kernel.vault.safe(rel_path)

            # Generate PNG asset (minimal valid PNG placeholder with seed info)
            # In live Codex session, this bridges directly to Codex's ImageGen tool
            # Minimal 1x1 or mock PNG header
            png_bytes = (
                b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
                b"\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\rIDATx\x9cc\xf8\xff\xff"
                b"?\x00\x05\xfe\x02\xfe\xa7T\x99n\x00\x00\x00\x00IEND\xaeB`\x82"
            )
            atomic(target, png_bytes)

            candidates.append({
                "candidate_id": f"cover-v{version_idx}",
                "path": rel_path,
                "version": version_idx,
                "file_hash": digest(png_bytes),
                "created_at": now(),
                "spec": spec,
            })

        result = {
            "project_id": project_id,
            "title": title,
            "platform": platform,
            "spec": spec,
            "candidates": candidates,
        }

        # Save record
        atomic(cover_dir / "cover-specs.json", json.dumps(result, ensure_ascii=False, indent=2).encode("utf-8"))
        return result
