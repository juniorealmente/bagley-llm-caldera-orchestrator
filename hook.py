# hook.py
# Plugin CALDERA – Registration of the LLM Planner (CDB_LLM)

import logging
from pathlib import Path
import os

log = logging.getLogger("cdb_llm")

description = "CDB LLM Integration Plugin for CALDERA"
address = "cdb_llm"


def initialize(app, services):
    """
    Executed during CALDERA startup.
    Responsible for registering the LLM planner.
    """
    log.info("[CDB-LLM] Initializing plugin")

    # Ensures plugin data directory.
    try:
        cfg = services.get("config")
        plugins_path = getattr(cfg, "plugins_path", None)
        base = Path(plugins_path or Path(app.config_dir) / "plugins")
        data_dir = base / "cdb_llm" / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        log.warning(f"[CDB-LLM] Failed to prepare directory: {e}")

    # Planner registration
    try:
        from .app import CDBLLMPlanner

        planning_svc = services.get("planning_svc")
        if not planning_svc:
            log.error("[CDB-LLM] planning_svc unavailable")
            return

        # URL of services LLM (Gemini proxy or local API)
        llm_url = os.environ.get("CDB_LLM_URL", "http://127.0.0.1:8001")

        planner = CDBLLMPlanner(llm_url=llm_url)
        planning_svc.register_planner(planner)

        log.info("[CDB-LLM] Planner 'cdb_llm' registered successfully")

    except Exception as e:
        log.exception(f"[CDB-LLM] Error registering planner: {e}")


def operation_complete(app, operation, services):
    """
    Callback called when a CALDERA operation completes.
    Useful for post-processing or report generation.
    """
    try:
        name = operation.get("name")
        oid = operation.get("id")
        log.info(f"[CDB-LLM] Operation completed: {name} ({oid})")
    except Exception:
        pass

