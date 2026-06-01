#!/bin/bash
set -euo pipefail

# ── Docker ────────────────────────────────────────────────────────────────────
dnf update -y
dnf install -y docker
systemctl enable --now docker
usermod -aG docker ec2-user

# Docker Compose v2 plugin
mkdir -p /usr/local/lib/docker/cli-plugins
curl -fsSL \
  "https://github.com/docker/compose/releases/download/v2.27.0/docker-compose-linux-x86_64" \
  -o /usr/local/lib/docker/cli-plugins/docker-compose
chmod +x /usr/local/lib/docker/cli-plugins/docker-compose

# ── Config files ──────────────────────────────────────────────────────────────
mkdir -p /opt/monitoring/grafana/datasources

# Prometheus — only scrapes Pushgateway; both Lambda and SageMaker push here
cat > /opt/monitoring/prometheus.yml <<'PROMEOF'
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: pushgateway
    honor_labels: true
    static_configs:
      - targets: ["pushgateway:9091"]
PROMEOF

# Grafana datasource
cat > /opt/monitoring/grafana/datasources/prometheus.yml <<'DSEOF'
apiVersion: 1
datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    uid: prometheus
    jsonData:
      timeInterval: "15s"
DSEOF

# Docker Compose stack
cat > /opt/monitoring/docker-compose.yml <<COMPOSEEOF
services:
  prometheus:
    image: prom/prometheus:latest
    ports: ["9090:9090"]
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml:ro
    restart: unless-stopped

  pushgateway:
    image: prom/pushgateway:latest
    ports: ["9091:9091"]
    restart: unless-stopped

  grafana:
    image: grafana/grafana:latest
    ports: ["3000:3000"]
    environment:
      GF_SECURITY_ADMIN_PASSWORD: "${grafana_password}"
      GF_PATHS_PROVISIONING: /etc/grafana/provisioning
    volumes:
      - ./grafana/datasources:/etc/grafana/provisioning/datasources:ro
      - grafana-data:/var/lib/grafana
    restart: unless-stopped

volumes:
  grafana-data:
COMPOSEEOF

# ── Start ─────────────────────────────────────────────────────────────────────
cd /opt/monitoring
docker compose pull -q
docker compose up -d

# ── MLflow ────────────────────────────────────────────────────────────────────
dnf install -y python3-pip
pip3 install mlflow
mkdir -p /opt/mlflow/artifacts
nohup mlflow server \
  --host 0.0.0.0 \
  --port 5000 \
  --backend-store-uri sqlite:////opt/mlflow/mlflow.db \
  --default-artifact-root /opt/mlflow/artifacts \
  > /var/log/mlflow.log 2>&1 &
