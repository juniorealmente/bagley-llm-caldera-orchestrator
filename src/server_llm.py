from flask import Flask, request, jsonify
import requests
import json
import re
import logging
import time

app = Flask(__name__)
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

ACTIVE_PROVIDER = "cerebras" # Options: "gemini", "openai", "anthropic", "ollama"
MAX_OUTPUT_CHARS = 3000
MAX_MEMORY_HISTORY = 10

GEMINI_API_KEY = "INSERT_YOUR_GEMINI_API_KEY_HERE"
GROQ_API_KEY = "INSERT_YOUR_GROQ_API_KEY_HERE"
CEREBRAS_API_KEY = "INSERT_YOUR_CEREBRAS_API_KEY_HERE"
OPENAI_API_KEY = "INSERT_YOUR_OPENAI_API_KEY_HERE"
ANTHROPIC_API_KEY = "INSERT_YOUR_ANTHROPIC_API_KEY_HERE"

MODEL_NAME_GEMINI ="gemini-3.5-flash" # Here, you change the LLM model to the one available to you.
MODEL_NAME_GROQ = "llama-3.1-8b-instant" # Here, you change the LLM model to the one available to you.
MODEL_NAME_CEREBRAS = "gpt-oss-120b" # Here, you change the LLM model to the one available to you.
MODEL_NAME_OPENAI = "gpt-4-turbo" # Here, you change the LLM model to the one available to you.
MODEL_NAME_ANTHROPIC = "claude-3-opus-20240229" # Here, you change the LLM model to the one available to you.
MODEL_NAME_OLLAMA = "llama3" # Here, you change the LLM model to the one available to you.
OLLAMA_ENDPOINT = "http://127.0.0.1:11434/api/generate"

CURRENT_MISSION = {
    "active": False,
    "objective": None,
    "generated_command": None,
    "remediation_advice": None,
    "description": None,
    "timestamp": 0
}

KNOWLEDGE_SOURCES = {
   "NIST_NVD": "https://nvd.nist.gov",
   "LOLBINS": "https://lolbas-project.github.io/",
   "0xMarcio_PoC": "https://github.com/0xMarcio/cve"
}

OS_SYNTAX_MAP = {
    'windows': 'PowerShell One-Liner (Windows Native)',
    'linux': 'Bash Script (Linux Native)',
    'kali': 'Bash Script (Kali Linux Tools/Native)',
    'ubuntu': 'Bash Script (Ubuntu/Debian Native)',
    'debian': 'Bash Script (Debian Native)',
    'centos': 'Bash Script (RHEL/CentOS Native)',
    'darwin': 'Zsh/Bash Script (macOS Native)',
    'macos': 'Zsh/Bash Script (macOS Native)',
    'solaris': 'Ksh/Bash Script (Solaris Native)',
    'freebsd': 'Csh/Tcsh/Bash Script (FreeBSD Native)',
    'android': 'Shell Script (Android ADB/Termux)',
    'unknown': 'Bash Script (Generic Unix) or PowerShell (if Windows-like)'
}

def get_syntax_guide(platform_name):
    platform = platform_name.lower().strip()
    if platform in OS_SYNTAX_MAP: return OS_SYNTAX_MAP[platform]
    if 'win' in platform: return OS_SYNTAX_MAP['windows']
    if 'bsd' in platform: return OS_SYNTAX_MAP['freebsd']
    if 'sun' in platform or 'oracle' in platform: return OS_SYNTAX_MAP['solaris']
    if 'mac' in platform or 'apple' in platform: return OS_SYNTAX_MAP['macos']
    return OS_SYNTAX_MAP['linux']

def check_nist_connection():
    print("[*] Validating access to the National Vulnerability Database (NIST NVD)...", end=" ")
    try:
        r = requests.head("https://nvd.nist.gov", timeout=3)
        if r.status_code == 200:
            print(f"SUCCESS (HTTP 200)")
            return True
    except:
        print("FAILURE (Offline/Simulated Mode Activated)")
    return False

def _query_gemini(prompt, temperature):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME_GEMINI}:generateContent?key={GEMINI_API_KEY}"
    try:
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": temperature, "maxOutputTokens": 4096}
        }
        response = requests.post(url, headers={'Content-Type': 'application/json'}, json=payload, timeout=130)
        if response.status_code == 200:
            return response.json()['candidates'][0]['content']['parts'][0]['text']
        print(f"\n[!] GEMINI API ERROR: {response.text}\n")
        return None
    except Exception as e:
        print(f"[!] Python Connection Error: {e}")
        return None

def _query_groq(prompt, temperature):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": MODEL_NAME_GROQ,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": 4096
    }
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=130)
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
        print(f"\n[!] GROQ API ERROR: {response.text}\n")
        return None
    except Exception as e:
        print(f"[!] Python Connection Error (Groq): {e}")
        return None

def _query_cerebras(prompt, temperature):
    url = "https://api.cerebras.ai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {CEREBRAS_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": MODEL_NAME_CEREBRAS,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": 4096
    }
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=130)
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
        print(f"\n[!] CEREBRAS API ERROR: {response.text}\n")
        return None
    except Exception as e:
        print(f"[!] Python Connection Error (Cerebras): {e}")
        return None

def query_llm(prompt, temperature=0.1):
    if ACTIVE_PROVIDER == "gemini": return _query_gemini(prompt, temperature)
    if ACTIVE_PROVIDER == "groq": return _query_groq(prompt, temperature)
    if ACTIVE_PROVIDER == "cerebras": return _query_cerebras(prompt, temperature)
    return None

