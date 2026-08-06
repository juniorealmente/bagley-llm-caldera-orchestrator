# BAGLEY: LLM-Based Automated Orchestration of Purple Teaming Cycles and MITRE CALDERA

## Project Description
This repository contains the source code and reproducibility instructions for the implementation of an LLM-based orchestrator capable of autonomously integrating Red Team tactics (via MITRE CALDERA) and Blue Team monitoring (via Wazuh SIEM).

## Environment Reproducibility (Testbed)

** Quick Start (Pre-configured VM):**
For a plug-and-play experience, a fully provisioned Virtual Machine containing the entire environment (Caldera, Wazuh, and the Bagley Orchestrator) is available for download. 
 **[Download the Pre-configured VM via Google Drive here](https://drive.google.com/drive/folders/1gH6jwN7ASjL7zV4Kx6icIenPEEWa31Lc?usp=sharing)**

** Test Evidence and Scenarios:**
You can view the reports, logs, and types of tests performed during the evaluation of this orchestrator in our shared folder.
 **[Access the Test Evidence Folder on Google Drive here](https://drive.google.com/drive/folders/1BOq95nTBnr9YPRqybyWO1YPnEBUiV8jk?usp=sharing)**

To ensure accessibility and scientific transparency, the test environment can also be built from scratch. The infrastructure has been defined as code (IaC) and can be provisioned on any system compatible with Docker and automation scripts.

### Prerequisites
- Docker and Docker Compose installed on the host.
- Python 3.10 or higher.
- Two target machines (VMs or physical hosts) to act as victims: one running Windows (supported versions: 10, 11, or Server 2016/2019/2022) and another running a Debian-based Linux distribution (such as Ubuntu or Kali Linux).

### Step 1: Server Provisioning (Control Plane)
1. Clone this repository:
   `git clone https://github.com/juniorealmente/bagley-llm-caldera-orchestrator.git`
2. Access the project directory:
   `cd bagley-llm-caldera-orchestrator`
3. To provision the Wazuh SIEM, use the official automated installation script (All-in-one) on your main Linux machine or container:
   `curl -sO https://packages.wazuh.com/4.x/wazuh-install.sh && sudo bash ./wazuh-install.sh -a`

**Web Dashboards Default Access:**
Once the foundational services are running, you can access the graphical interfaces using the following default credentials:
- **Wazuh SIEM:** `https://192.168.56.105` (Username: `admin` | Password: `SecretPassword`)
- **MITRE CALDERA:** `http://localhost:8888` (Username: `admin` | Password: `admin`)

### Step 2: Target Agent Preparation (Victims)
To execute attacks, you need to deploy a Caldera Agent (Sandcat) on your target machines. 

**Manual Deployment via Dashboard:**
1. Log in to the Caldera Dashboard (`http://localhost:8888`).
2. Navigate to **Campaigns > Agents** and click **Deploy an agent**.
3. Select **Sandcat**, choose your target's Operating System, and copy the provided deployment command.
4. Run the command on your target victim machine. Once executed, the agent will appear as "ONLINE" in the Caldera dashboard.

*(Alternatively, you can use the automated provisioning scripts located in the `/scripts` folder of this repository to link Wazuh and Caldera simultaneously).*

**On the Linux target (Ubuntu):**
Execute the script in a terminal with root privileges:
`sudo bash scripts/install_linux_agent.sh <WAZUH_SERVER_IP> <CALDERA_SERVER_IP>`

**On the Windows target:**
Open PowerShell as Administrator and execute:
`.\scripts\install_windows_agent.ps1 -WazuhIP "<WAZUH_SERVER_IP>" -CalderaIP "<CALDERA_SERVER_IP>"`

### Step 3: Execution of the Cognitive Orchestrator
With the infrastructure provisioned and the agents reporting to the servers, configure your API keys in `main_controller.py`, `wazuh_client.py`, and `server_llm.py` by replacing the placeholder strings.

You will need to open **three separate terminals** in the project directory to run the orchestrator:

**Terminal 1: Start MITRE CALDERA Server**
```bash
cd caldera
source venv/bin/activate
python server.py --insecure

**Terminal 2: Start the Cognitive LLM Router**
cd caldera
source venv/bin/activate
Note: here you need to enter the API key for the LLM (Gemini, OpenAI, etc..) model you intend to use, along with the model name; simply type `nano server_llm.py` to find the necessary fields.
python server_llm.py

**Terminal 3: Execute the Main Controller (BAGLEY)**
cd caldera
source venv/bin/activate
python main_controller.py

#### Understanding the Workflow (Execution Walkthrough)
When you run `main_controller.py`, Bagley initializes its cognitive engine and scans the network for targets. Here is a breakdown of the interaction flow:

```text
(venv) caldera@caldera-VirtualBox:~/caldera$ python main_controller.py
                                                                                
              ██████╗  █████╗  ██████╗ ██╗      ███████╗██╗   ██╗               
              ██╔══██╗██╔══██╗██╔════╝ ██║      ██╔════╝╚██╗ ██╔╝               
              ██████╔╝███████║██║  ███╗██║      █████╗   ╚████╔╝                
              ██╔══██╗██╔══██║██║   ██║██║      ██╔══╝    ╚██╔╝                 
              ██████╔╝██║  ██║╚██████╔╝███████╗ ███████╗   ██║                  
              ╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚══════╝ ╚══════╝   ╚═╝                  
                                                                                
Hi. I am Bagley. I am your analytical and operational thought.
I am ready to simulate adversaries and diagnose defenses.

>> SCANNING NETWORK...
                                                                                
    NUM      PAW        GROUP    PLATFORM    PRIVILEGE     IP          STATUS  
 ────────────────────────────────────────────────────────────────────────────── 
     1       ihjuyp     red      linux       User          10.0.2.15   ONLINE  
                                                                                

>> Select IDs (e.g., 1,2), Group (e.g., red) or 'all': 1

>> Tactical Objective: The target has a VPN connection that can access the site: https://xxxxxxxxxxx. The objective is to evaluate the presence of Rate Limiting controls and automation detection within the application's login mechanism. Use curl within a loop of 1 to 500 to send consecutive POST requests, simulating invalid login attempts against the 'xxxxxxxxx' endpoint. Monitor whether the application maintains a stable response time or activates a network defense mechanism, such as a temporary IP block (HTTP 429) or an artificial response delay (Tarpitting).

──────────────────────────── TARGET: ihjuyp (LINUX) ────────────────────────────
Attempt 1/10: for i in $(seq 1 100); do curl -s -o /dev/null -w "%{http_code} %{time_total}\n" -X POST [xxxxxxxxxxxxxxxxxxxxxxxxxxxxx](xxxxxxxxxxxxxxxxxxxxxxxxxxxx); done


### Execution Workflow (Bagley Report Lifecycle)

The following flowchart illustrates the autonomous lifecycle of a tactical operation, from the initial prompt to the final AI-generated defensive report:

```text
 ┌─────────────────────────────────────────┐
 │          1. Target Selection            │
 │ (Bagley scans network for active agents)│
 └────────────────────┬────────────────────┘
                      ▼
 ┌─────────────────────────────────────────┐
 │       2. Tactical Objective Input       │
 │   (User defines the attack in prompt)   │
 └────────────────────┬────────────────────┘
                      ▼
 ┌─────────────────────────────────────────┐
 │   3. Payload Generation & Execution     │
 │(LLM translates intent to native command)│
 └────────────────────┬────────────────────┘
                      ▼
 ┌─────────────────────────────────────────┐
 │        4. Telemetry Monitoring          │
 │ (X-RAY Mode tracks Caldera API status)  │
 └────────────────────┬────────────────────┘
                      ▼
 ┌─────────────────────────────────────────┐
 │    5. Output Capture (Raw Report)       │
 │ (System collects the execution results) │
 └────────────────────┬────────────────────┘
                      ▼
 ┌─────────────────────────────────────────┐
 │  6. Defense Detection (Blue Team Check) │
 │ (Checks if Wazuh SIEM triggered alerts) │
 └────────────────────┬────────────────────┘
                      ▼
 ┌─────────────────────────────────────────┐
 │   7. Cognitive Analysis (AI Forensics)  │
 │(LLM analyzes raw output and SIEM alerts)│
 └────────────────────┬────────────────────┘
                      ▼
 ┌─────────────────────────────────────────┐
 │   8. MITRE ATT&CK & CVE Identification  │
 │ (Maps techniques and potential exploits)│
 └────────────────────┬────────────────────┘
                      ▼
 ┌─────────────────────────────────────────┐
 │  9. Hardening & Detection Rules Output  │
 │ (Proposes custom Wazuh XML tuning rules)│
 └────────────────────┬────────────────────┘
                      ▼
 ┌─────────────────────────────────────────┐
 │       10. Final Report Generation       │
 │   (Consolidated integrated operation)   │
 └─────────────────────────────────────────┘


## Conclusion and Advanced Use Cases

The Bagley Cognitive Orchestrator demonstrates significant versatility across diverse cybersecurity workflows. Beyond standard MITRE ATT&CK TTP emulations, it can be adapted to evaluate operating system hardening, validate endpoint security controls, and simulate complex, multi-stage attack scenarios across hybrid environments.

### Maximizing Capabilities with a Kali Linux Agent
While Bagley operates effectively using native operating system binaries (such as PowerShell or bash), its autonomous orchestration becomes **exceptionally powerful when deploying a Caldera agent on a Kali Linux host** equipped with pre-installed penetration testing tools.

In a Kali Linux environment, Bagley is not limited to basic scripts. By simply defining your high-level goal in the `>> Tactical Objective:` prompt, the LLM cognitive engine autonomously identifies and leverages specialized security tools to execute elaborate assessments:

*   **Web Application & URL Security:** Instead of relying solely on basic HTTP requests, the LLM can autonomously invoke tools like `curl`, `nikto`, `sqlmap`, or `ffuf` to conduct deep reconnaissance, rate-limiting evaluations, and vulnerability scanning against target URLs.
*   **Software & Service Auditing:** Bagley can inspect installed software, enumerate running services, and dynamically craft payloads or exploitation scripts based on the specific weaknesses it discovers.
*   **Autonomous Tool Orchestration:** Because the LLM understands the CLI syntax and flags of standard penetration testing utilities, providing it with a well-stocked Kali host allows the agent to design and execute sophisticated, multi-tool attack chains on its own—transforming a simple natural language prompt into an advanced, automated security evaluation.
