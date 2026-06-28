from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from . import __version__
from .http import fetch_json
from .io import ensure_dir, load_config, sha256_json, utc_now, write_json
from .models import RawRecord


SOURCE = "dimbreath_textmap"


def _make_record(*, source_url: str, language: str, filename: str, payload: Any) -> RawRecord:
    return RawRecord(
        raw_id=f"{SOURCE}:{language}:{filename}",
        source=SOURCE,
        source_url=source_url,
        fetched_at=utc_now(),
        language=language,
        raw_format="json",
        content_hash=sha256_json(payload),
        crawler_version=__version__,
        payload=payload,
        metadata={"filename": filename, "kind": "textmap"},
    )


def crawl_dimbreath_textmaps(
    root: Path,
    *,
    languages: list[str] | None = None,
    force: bool = False,
    sleep_seconds: float = 0.5,
) -> dict[str, Any]:
    config = load_config(root)
    lang_config = config["languages"]
    source_config = config["sources"][SOURCE]
    if languages is None:
        languages = list(lang_config.keys())

    base_url = source_config["base_url"].rstrip("/")
    report: dict[str, Any] = {"source": SOURCE, "files": [], "errors": []}

    for language in languages:
        if language not in lang_config:
            raise ValueError(f"Unknown language: {language}")
        filename = lang_config[language]["dimbreath_textmap"]
        url = f"{base_url}/{filename}"
        path = root / "data" / "raw" / SOURCE / language / f"{filename}.raw.json"
        if path.exists() and not force:
            report["files"].append({"language": language, "filename": filename, "status": "cached", "path": str(path)})
            continue
        try:
            payload = fetch_json(url, timeout=180, retries=3, sleep_seconds=sleep_seconds)
            record = _make_record(source_url=url, language=language, filename=filename, payload=payload)
            write_json(path, record.to_dict())
            report["files"].append(
                {
                    "language": language,
                    "filename": filename,
                    "status": "fetched",
                    "entries": len(payload) if isinstance(payload, dict) else None,
                    "path": str(path),
                }
            )
        except Exception as error:
            report["errors"].append({"url": url, "error": str(error)})
        time.sleep(sleep_seconds)

    ensure_dir(root / "data" / "logs")
    write_json(root / "data" / "logs" / "dimbreath_textmap_last_run.json", report)
    return report

