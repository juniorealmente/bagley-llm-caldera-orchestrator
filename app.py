                                                      
# app.py - planner implementation that calls an external LLM endpoint
import os
import asyncio
import logging
from aiohttp import web

try:
    import aiohttp
except Exception:
    aiohttp = None

log = logging.getLogger("cdb_llm")

DEFAULT_LLM_URL = os.environ.get("CDB_LLM_URL", "http://127.0.0.1:8001")

class CDBLLMPlanner:
    """A simple planner that can be registered with Caldera's planning service."""

    name = "cdb_llm"
    description = "CDB LLM planner — delegates plan generation to external LLM"

    def __init__(self, llm_url: str = None, timeout: int = 10):
        self.llm_url = llm_url or DEFAULT_LLM_URL
        self.timeout = timeout

    async def plan(self, objective: str, target: dict = None, context: dict = None, max_steps: int = 6):
        """Return a plan as a Python dict."""
        target = target or {}
        context = context or {}

        payload = {
            "objective": objective,
            "target": target,
            "max_steps": max_steps,
        }

        # try to call external LLM service
        if aiohttp is None:
            log.warning("aiohttp not installed — returning fallback plan")
            return self._fallback_plan(objective, max_steps)

        try:
            url = self.llm_url.rstrip("/") + "/plan_attack"
            log.info(f"CDB-LLM: calling LLM at {url} with payload={payload}")

            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, timeout=self.timeout) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        log.info("CDB-LLM: received plan from LLM")
                        return self._normalize_response(data, max_steps)
                    else:
                        log.warning(f"CDB-LLM: LLM returned status {resp.status}")
                        return self._fallback_plan(objective, max_steps)
        except asyncio.TimeoutError:
            log.warning("CDB-LLM: request to LLM timed out")
            return self._fallback_plan(objective, max_steps)
        except Exception as e:
            log.exception("CDB-LLM: error calling LLM")
            return self._fallback_plan(objective, max_steps)

    def _normalize_response(self, data: dict, max_steps: int):
        if isinstance(data, dict) and data.get("steps"):
            steps = data.get("steps")[:max_steps]
            return {"objective": data.get("objective"), "steps": steps}

        if isinstance(data, dict) and data.get("tactics") and data.get("techniques"):
            tactics = data.get("tactics")
            techniques = data.get("techniques")
            procedures = data.get("procedures", [])
            steps = []
            for i in range(min(max_steps, len(techniques))):
                steps.append({
                    "step": i+1,
                    "tactic": tactics[i] if i < len(tactics) else tactics[0],
                    "technique": techniques[i],
                    "action": procedures[i] if i < len(procedures) else "Automated action from LLM"
                })
            return {"objective": data.get("objective", ""), "steps": steps}

        return self._fallback_plan(data.get("objective") if isinstance(data, dict) else None, max_steps)

    def _fallback_plan(self, objective: str, max_steps: int):
        steps = []
        for i in range(1, max_steps+1):
            steps.append({
                "step": i,
                "tactic": "Initial Access" if i == 1 else "Lateral Movement",
                "technique": "T1566" if i == 1 else "T1021",
                "action": f"Fallback action {i} for objective: {objective or 'unknown'}"
            })
        return {"objective": objective, "steps": steps}
