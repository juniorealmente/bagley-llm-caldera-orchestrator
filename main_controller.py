import requests
import time
import json
import uuid
import os
import base64
from report_generator import print_detailed_report
from wazuh_client import get_wazuh_alerts
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt
from rich.theme import Theme
from rich import box
from rich.align import Align

# ================= DESIGN SYSTEM (BAGLEY) =================
custom_theme = Theme({
    "info": "dim white", 
    "warning": "bold yellow", 
    "danger": "bold red", 
    "success": "bold green",
    "ba": "bold yellow", 
    "logo": "bold yellow"
})
console = Console(theme=custom_theme)

# ================= CONFIGURATIONS =================
CALDERA_URL = "http://127.0.0.1:8888/api/v2"
API_KEY = "ADMIN123"
HEADERS = {'KEY': API_KEY, 'Content-Type': 'application/json'}
LLM_SERVER = "http://127.0.0.1:8001"
HISTORY_FILE = "mission_memory.json"

# ================= MEMORY SYSTEM (LEVEL 2) =================
def load_global_history():
    """Loads the persistent history."""
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r") as f:
                return json.load(f)
        except:
            return []
    return []

def save_global_history(platform, command, output, objective):
    """Saves the success to disk."""
    history = load_global_history()
    entry = {
        "timestamp": time.ctime(),
        "platform": platform,
        "objective": objective,
        "command": command,
        "output": output
    }
    history.append(entry)
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=4)

# ================= INTERFACE FUNCTIONS =================
def print_bagley_logo():
    logo = """
  ██████╗  █████╗  ██████╗ ██╗      ███████╗██╗   ██╗
  ██╔══██╗██╔══██╗██╔════╝ ██║      ██╔════╝╚██╗ ██╔╝
  ██████╔╝███████║██║  ███╗██║      █████╗   ╚████╔╝ 
  ██╔══██╗██╔══██║██║   ██║██║      ██╔══╝    ╚██╔╝  
  ██████╔╝██║  ██║╚██████╔╝███████╗ ███████╗   ██║      
  ╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚══════╝ ╚══════╝   ╚═╝      
    """
    console.print(Align.center(f"[logo]{logo}[/logo]"))
    console.print(Align.center("[italic grey70]Hi. I am Bagley. I am your analytical and operational thought.[/italic grey70]"))
    console.print(Align.center("[italic grey70]I am ready to simulate adversaries and diagnose defenses.[/italic grey70]"))

def select_targets():
    console.print("\n[bold yellow]>> SCANNING NETWORK...[/bold yellow]")
    try:
        res = requests.get(f"{CALDERA_URL}/agents", headers=HEADERS, timeout=5)
        agents = res.json()
        if not agents:
            console.print("[danger]No online agents found.[/danger]")
            return []

        # Table with GROUP and PRIVILEGE Columns
        table = Table(box=box.SIMPLE_HEAD, header_style="bold black on yellow", expand=True)
        table.add_column("NUM", justify="center", width=6)
        table.add_column("PAW", style="cyan")
        table.add_column("GROUP", style="magenta") 
        table.add_column("PLATFORM")
        table.add_column("PRIVILEGE", style="bold red")
        table.add_column("IP", style="green")
        table.add_column("STATUS", justify="center")

        for idx, agent in enumerate(agents):
            status = "[green]ONLINE[/green]" if agent.get('trusted') else "[red]OFFLINE[/red]"
            execs = ",".join(agent.get('executors', []))
            group = agent.get('group', 'red') 
            priv = agent.get('privilege', 'User')
            table.add_row(
                str(idx + 1), 
                agent['paw'], 
                group,
                agent['platform'],
                priv,
                agent.get('host_ip_addrs',['N/A'])[0], 
                status
            )
        console.print(table)

        selection = Prompt.ask("\n[bold yellow]>> Select IDs (e.g., 1,2), Group (e.g., red) or 'all'[/bold yellow]")

        if selection.lower() == 'all': return agents

        if any(a.get('group') == selection for a in agents):
            return [a for a in agents if a.get('group') == selection]

        try:
            indices = [int(i.strip()) - 1 for i in selection.split(',')]
            return [agents[i] for i in indices if 0 <= i < len(agents)]
        except:
            console.print("[danger]Invalid selection.[/danger]")
            return []
    except Exception as e:
        console.print(f"[danger]Selection error: {e}[/danger]")
        return []

