import json
import requests
import time
import base64
import urllib3
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.theme import Theme
from rich import box
from rich.align import Align
from rich.table import Table

console = Console()
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- CONFIGURATIONS ---
CALDERA_URL = "http://127.0.0.1:8888/api/v2"
API_KEY = "ADMIN123"
HEADERS = {'KEY': API_KEY, 'Content-Type': 'application/json'}

# YOUR FLASK SERVER URL (GEMINI)
LLM_SERVER_URL = "http://127.0.0.1:8001/analyze_result"

def get_real_output_via_report(op_id):
    """
    Fetches the real output through the operation's /report endpoint.
    This approach is more robust than fetching the individual link.
    """
    try:
        res = requests.post(f"{CALDERA_URL}/operations/{op_id}/report", headers=HEADERS, json={"enable_agent_output": True}, timeout=10)

        if res.status_code == 200:
            report = res.json()
            steps = []

            # Logic to extract steps from new or old Caldera format
            if 'steps' in report:
                if isinstance(report['steps'], dict):
                    for paw in report['steps']:
                        steps.extend(report['steps'][paw].get('steps', []))
                else:
                    steps = report['steps']
            elif 'chain' in report:
                 steps = report['chain']

            # Returns the output of the last executed step
            if steps:
                last_step = steps[-1]
                # Prioritizes decoded output if it exists, otherwise raw
                return last_step.get('output', '')

    except:
        pass
    return None

def clean_text_forensic(data):
    """Cleans the output for visual presentation."""
    if not data: return "No return."
    if isinstance(data, dict): return str(data)
    if isinstance(data, list): return str(data)
    
    if isinstance(data, str) and " " not in data and len(data) > 20:
        try:
            decoded = base64.b64decode(data).decode('utf-8', errors='ignore')
            if decoded.strip().startswith('{'): return decoded
            # If decoded and looks like readable text, return
            return decoded
        except: pass

    return str(data).strip()

def gerar_analise_forense_remota(comando, output, wazuh_logs_str):
    """Sends data to server_llm.py."""
    payload = {
        "command": comando,
        "output": output,
        "wazuh_logs": wazuh_logs_str if wazuh_logs_str else "[]"
    }

    try:
        # Calls your server on port 8001
        response = requests.post(LLM_SERVER_URL, json=payload, timeout=120)

        if response.status_code == 200:
            # Your server returns {"analysis": "text..."}
            return response.json().get("analysis", "Error: Empty analysis from server.")
        else:
            return f"Server Error ({response.status_code}): Check server_llm.py."

    except requests.exceptions.ConnectionError:
        return "CRITICAL ERROR: Could not connect to http://127.0.0.1:8001. Check if server_llm.py is running."
    except Exception as e:
        return f"Unexpected AI Error: {str(e)}"


def print_detailed_report(op_id, mission_data, targets, wazuh_alerts_str):
     """Generates the visual report."""

     target_agent = targets[0] if targets else {'paw': 'Unknown', 'platform': 'N/A'}
     target_paw = target_agent.get('paw')
     target_platform = target_agent.get('platform')
    
     comando = mission_data.get('command', 'N/A')
    
    # --- NEW OUTPUT RECOVERY LOGIC (Via Report) ---
     output_raw = mission_data.get('output', '')
    
    # If the output is "True" or empty, fetch via full report
     if str(output_raw).strip() == "True" or not output_raw:
        real_output = get_real_output_via_report(op_id)
        if real_output:
            output_raw = real_output

     output_clean = clean_text_forensic(output_raw)
    
     console.print("\n")
    
    # Header
     header = f"[bold black on yellow] INTEGRATED OPERATION REPORT [/]\n[dim]ID: {op_id} | TARGET: {target_paw} ({target_platform})[/dim]"
     console.print(Panel(Align.center(header), box=box.DOUBLE, border_style="yellow"))
 
    # Objective
     console.print(Panel(f"[bold white]{mission_data.get('objective')}[/bold white]", title="TACTICAL OBJECTIVE", box=box.ROUNDED, border_style="cyan"))

    # Execution Action
     action_grid = Table.grid(expand=True)
     action_grid.add_row(f"[bold red]> COMMAND[/bold red]")
     action_grid.add_row(Panel(f"{comando}", border_style="red", box=box.SIMPLE))
     action_grid.add_row(f"[bold white]> RETURN (CAPTURED)[/bold white]")
    
    # Visualization treatment
     display_output = output_clean[:3000] + "..." if len(output_clean) > 3000 else output_clean
     if display_output.strip() == "True":
         display_output = "[WARNING: The agent returned success (exit code 0), but no output text was captured.]"

     action_grid.add_row(Panel(f"[dim]{display_output}[/dim]", border_style="white", box=box.SIMPLE))
     console.print(Panel(action_grid, title=f"EXECUTION ACTION", border_style="yellow", box=box.ROUNDED))

    # Wazuh Detections (MITRE Format)
     if wazuh_alerts_str and "Error" not in wazuh_alerts_str and "Erro" not in wazuh_alerts_str and wazuh_alerts_str.strip():
        # Displays raw logs formatted as CSV/MITRE
        console.print(Panel(wazuh_alerts_str, title="[bold green]BLUE TEAM DETECTIONS (WAZUH - MITRE)[/bold green]", border_style="green", box=box.HEAVY_EDGE))
     else:
        msg = wazuh_alerts_str if wazuh_alerts_str else "No alerts registered."
        console.print(Panel(f"[dim]{msg}[/dim]", title="[bold dim]BLUE TEAM DETECTIONS[/bold dim]", border_style="dim white", box=box.HEAVY_EDGE))

    # AI Analysis
     with console.status("[bold magenta]Consulting Gemini Brain (Port 8001)...[/bold magenta]"):
        analise_texto = gerar_analise_forense_remota(comando, output_clean, wazuh_alerts_str)

     console.print(Panel(Markdown(analise_texto), title="COGNITIVE ANALYSIS (FORENSIC AI)", border_style="magenta", padding=(1, 2), box=box.ROUNDED))
     console.print(Panel(Align.center("[bold green]REPORT FINISHED[/bold green]"), box=box.DOUBLE_EDGE, border_style="green"))