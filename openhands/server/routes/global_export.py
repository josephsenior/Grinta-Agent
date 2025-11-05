"""Global export/import for all user data."""

import json
import logging
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from openhands.server.shared import config

app = APIRouter(prefix="/api/global-export")
logger = logging.getLogger(__name__)


class GlobalExportData(BaseModel):
    """Container for all exportable data."""

    version: str = Field("1.0.0", description="Export format version")
    exported_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    memories: list[dict] = Field(default_factory=list)
    prompts: list[dict] = Field(default_factory=list)
    snippets: list[dict] = Field(default_factory=list)
    templates: list[dict] = Field(default_factory=list)
    settings: dict = Field(default_factory=dict)
    metadata: dict = Field(default_factory=dict)


def _load_json_files(directory: str) -> list[dict]:
    """Load all JSON files from a directory."""
    workspace_base = Path(config.workspace_base or ".")
    dir_path = workspace_base / directory

    if not dir_path.exists():
        return []

    data = []
    for file_path in dir_path.glob("*.json"):
        try:
            with open(file_path, encoding="utf-8") as f:
                data.append(json.load(f))
        except Exception as e:
            logger.exception(f"Error loading {file_path}: {e}")

    return data


def _save_json_files(directory: str, data: list[dict]) -> tuple[int, int]:
    """Save JSON files to a directory."""
    workspace_base = Path(config.workspace_base or ".")
    dir_path = workspace_base / directory
    dir_path.mkdir(parents=True, exist_ok=True)

    imported = 0
    updated = 0

    for item in data:
        try:
            item_id = item.get("id")
            if not item_id:
                continue

            file_path = dir_path / f"{item_id}.json"
            exists = file_path.exists()

            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(item, f, indent=2)

            if exists:
                updated += 1
            else:
                imported += 1
        except Exception as e:
            logger.exception(f"Error saving item: {e}")

    return imported, updated


@app.get("/")
async def export_all_data() -> JSONResponse:
    """Export all user data."""
    try:
        export_data = GlobalExportData(
            version="1.0.0",
            memories=_load_json_files("memories"),
            prompts=_load_json_files("prompts"),
            snippets=_load_json_files("snippets"),
            templates=_load_json_files("templates"),
            metadata={
                "total_memories": len(_load_json_files("memories")),
                "total_prompts": len(_load_json_files("prompts")),
                "total_snippets": len(_load_json_files("snippets")),
                "total_templates": len(_load_json_files("templates")),
            },
        )

        return JSONResponse(
            content=json.loads(export_data.model_dump_json(indent=2)),
            headers={
                "Content-Disposition": f'attachment; filename="openhands_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json"',
            },
        )
    except Exception as e:
        logger.exception(f"Error exporting data: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/")
async def import_all_data(data: GlobalExportData) -> dict[str, dict[str, int]]:
    """Import all user data."""
    try:
        # Import memories
        mem_imported, mem_updated = _save_json_files("memories", data.memories)
        results = {"memories": {"imported": mem_imported, "updated": mem_updated}}
        # Import prompts
        prompt_imported, prompt_updated = _save_json_files("prompts", data.prompts)
        results["prompts"] = {"imported": prompt_imported, "updated": prompt_updated}

        # Import snippets
        snip_imported, snip_updated = _save_json_files("snippets", data.snippets)
        results["snippets"] = {"imported": snip_imported, "updated": snip_updated}

        # Import templates
        temp_imported, temp_updated = _save_json_files("templates", data.templates)
        results["templates"] = {"imported": temp_imported, "updated": temp_updated}

        logger.info(f"Import complete: {results}")
        return results
    except Exception as e:
        logger.exception(f"Error importing data: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e