# ================= CALDERA CORE =================
def register_and_run(agent, objective, command_str):
    unique_id = str(uuid.uuid4())[:8] 
    abi_id = f"abi-{unique_id}"
    adv_id = f"adv-{unique_id}"
    op_name = f"Op_{unique_id}"
    
    supported_execs = agent.get('executors', [])
    
    if agent['platform'] == 'windows':
        executor = 'psh' if 'psh' in supported_execs else 'cmd'
    else:
        if 'sh' in supported_execs: executor = 'sh'
        elif 'bash' in supported_execs: executor = 'bash'
        else: executor = supported_execs[0] if supported_execs else 'sh'

    console.print(f"[dim info]DEBUG: Executor '{executor}' | Unique ID: {unique_id}[/dim info]")

    try:
        # 1. Ability
        ability_payload = {
            "ability_id": abi_id,
            "tactic": "execution",
            "technique_id": "T1059",
            "technique_name": "Command Execution", 
            "name": f"Task_{unique_id}",
            "description": f"Atomic task generated by Bagley for {objective}", 
            "executors": [{
                "name": executor,
                "platform": agent['platform'],
                "command": command_str,
                "timeout": 60, 
                "cleanup": [],
                "parsers": []
            }]
        }

        res1 = requests.post(f"{CALDERA_URL}/abilities", headers=HEADERS, json=ability_payload)
        if res1.status_code >= 400:
            console.print(f"[red]API Error (Ability): {res1.status_code} - {res1.text}[/red]")
            return None

        # 2. Adversary
        res2 = requests.post(f"{CALDERA_URL}/adversaries", headers=HEADERS, json={
            "adversary_id": adv_id, 
            "name": f"Adv_{unique_id}",
            "description": "Generated by Bagley",
            "atomic_ordering": [abi_id]
        })
        if res2.status_code >= 400:
            console.print(f"[red]API Error (Adversary): {res2.text}[/red]")
            return None

        # 3. Operation
        res3 = requests.post(f"{CALDERA_URL}/operations", headers=HEADERS, json={
            "name": op_name, 
            "group": agent['group'], 
            "adversary": {"adversary_id": adv_id}, 
            "planner": {"id": "atomic"},
            "state": "running", 
            "autonomous": 1,
            "jitter": "0/0"
        })
        if res3.status_code >= 400:
            console.print(f"[red]API Error (Operation): {res3.text}[/red]")
            return None
        return res3.json().get('id')
    except Exception as e: 
        console.print(f"[red]Critical Python Error: {e}[/red]")
        return None

def wait_for_finish_xray(op_id):
    console.print("[bold yellow]>> Monitoring Caldera API (X-RAY Mode)...[/bold yellow]")
    
    start_time = time.time()
    for i in range(30): 
        try:
            res_links = requests.get(f"{CALDERA_URL}/operations/{op_id}/links", headers=HEADERS)
            links = res_links.json()
            elapsed = time.time() - start_time

            if not links:
                console.print(f"   [dim]T+{elapsed:.0f}s: Operation created ({op_id}), waiting for Planner...[/dim]")
                if elapsed > 15:
                     console.print("   [bold red]WARNING: Planner delay. Check if the agent is active.[/bold red]")
            else:
                last_link = links[-1]
                status = last_link.get('status') 
                status_map = {-5: "CANDIDATE", -4: "UNTRUSTED", -3: "DISCARD/WAIT", -2: "DISCARD", -1: "PAUSED", 0: "SUCCESS", 1: "ERROR", 124: "TIMEOUT"}
                status_text = status_map.get(status, f"CODE {status}")

                color = "green" if status == 0 else "yellow"
                if status > 0 or status == -4: color = "red"

                console.print(f"   [dim]T+{elapsed:.0f}s:[/dim] Link ID {last_link['id'][:8]}... | Status: [{color}]{status_text}[/{color}]")
                if status == 0: return True # SUCCESS
                if status > 0: 
                    console.print(f"[red]   The command failed on the agent with code {status}.[/red]")
                    return True # Ends with error (try next command)

            time.sleep(2)
        except Exception as e: 
            break
    return False

