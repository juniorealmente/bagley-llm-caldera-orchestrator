# Cognitive Cybersecurity Orchestrator (Red and Blue Team)

## Project Description
This repository contains the source code and reproducibility instructions for the implementation of an LLM-based orchestrator capable of autonomously integrating Red Team tactics (via MITRE CALDERA) and Blue Team monitoring (via Wazuh SIEM).

## Environment Reproducibility (Testbed)
To ensure accessibility and scientific transparency, the test environment does not rely on pre-packaged Virtual Machines. The infrastructure has been defined as code (IaC) and can be provisioned on any system compatible with Docker and automation scripts.

### Prerequisites
- Docker and Docker Compose installed on the host.
- Python 3.10 or higher.
- Two target machines (VMs or physical hosts) to act as victims: one running Windows (supported versions: 10, 11, or Server 2016/2019/2022) and another running a Debian-based Linux distribution (such as Ubuntu or Kali Linux).

### Step 1: Server Provisioning (Control Plane)
1. Clone this repository:
   `git clone https://github.com/juniorealmente/bagley-llm-caldera-orchestrator.git`
2. Access the project directory:
   `cd bagley-llm-caldera-orchestrator`
3. Spin up the CALDERA server using Docker Compose:
   `docker-compose up -d`
4. To provision the Wazuh SIEM, use the official automated installation script (All-in-one) on your main Linux machine or container:
   `curl -sO https://packages.wazuh.com/4.x/wazuh-install.sh && sudo bash ./wazuh-install.sh -a`

### Step 2: Target Agent Preparation (Victims)
On the machines that will act as attack targets, you must execute the provisioning scripts located in the `/scripts` folder of this repository. They will install and link the Wazuh and Caldera agents to the newly created servers.

**On the Linux target (Ubuntu):**
Execute the script in a terminal with root privileges:
`sudo bash scripts/install_linux_agent.sh <WAZUH_SERVER_IP> <CALDERA_SERVER_IP>`

**On the Windows target:**
Open PowerShell as Administrator and execute:
`.\scripts\install_windows_agent.ps1 -WazuhIP "<WAZUH_SERVER_IP>" -CalderaIP "<CALDERA_SERVER_IP>"`

### Step 3: Execution of the Cognitive Orchestrator
With the infrastructure provisioned and the agents reporting to the servers:
1. Install the Python dependencies:
   `pip install -r requirements.txt`
2. Configure your API keys (e.g., Google Gemini, Caldera API) in the `.env` file.
3. Start the orchestration engine:
   `python main_controller.py`

### Use Cases (Prompts)
Enter the following tactical objectives when prompted by the terminal to replicate the results presented in the dissertation:
1. **Windows SAM/SYSTEM:** `Simulate an offline credential theft (T1003.002)...`
2. **Linux PwnKit:** `Verify if the system is vulnerable to the PwnKit...`
3. **Cross-platform:** `Simulate a post-compromise reconnaissance and staging phase...`

## Extensibility (Future Work)
The architecture of this orchestrator was designed in a modular way. Although the current implementation of the cognitive module uses the Google Gemini API (`google-generativeai`), the system is LLM-agnostic. Future developers can easily create new connectors for OpenAI, Anthropic, or local LLMs (such as Llama 3 via Ollama) by simply adapting the communication interface in the `src/` folder, without the need to alter the Caldera orchestration engine or the Wazuh ingestion routines.
