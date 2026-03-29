import requests
import urllib3
import json
from requests.auth import HTTPBasicAuth

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- CONFIGURATIONS ---
WAZUH_API_URL = "https://192.168.56.105:55000"
WAZUH_USER = "wazuh-wui"
WAZUH_PASS = "MyS3cr37P450r.*-"

# --- IP TRANSLATION MAP (Caldera -> Wazuh) ---
# If Caldera attacks an IP, but Wazuh knows it by another, map it here.
# Format: "CALDERA_IP": "WAZUH_IP"
IP_MAP = {
    "192.168.1.65": "192.168.56.104"  # Fixes the Linux IP
}

def get_token():
    try:
        response = requests.get(
            f"{WAZUH_API_URL}/security/user/authenticate",
            auth=HTTPBasicAuth(WAZUH_USER, WAZUH_PASS),
            verify=False,
            timeout=5
        )
        if response.status_code == 200:
            return response.json()['data']['token']
        print(f" [X] Wazuh Auth Error: {response.status_code}")
        return None
    except Exception as e:
        print(f" [X] Wazuh Connection Error: {e}")
        return None

def get_agent_id_by_ip(ip, headers):
    """
    Fetches the agent ID. 
    1. Checks if IP translation is needed.
    2. Prioritizes agents with 'active' status.
    """
    # Checks if there is an IP translation
    target_ip = IP_MAP.get(ip, ip)
    
    if target_ip != ip:
        print(f" [i] Translating Caldera IP ({ip}) -> Wazuh IP ({target_ip})")

    try:
        r = requests.get(f"{WAZUH_API_URL}/agents?limit=2000", headers=headers, verify=False)
        if r.status_code == 200:
            agents = r.json().get('data', {}).get('affected_items', [])

            best_match = None

            print(f"\n--- WAZUH DEBUG: Searching for {target_ip} ---")

            for agent in agents:
                a_ip = agent.get('ip', '0.0.0.0')
                a_status = agent.get('status', 'unknown')
                a_id = agent.get('id')
                a_name = agent.get('name')

                if a_ip == target_ip:
                    print(f" [?] Candidate found: {a_name} (ID: {a_id}) - Status: {a_status}")

                                        # If an active one is found, it's the immediate winner
                    if a_status == 'active':
                        print(f" [V] PERFECT MATCH! Using active agent: {a_id}")
                        return a_id

                    # If disconnected, keep as backup in case an active one isn't found
                    if best_match is None:
                        best_match = a_id

            if best_match:
                print(f" [!] Warning: No active agent found. Using the disconnected one: {best_match}")
                return best_match

            print(f" [X] NO agent found for IP {target_ip}.")
            return None
    except Exception as e:
        print(f"Error searching for agents: {e}")
        return None

def get_wazuh_alerts(agent_ip):
    token = get_token()
    if not token: return ["Error: Wazuh API Auth Failed."]

    headers = {'Authorization': f'Bearer {token}'}
    
    # 1. Smart ID Search
    agent_id = get_agent_id_by_ip(agent_ip, headers)
    
    
    if not agent_id:
        return [f"Error: Wazuh did not find an agent for IP {agent_ip}."]

    logs = []
    
    # 2. Fetch FIM Events (Syscheck)
    try:
        r_fim = requests.get(f"{WAZUH_API_URL}/syscheck/{agent_id}?limit=5&sort=-mtime", headers=headers, verify=False)
        if r_fim.status_code == 200:
            items = r_fim.json().get('data', {}).get('affected_items', [])
            for item in items:
                f_name = item.get('file')
                f_time = item.get('mtime', '')
                logs.append(f"[FIM] {f_time} - Modified: {f_name}")
    except: pass

    # 3. Fetch Vulnerabilities
    try:
        r_vuln = requests.get(f"{WAZUH_API_URL}/vulnerability/{agent_id}?limit=3&sort=-severity", headers=headers, verify=False)
        if r_vuln.status_code == 200:
            items = r_vuln.json().get('data', {}).get('affected_items', [])
            for v in items:
                logs.append(f"[VULN] {v.get('cve')} ({v.get('severity')}) - {v.get('title')}")
    except: pass

    if not logs:
        return [f"[Wazuh] Connected to Agent {agent_id}, but no recent alerts."]
    
  
    return logs