# ================= LLM COMMUNICATION =================
def get_ai_command(objective, history, memory, agent):
    """
    Centralized function to request a command from the AI.
    Now sends the agent's PRIVILEGE for context.
    """
    payload = {
        "objective": objective, 
        "history": history, 
        "global_memory": memory, 
        "agent": agent,
        "platform": agent['platform'],
        "privilege": agent.get('privilege', 'User') # SENDS PRIVILEGE TO THE SERVER
    }
    try:
        res_ai = requests.post(f"{LLM_SERVER}/analyze_objective", json=payload)
        return res_ai.json().get('generated_command')
    except:
        return "id"

# ================= MAIN LOOP =================
def main():
    print_bagley_logo()
    targets = select_targets()
    if not targets: return

    global_memory = load_global_history()

    objective = Prompt.ask(f"\n[bold white]>> Tactical Objective[/bold white]")
    
    for agent in targets:
        attempts_history = [] 
        agent_success = False
        console.rule(f"TARGET: {agent['paw']} ({agent['platform'].upper()})", style="bold blue")

        for attempt in range(1, 6): 
            # Calls the AI with the complete context (including privilege)
            command = get_ai_command(objective, attempts_history, global_memory, agent)

            console.print(f"[dim]Attempt {attempt}/5:[/dim] [bold cyan]{command}[/bold cyan]")

            op_id = register_and_run(agent, objective, command)

            if op_id:
                finished = wait_for_finish_xray(op_id)
                if finished:
                    # --- NEW: FETCH OUTPUT VIA FULL REPORT ---
                    final_output = ""
                    try:
                        report_res = requests.post(f"{CALDERA_URL}/operations/{op_id}/report", headers=HEADERS, json={"enable_agent_output": True})
                        report = report_res.json()

                        # Extracts output from the complex report structure
                        steps = []
                        if 'steps' in report:
                            if isinstance(report['steps'], dict): # New format
                                 for paw in report['steps']:
                                     steps.extend(report['steps'][paw].get('steps', []))
                            else: steps = report['steps'] # Old format

                        if steps:
                            # Gets the output of the last executed step
                            last_step = steps[-1]
                            final_output = last_step.get('output', '')

                    except Exception as e:
                        console.print(f"[dim red]Error fetching detailed report: {e}[/dim red]")

                    # Verifies success (Text OR code 0 if supported)
                    # Note: Caldera status 0 already validated the exit_code, so if it reached here with finished=True
                    if finished: 
                        console.print(f"[success]>> Technical Success![/success]")
                        console.print(Panel(str(final_output).strip()[:3000], title="REAL OUTPUT (REPORT)", border_style="green"))
                        save_global_history(agent['platform'], command, final_output, objective)

                        # --- WAZUH INTEGRATION ---
                        wazuh_alerts_str = ""
                        wazuh_list = []
                        with console.status("[bold green]Checking Wazuh (5s Delay)...[/]"):
                            time.sleep(5) # Delay for Wazuh indexing
                            target_ip = agent.get('host_ip_addrs', ['0.0.0.0'])[0]

                            # Fetches alerts already formatted as a list of strings
                            wazuh_list = get_wazuh_alerts(target_ip)

                        if wazuh_list:
                            wazuh_alerts_str = "\n".join(wazuh_list)
                            console.print(f"[bold red]>> {len(wazuh_list)} Alerts detected by the Blue Team![/bold red]")
                        else:
                            console.print("[dim]>> No alerts detected by Wazuh (Shadow Technique?)[/dim]")

                        # Passes the unified string and the REAL OUTPUT to the report
                        print_detailed_report(
                            op_id, 
                            {
                                "objective": objective, 
                                "command": command, 
                                "output": final_output # Here goes the real decoded output!
                            }, 
                            [agent], 
                            wazuh_alerts_str
                        )

                        agent_success = True
                        break 
                else:
                    console.print(f"[danger]>> Real Timeout (Agent did not respond).[/danger]")
                    attempts_history.append(f"Command '{command}' timed out.")
            else:
                attempts_history.append(f"Failed to register operation in Caldera.")

        if not agent_success:
            console.print(f"[danger]XXXX Total Failure on agent {agent['paw']}. XXXX[/danger]")

if __name__ == "__main__":
    main()