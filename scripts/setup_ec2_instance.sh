#!/usr/bin/env bash
# DocQuery - Initial EC2 Instance Setup
# Run this script on a fresh Ubuntu 22.04 EC2 instance

set -euo pipefail

echo "============================================"
echo "DocQuery - EC2 Instance Setup"
echo "============================================"

# Update system packages
echo "→ Updating system packages..."
sudo apt-get update
sudo apt-get upgrade -y

# Install Docker
echo ""
echo "→ Installing Docker..."
sudo apt-get install -y apt-transport-https ca-certificates curl software-properties-common
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io

# Install Docker Compose
echo ""
echo "→ Installing Docker Compose..."
DOCKER_COMPOSE_VERSION="v2.24.0"
sudo curl -L "https://github.com/docker/compose/releases/download/${DOCKER_COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Add user to docker group
echo ""
echo "→ Adding user to docker group..."
sudo usermod -aG docker $USER

# Install Node.js 20
echo ""
echo "→ Installing Node.js 20..."
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs

# Install system utilities
echo ""
echo "→ Installing system utilities..."
sudo apt-get install -y git make nginx certbot python3-certbot-nginx htop vim

# Install AWS CLI
echo ""
echo "→ Installing AWS CLI..."
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip -q awscliv2.zip
sudo ./aws/install
rm -rf awscliv2.zip aws

# Install CloudWatch agent (optional)
echo ""
echo "→ Installing CloudWatch agent..."
wget -q https://s3.amazonaws.com/amazoncloudwatch-agent/ubuntu/amd64/latest/amazon-cloudwatch-agent.deb
sudo dpkg -i -E ./amazon-cloudwatch-agent.deb
rm amazon-cloudwatch-agent.deb

# Create application directory
echo ""
echo "→ Creating application directory..."
mkdir -p ~/docquery
cd ~/docquery

# Configure firewall (UFW)
echo ""
echo "→ Configuring firewall..."
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 8000/tcp
sudo ufw allow 3000/tcp
echo "y" | sudo ufw enable || true

# Optimize system settings
echo ""
echo "→ Optimizing system settings..."
sudo tee -a /etc/sysctl.conf > /dev/null << EOF

# DocQuery optimizations
net.core.somaxconn = 1024
net.ipv4.tcp_max_syn_backlog = 2048
vm.swappiness = 10
EOF
sudo sysctl -p

# Create swap file (if not exists)
if [ ! -f /swapfile ]; then
    echo ""
    echo "→ Creating swap file..."
    sudo fallocate -l 2G /swapfile
    sudo chmod 600 /swapfile
    sudo mkswap /swapfile
    sudo swapon /swapfile
    echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
fi

# Verify installations
echo ""
echo "============================================"
echo "✓ Installation Complete!"
echo "============================================"
docker --version
docker-compose --version
node --version
npm --version
aws --version
echo "============================================"
echo ""
echo "NEXT STEPS:"
echo "1. Clone your repository: git clone <repo-url> ~/docquery"
echo "2. Configure environment variables in ~/docquery/backend/.env"
echo "3. Run: cd ~/docquery && docker-compose up -d"
echo "4. Create admin user: docker-compose exec backend python scripts/create_admin.py"
echo ""
echo "NOTE: You may need to log out and back in for docker group permissions"
echo "============================================"