def extract_json(text):
    if not text: return None
    try:
        clean = re.sub(r'```json|```', '', text, flags=re.IGNORECASE).strip()
        start = clean.find('{')
        end = clean.rfind('}') + 1
        return json.loads(clean[start:end])
    except:
        return None

@app.route('/analyze_objective', methods=['POST'])
def analyze_objective():
    global CURRENT_MISSION
    data = request.json
    user_objective = data.get('objective', '')
    
    previous_errors = data.get('previous_errors', [])[-MAX_MEMORY_HISTORY:]
    
    raw_platform = data.get('platform', 'linux').lower().strip()
    privilege = data.get('privilege', 'User')
    lang_guide = get_syntax_guide(raw_platform)

    error_context = ""
    if previous_errors:
        error_context = "\n--- STATE MEMORY (PREVIOUS FAILURE ANALYSIS) ---\n"
        error_context += "MANDATORY DIAGNOSIS: Read the failures below. Identify the root cause of each error and DO NOT REPEAT THE TACTIC THAT FAILED.\n"
        for i, err in enumerate(previous_errors):
            err_str = str(err).lower()
            err_truncated = str(err)[:300]

            hint = ""
            if "not found" in err_str or "não encontrado" in err_str:
                hint = "-> The binary does not exist on the system. Change the tool (E.g.: if curl failed, use wget, python3 or native bash)."
            elif "permission denied" in err_str or "not permitted" in err_str:
                hint = "-> Privilege block (e.g., Guest) or AppArmor/SELinux. Abort root/sudo commands. Change target to low privilege enumeration in /home/ or /tmp/."
            elif "syntax" in err_str or "usage" in err_str:
                hint = "-> Syntax error. Correct the command arguments."
            else:
                hint = "-> Tactic blocked. Try a different LotL (Living off the Land) approach."

            error_context += f"Attempt {i+1} failed with error: {err_truncated}\n{hint}\n\n"

    priv_context = "You have ROOT privileges (Can install packages and change global configurations)." if privilege.lower() in ['elevated', 'root'] else "You have LIMITED privileges (USER/GUEST). Extreme focus on low privilege exploitation and stealth."

    prompt = f"""
    SYSTEM: BAGLEY KERNEL - SENIOR AUDITOR AND RED TEAM AGENT (PCI DSS AWARE).
    Reply ONLY with a valid and decodable JSON. You are a 'Problem Solver'. Never give up.

    TARGET CONTEXT:
    - OS: {raw_platform.upper()} ({lang_guide})
    - Privilege: {privilege.upper()}
    - Guideline: {priv_context}
    {error_context}

    OBJECTIVE: "{user_objective}"

    TACTICAL INSTRUCTIONS - "AT ALL COSTS" ADAPTATION HIERARCHY:
    1. Root Cause Analysis: Based on the errors above, identify why the attack failed.
    2. Immediate Adaptation: If tool X does not exist, use tool Y. If permission Z was denied, change the execution directory or the attack focus.
    3. Tactics Ladder: First try OS native binaries (LotL). If that fails, try standard OS tools. If you are root and everything fails, write commands to download or install vital dependencies.
    4. Reasoning: Hide the complexity. Use the 'reasoning' field to plan the bypass maneuver based strictly on reading past errors BEFORE generating the command.

    MANDATORY OUTPUT SCHEMA:
    {{
        "reasoning": "Your diagnosis of the errors and the thought chain of the new tactic. Explain which alternative path you chose and why.",
        "command": "technical_command_here",
        "description": "MITRE ID and Adapted Technique Name",
        "remediation": "NIST technical summary of countermeasure",
        "platform": "{raw_platform}",
        "executor": "{'psh' if 'windows' in raw_platform else 'sh'}"
    }}
    """
    
    resp = query_llm(prompt, temperature=0.1)
    json_resp = extract_json(resp)
    
    if json_resp and json_resp.get('command'):
        CURRENT_MISSION = {
            "active": True,
            "objective": user_objective,
            "generated_command": json.dumps(json_resp),
            "timestamp": time.time()
        }
        return jsonify(CURRENT_MISSION)
    else:
        return jsonify({"error": "Failed to generate instruction.", "debug": resp}), 400

@app.route('/analyze_result', methods=['POST'])
def analyze_result():
    data = request.json
    cmd = data.get('command')
    
    raw_output = data.get('output', '')
    output = raw_output[:MAX_OUTPUT_CHARS] + ("\n... [TRUNCATED TO PRESERVE TOKENS]" if len(raw_output) > MAX_OUTPUT_CHARS else "")
    
    wazuh_logs = data.get('wazuh_logs', '[]')
    
    prompt = f"""
    ACT AS: Senior Digital Forensics Analyst and Compliance Auditor.
    OBTAINED DATA:
    - Executed Command: {cmd}
    - System Output: {output}
    - Security Alerts (Wazuh): {wazuh_logs}

    Structure a professional report detailing:
    ### 1. Technical Execution Diagnosis
    ### 2. Data Exposure (Violations and DLP)
    ### 3. Visibility Efficacy (SIEM/Wazuh Analysis)
    ### 4. MITRE ATT&CK Mapping & CVE Identification
    ### 5. Practical Detection Rules (Wazuh XML) and Hardening (Informative)
    """
    analysis = query_llm(prompt, temperature=0.3)
    return jsonify({"analysis": analysis or "Analysis failed."})

if __name__ == '__main__':
    print(f"\n[V11.0] BAGLEY SERVER LLM ACTIVE - PROBLEM SOLVER ENABLED")
    check_nist_connection() 
    app.run(host='0.0.0.0', port=8001)
