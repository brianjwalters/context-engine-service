#!/bin/bash
###############################################################################
# Context Engine Service - Monitoring Stack Deployment Script
#
# Purpose: Automated deployment of Prometheus, Grafana, Alertmanager, and
#          Node Exporter for comprehensive Context Engine monitoring
#
# Platform: Ubuntu 20.04+ with systemd
# Services: Prometheus, Grafana, Alertmanager, Node Exporter
# Author: Linux Systems Engineer (Claude)
# Version: 1.0.0
# Date: 2025-10-23
#
# Usage:
#   sudo ./deploy_monitoring.sh --component=all
#   sudo ./deploy_monitoring.sh --component=prometheus --verbose
#   sudo ./deploy_monitoring.sh --dry-run
#   sudo ./deploy_monitoring.sh --uninstall
#
###############################################################################

set -euo pipefail
IFS=$'\n\t'

###############################################################################
# Configuration & Constants
###############################################################################

# Script metadata
readonly SCRIPT_VERSION="1.0.0"
readonly SCRIPT_NAME="$(basename "${BASH_SOURCE[0]}")"
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Default versions (override with environment variables)
readonly PROMETHEUS_VERSION="${PROMETHEUS_VERSION:-2.45.0}"
readonly GRAFANA_VERSION="${GRAFANA_VERSION:-10.2.0}"
readonly ALERTMANAGER_VERSION="${ALERTMANAGER_VERSION:-0.26.0}"
readonly NODE_EXPORTER_VERSION="${NODE_EXPORTER_VERSION:-1.6.1}"

# Installation paths
readonly INSTALL_ROOT="/opt"
readonly PROMETHEUS_DIR="${INSTALL_ROOT}/prometheus"
readonly ALERTMANAGER_DIR="${INSTALL_ROOT}/alertmanager"
readonly NODE_EXPORTER_DIR="${INSTALL_ROOT}/node_exporter"
readonly GRAFANA_DIR="/usr/share/grafana"

# Configuration paths
readonly ETC_PROMETHEUS="/etc/prometheus"
readonly ETC_ALERTMANAGER="/etc/alertmanager"
readonly ETC_GRAFANA="/etc/grafana"

# Data paths
readonly VAR_LIB_PROMETHEUS="/var/lib/prometheus"
readonly VAR_LIB_ALERTMANAGER="/var/lib/alertmanager"
readonly VAR_LIB_GRAFANA="/var/lib/grafana"

# Log paths
readonly LOG_DIR="/var/log/luris"
readonly DEPLOYMENT_LOG="${LOG_DIR}/monitoring-deployment.log"

# Service configuration
readonly CONTEXT_ENGINE_IP="10.10.0.87"
readonly CONTEXT_ENGINE_PORT="8015"
readonly GRAPHRAG_PORT="8010"
readonly PROMPT_SERVICE_PORT="8003"
readonly SUPABASE_PORT="8002"

# Ports
readonly PROMETHEUS_PORT="9090"
readonly GRAFANA_PORT="3000"
readonly ALERTMANAGER_PORT="9093"
readonly NODE_EXPORTER_PORT="9100"

# Required disk space (bytes)
readonly REQUIRED_DISK_SPACE=$((5 * 1024 * 1024 * 1024))  # 5GB

# Color codes
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m' # No Color

###############################################################################
# Global Variables
###############################################################################

DRY_RUN=0
VERBOSE=0
COMPONENT="all"
UNINSTALL=0
GRAFANA_ADMIN_PASSWORD="${GRAFANA_ADMIN_PASSWORD:-}"
BACKUP_ENABLED=1
ROLLBACK_STACK=()

###############################################################################
# Logging Functions
###############################################################################

log_info() {
    local message="$1"
    local timestamp
    timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${GREEN}[INFO]${NC} ${message}"
    echo "[${timestamp}] [INFO] ${message}" >> "${DEPLOYMENT_LOG}"
}

log_warn() {
    local message="$1"
    local timestamp
    timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${YELLOW}[WARN]${NC} ${message}"
    echo "[${timestamp}] [WARN] ${message}" >> "${DEPLOYMENT_LOG}"
}

log_error() {
    local message="$1"
    local timestamp
    timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${RED}[ERROR]${NC} ${message}" >&2
    echo "[${timestamp}] [ERROR] ${message}" >> "${DEPLOYMENT_LOG}"
}

log_debug() {
    if [[ ${VERBOSE} -eq 1 ]]; then
        local message="$1"
        local timestamp
        timestamp=$(date '+%Y-%m-%d %H:%M:%S')
        echo -e "${BLUE}[DEBUG]${NC} ${message}"
        echo "[${timestamp}] [DEBUG] ${message}" >> "${DEPLOYMENT_LOG}"
    fi
}

log_step() {
    local step="$1"
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}▶ ${step}${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    log_info "Step: ${step}"
}

###############################################################################
# Utility Functions
###############################################################################

command_exists() {
    command -v "$1" >/dev/null 2>&1
}

execute_command() {
    local cmd="$*"
    log_debug "Executing: ${cmd}"

    if [[ ${DRY_RUN} -eq 1 ]]; then
        log_info "[DRY RUN] Would execute: ${cmd}"
        return 0
    fi

    if ! eval "${cmd}" >> "${DEPLOYMENT_LOG}" 2>&1; then
        log_error "Command failed: ${cmd}"
        return 1
    fi
    return 0
}

prompt_user() {
    local message="$1"
    local default="${2:-n}"

    if [[ ${DRY_RUN} -eq 1 ]]; then
        log_info "[DRY RUN] Would prompt: ${message}"
        return 0
    fi

    local response
    read -r -p "${message} [y/N]: " response
    response="${response:-${default}}"

    if [[ "${response,,}" == "y" ]]; then
        return 0
    else
        return 1
    fi
}

add_rollback_action() {
    local action="$1"
    ROLLBACK_STACK+=("${action}")
    log_debug "Added rollback action: ${action}"
}

execute_rollback() {
    log_warn "Executing rollback actions..."

    # Execute in reverse order
    for ((i=${#ROLLBACK_STACK[@]}-1; i>=0; i--)); do
        local action="${ROLLBACK_STACK[$i]}"
        log_debug "Rollback: ${action}"
        eval "${action}" || true
    done

    log_info "Rollback completed"
}

###############################################################################
# Prerequisites Check Functions
###############################################################################

check_root() {
    log_step "Checking root privileges"

    if [[ ${EUID} -ne 0 ]]; then
        log_error "This script must be run as root or with sudo"
        log_info "Usage: sudo ${SCRIPT_NAME} [options]"
        exit 1
    fi

    log_info "✓ Running as root"
}

check_ubuntu_version() {
    log_step "Checking Ubuntu version"

    if [[ ! -f /etc/os-release ]]; then
        log_error "/etc/os-release not found"
        exit 1
    fi

    source /etc/os-release

    if [[ "${ID}" != "ubuntu" ]]; then
        log_error "This script is designed for Ubuntu (detected: ${ID})"
        exit 1
    fi

    local version_major
    version_major=$(echo "${VERSION_ID}" | cut -d. -f1)

    if [[ ${version_major} -lt 20 ]]; then
        log_error "Ubuntu 20.04 or higher required (detected: ${VERSION_ID})"
        exit 1
    fi

    log_info "✓ Ubuntu ${VERSION_ID} detected"
}

check_systemd() {
    log_step "Checking systemd"

    if ! command_exists systemctl; then
        log_error "systemd not found or not running"
        exit 1
    fi

    if ! systemctl is-system-running --quiet 2>/dev/null; then
        log_warn "systemd is running but may be in degraded state"
    fi

    log_info "✓ systemd is operational"
}

check_network() {
    log_step "Checking network connectivity"

    local test_hosts=(
        "github.com"
        "grafana.com"
        "prometheus.io"
    )

    for host in "${test_hosts[@]}"; do
        if ! ping -c 1 -W 2 "${host}" >/dev/null 2>&1; then
            log_error "Cannot reach ${host} - check network connectivity"
            exit 1
        fi
        log_debug "✓ Can reach ${host}"
    done

    log_info "✓ Network connectivity verified"
}

check_disk_space() {
    log_step "Checking available disk space"

    local available_space
    available_space=$(df -B1 / | awk 'NR==2 {print $4}')

    if [[ ${available_space} -lt ${REQUIRED_DISK_SPACE} ]]; then
        log_error "Insufficient disk space"
        log_error "Required: $(numfmt --to=iec ${REQUIRED_DISK_SPACE})"
        log_error "Available: $(numfmt --to=iec ${available_space})"
        exit 1
    fi

    log_info "✓ Sufficient disk space: $(numfmt --to=iec ${available_space})"
}

check_port_available() {
    local port="$1"
    local service_name="$2"

    if ss -tuln | grep -q ":${port} "; then
        log_error "Port ${port} is already in use (required for ${service_name})"
        log_info "Check with: sudo lsof -i :${port}"
        return 1
    fi

    log_debug "✓ Port ${port} available for ${service_name}"
    return 0
}

check_ports() {
    log_step "Checking required ports"

    local all_ports_available=1

    if [[ "${COMPONENT}" == "all" ]] || [[ "${COMPONENT}" == "prometheus" ]]; then
        check_port_available "${PROMETHEUS_PORT}" "Prometheus" || all_ports_available=0
    fi

    if [[ "${COMPONENT}" == "all" ]] || [[ "${COMPONENT}" == "grafana" ]]; then
        check_port_available "${GRAFANA_PORT}" "Grafana" || all_ports_available=0
    fi

    if [[ "${COMPONENT}" == "all" ]] || [[ "${COMPONENT}" == "alertmanager" ]]; then
        check_port_available "${ALERTMANAGER_PORT}" "Alertmanager" || all_ports_available=0
    fi

    if [[ ${all_ports_available} -eq 0 ]]; then
        log_error "One or more required ports are in use"
        exit 1
    fi

    log_info "✓ All required ports available"
}

###############################################################################
# Prometheus Installation Functions
###############################################################################

install_prometheus() {
    log_step "Installing Prometheus ${PROMETHEUS_VERSION}"

    # Create prometheus user
    if ! id -u prometheus >/dev/null 2>&1; then
        log_info "Creating prometheus user"
        execute_command "useradd --no-create-home --shell /bin/false prometheus"
        add_rollback_action "userdel prometheus"
    else
        log_debug "prometheus user already exists"
    fi

    # Create directories
    log_info "Creating Prometheus directories"
    execute_command "mkdir -p ${ETC_PROMETHEUS}"
    execute_command "mkdir -p ${ETC_PROMETHEUS}/rules"
    execute_command "mkdir -p ${VAR_LIB_PROMETHEUS}"
    add_rollback_action "rm -rf ${ETC_PROMETHEUS} ${VAR_LIB_PROMETHEUS}"

    # Download Prometheus
    local download_url="https://github.com/prometheus/prometheus/releases/download/v${PROMETHEUS_VERSION}/prometheus-${PROMETHEUS_VERSION}.linux-amd64.tar.gz"
    local temp_dir
    temp_dir=$(mktemp -d)

    log_info "Downloading Prometheus from ${download_url}"
    if ! execute_command "curl -L -o ${temp_dir}/prometheus.tar.gz ${download_url}"; then
        log_error "Failed to download Prometheus"
        rm -rf "${temp_dir}"
        exit 1
    fi

    # Extract
    log_info "Extracting Prometheus"
    execute_command "tar -xzf ${temp_dir}/prometheus.tar.gz -C ${temp_dir}"

    # Install binaries
    log_info "Installing Prometheus binaries"
    execute_command "cp ${temp_dir}/prometheus-${PROMETHEUS_VERSION}.linux-amd64/prometheus /usr/local/bin/"
    execute_command "cp ${temp_dir}/prometheus-${PROMETHEUS_VERSION}.linux-amd64/promtool /usr/local/bin/"
    execute_command "cp -r ${temp_dir}/prometheus-${PROMETHEUS_VERSION}.linux-amd64/consoles ${ETC_PROMETHEUS}/"
    execute_command "cp -r ${temp_dir}/prometheus-${PROMETHEUS_VERSION}.linux-amd64/console_libraries ${ETC_PROMETHEUS}/"

    # Set ownership
    execute_command "chown -R prometheus:prometheus ${ETC_PROMETHEUS}"
    execute_command "chown -R prometheus:prometheus ${VAR_LIB_PROMETHEUS}"
    execute_command "chown prometheus:prometheus /usr/local/bin/prometheus"
    execute_command "chown prometheus:prometheus /usr/local/bin/promtool"

    # Cleanup
    rm -rf "${temp_dir}"

    log_info "✓ Prometheus ${PROMETHEUS_VERSION} installed"
}

configure_prometheus() {
    log_step "Configuring Prometheus"

    # Generate prometheus.yml
    local prometheus_config="${ETC_PROMETHEUS}/prometheus.yml"

    log_info "Creating ${prometheus_config}"

    cat > "${prometheus_config}" <<EOF
# Prometheus Configuration - Context Engine Monitoring
# Generated by ${SCRIPT_NAME} v${SCRIPT_VERSION}
# Date: $(date '+%Y-%m-%d %H:%M:%S')

global:
  scrape_interval: 15s
  evaluation_interval: 15s
  external_labels:
    cluster: 'luris-production'
    service: 'context-engine'

# Alertmanager configuration
alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - 'localhost:${ALERTMANAGER_PORT}'

# Load alert rules
rule_files:
  - '/etc/prometheus/rules/*.yml'

# Scrape configurations
scrape_configs:
  # Context Engine Service
  - job_name: 'context-engine'
    static_configs:
      - targets: ['${CONTEXT_ENGINE_IP}:${CONTEXT_ENGINE_PORT}']
    scrape_interval: 15s
    scrape_timeout: 10s
    metrics_path: '/metrics'

  # GraphRAG Service
  - job_name: 'graphrag'
    static_configs:
      - targets: ['${CONTEXT_ENGINE_IP}:${GRAPHRAG_PORT}']
    scrape_interval: 15s
    metrics_path: '/metrics'

  # Prompt Service
  - job_name: 'prompt-service'
    static_configs:
      - targets: ['${CONTEXT_ENGINE_IP}:${PROMPT_SERVICE_PORT}']
    scrape_interval: 15s
    metrics_path: '/metrics'

  # Supabase Service
  - job_name: 'supabase'
    static_configs:
      - targets: ['${CONTEXT_ENGINE_IP}:${SUPABASE_PORT}']
    scrape_interval: 15s
    metrics_path: '/metrics'

  # Node Exporter (system metrics)
  - job_name: 'node'
    static_configs:
      - targets: ['localhost:${NODE_EXPORTER_PORT}']

  # Prometheus self-monitoring
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:${PROMETHEUS_PORT}']
EOF

    execute_command "chown prometheus:prometheus ${prometheus_config}"

    # Copy alert rules
    if [[ -f "${SCRIPT_DIR}/prometheus-alerts-context-engine.yml" ]]; then
        log_info "Installing Context Engine alert rules"
        execute_command "cp ${SCRIPT_DIR}/prometheus-alerts-context-engine.yml ${ETC_PROMETHEUS}/rules/"
        execute_command "chown prometheus:prometheus ${ETC_PROMETHEUS}/rules/prometheus-alerts-context-engine.yml"

        # Validate rules
        if command_exists promtool; then
            log_info "Validating alert rules"
            if promtool check rules "${ETC_PROMETHEUS}/rules/prometheus-alerts-context-engine.yml" >> "${DEPLOYMENT_LOG}" 2>&1; then
                log_info "✓ Alert rules validated successfully"
            else
                log_warn "Alert rule validation failed - check logs"
            fi
        fi
    else
        log_warn "Alert rules file not found at ${SCRIPT_DIR}/prometheus-alerts-context-engine.yml"
    fi

    # Validate configuration
    if command_exists promtool; then
        log_info "Validating Prometheus configuration"
        if promtool check config "${prometheus_config}" >> "${DEPLOYMENT_LOG}" 2>&1; then
            log_info "✓ Prometheus configuration validated"
        else
            log_error "Prometheus configuration validation failed"
            exit 1
        fi
    fi

    log_info "✓ Prometheus configured"
}

create_prometheus_service() {
    log_step "Creating Prometheus systemd service"

    local service_file="/etc/systemd/system/prometheus.service"

    log_info "Creating ${service_file}"

    cat > "${service_file}" <<EOF
[Unit]
Description=Prometheus Monitoring System
Documentation=https://prometheus.io/docs/introduction/overview/
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=prometheus
Group=prometheus
ExecStart=/usr/local/bin/prometheus \\
  --config.file=/etc/prometheus/prometheus.yml \\
  --storage.tsdb.path=/var/lib/prometheus/ \\
  --web.console.templates=/etc/prometheus/consoles \\
  --web.console.libraries=/etc/prometheus/console_libraries \\
  --storage.tsdb.retention.time=90d \\
  --storage.tsdb.retention.size=50GB \\
  --web.listen-address=0.0.0.0:${PROMETHEUS_PORT} \\
  --web.enable-lifecycle

ExecReload=/bin/kill -HUP \$MAINPID
Restart=always
RestartSec=5s

LimitNOFILE=65536
LimitNPROC=4096

[Install]
WantedBy=multi-user.target
EOF

    execute_command "systemctl daemon-reload"
    add_rollback_action "systemctl stop prometheus; systemctl disable prometheus; rm ${service_file}"

    log_info "✓ Prometheus service created"
}

start_prometheus() {
    log_step "Starting Prometheus service"

    execute_command "systemctl enable prometheus"
    execute_command "systemctl start prometheus"

    # Wait for service to be ready
    log_info "Waiting for Prometheus to be ready..."
    local max_wait=30
    local waited=0

    while [[ ${waited} -lt ${max_wait} ]]; do
        if curl -sf "http://localhost:${PROMETHEUS_PORT}/-/healthy" >/dev/null 2>&1; then
            log_info "✓ Prometheus is healthy"
            break
        fi
        sleep 1
        ((waited++))
    done

    if [[ ${waited} -ge ${max_wait} ]]; then
        log_error "Prometheus failed to start within ${max_wait} seconds"
        log_info "Check logs: journalctl -u prometheus -n 50"
        exit 1
    fi

    # Verify targets
    log_info "Checking Prometheus targets..."
    sleep 5  # Give time for first scrape

    local targets_up
    targets_up=$(curl -s "http://localhost:${PROMETHEUS_PORT}/api/v1/targets" | grep -c '"health":"up"' || true)
    log_info "Prometheus targets up: ${targets_up}"

    log_info "✓ Prometheus service started"
    log_info "  URL: http://localhost:${PROMETHEUS_PORT}"
}

###############################################################################
# Node Exporter Installation Functions
###############################################################################

install_node_exporter() {
    log_step "Installing Node Exporter ${NODE_EXPORTER_VERSION}"

    # Create node_exporter user
    if ! id -u node_exporter >/dev/null 2>&1; then
        log_info "Creating node_exporter user"
        execute_command "useradd --no-create-home --shell /bin/false node_exporter"
        add_rollback_action "userdel node_exporter"
    fi

    # Download Node Exporter
    local download_url="https://github.com/prometheus/node_exporter/releases/download/v${NODE_EXPORTER_VERSION}/node_exporter-${NODE_EXPORTER_VERSION}.linux-amd64.tar.gz"
    local temp_dir
    temp_dir=$(mktemp -d)

    log_info "Downloading Node Exporter from ${download_url}"
    execute_command "curl -L -o ${temp_dir}/node_exporter.tar.gz ${download_url}"

    # Extract
    log_info "Extracting Node Exporter"
    execute_command "tar -xzf ${temp_dir}/node_exporter.tar.gz -C ${temp_dir}"

    # Install binary
    log_info "Installing Node Exporter binary"
    execute_command "cp ${temp_dir}/node_exporter-${NODE_EXPORTER_VERSION}.linux-amd64/node_exporter /usr/local/bin/"
    execute_command "chown node_exporter:node_exporter /usr/local/bin/node_exporter"

    # Cleanup
    rm -rf "${temp_dir}"

    # Create systemd service
    local service_file="/etc/systemd/system/node_exporter.service"

    log_info "Creating Node Exporter systemd service"

    cat > "${service_file}" <<EOF
[Unit]
Description=Prometheus Node Exporter
Documentation=https://github.com/prometheus/node_exporter
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=node_exporter
Group=node_exporter
ExecStart=/usr/local/bin/node_exporter \\
  --web.listen-address=:${NODE_EXPORTER_PORT} \\
  --collector.filesystem.mount-points-exclude='^/(sys|proc|dev|host|etc)(\$|/)' \\
  --collector.netdev.device-exclude='^(veth.*|docker.*|br-.*)\$'

Restart=always
RestartSec=5s

[Install]
WantedBy=multi-user.target
EOF

    execute_command "systemctl daemon-reload"
    execute_command "systemctl enable node_exporter"
    execute_command "systemctl start node_exporter"

    # Verify
    sleep 2
    if curl -sf "http://localhost:${NODE_EXPORTER_PORT}/metrics" >/dev/null 2>&1; then
        log_info "✓ Node Exporter installed and running"
    else
        log_error "Node Exporter failed to start"
        exit 1
    fi
}

###############################################################################
# Grafana Installation Functions
###############################################################################

install_grafana() {
    log_step "Installing Grafana ${GRAFANA_VERSION}"

    # Add Grafana APT repository
    log_info "Adding Grafana APT repository"
    execute_command "apt-get update"
    execute_command "apt-get install -y apt-transport-https software-properties-common wget"

    # Add GPG key
    execute_command "wget -q -O /usr/share/keyrings/grafana.key https://apt.grafana.com/gpg.key"

    # Add repository
    echo "deb [signed-by=/usr/share/keyrings/grafana.key] https://apt.grafana.com stable main" | \
        tee /etc/apt/sources.list.d/grafana.list

    # Install Grafana
    execute_command "apt-get update"
    execute_command "apt-get install -y grafana"

    add_rollback_action "apt-get remove -y grafana"

    log_info "✓ Grafana installed"
}

configure_grafana() {
    log_step "Configuring Grafana"

    # Prompt for admin password if not set
    if [[ -z "${GRAFANA_ADMIN_PASSWORD}" ]]; then
        log_info "Grafana admin password not set"

        if [[ ${DRY_RUN} -eq 0 ]]; then
            read -r -s -p "Enter Grafana admin password: " GRAFANA_ADMIN_PASSWORD
            echo ""

            if [[ -z "${GRAFANA_ADMIN_PASSWORD}" ]]; then
                log_warn "No password provided, using default: admin"
                GRAFANA_ADMIN_PASSWORD="admin"
            fi
        else
            GRAFANA_ADMIN_PASSWORD="admin"
        fi
    fi

    # Configure grafana.ini
    local grafana_ini="${ETC_GRAFANA}/grafana.ini"

    log_info "Updating Grafana configuration"

    # Backup original config
    if [[ -f "${grafana_ini}" ]]; then
        execute_command "cp ${grafana_ini} ${grafana_ini}.backup"
    fi

    # Set admin password
    execute_command "grafana-cli admin reset-admin-password ${GRAFANA_ADMIN_PASSWORD}" || true

    # Create provisioning directories
    execute_command "mkdir -p ${ETC_GRAFANA}/provisioning/datasources"
    execute_command "mkdir -p ${ETC_GRAFANA}/provisioning/dashboards"

    # Provision Prometheus data source
    log_info "Provisioning Prometheus data source"

    cat > "${ETC_GRAFANA}/provisioning/datasources/prometheus.yml" <<EOF
# Prometheus Data Source - Auto-provisioned
# Generated by ${SCRIPT_NAME} v${SCRIPT_VERSION}

apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://localhost:${PROMETHEUS_PORT}
    isDefault: true
    editable: true
    jsonData:
      timeInterval: 15s
      httpMethod: POST
EOF

    # Provision dashboard provider
    log_info "Provisioning dashboard provider"

    cat > "${ETC_GRAFANA}/provisioning/dashboards/context-engine.yml" <<EOF
# Dashboard Provider - Context Engine
# Generated by ${SCRIPT_NAME} v${SCRIPT_VERSION}

apiVersion: 1

providers:
  - name: 'Context Engine'
    orgId: 1
    folder: 'Context Engine'
    type: file
    disableDeletion: false
    updateIntervalSeconds: 10
    allowUiUpdates: true
    options:
      path: /var/lib/grafana/dashboards
EOF

    # Create dashboard directory
    execute_command "mkdir -p ${VAR_LIB_GRAFANA}/dashboards"

    # Copy dashboard if available
    if [[ -f "${SCRIPT_DIR}/grafana-dashboard.json" ]]; then
        log_info "Installing Context Engine dashboard"
        execute_command "cp ${SCRIPT_DIR}/grafana-dashboard.json ${VAR_LIB_GRAFANA}/dashboards/"
        execute_command "chown -R grafana:grafana ${VAR_LIB_GRAFANA}/dashboards"
    else
        log_warn "Dashboard file not found at ${SCRIPT_DIR}/grafana-dashboard.json"
    fi

    # Set ownership
    execute_command "chown -R grafana:grafana ${ETC_GRAFANA}/provisioning"

    log_info "✓ Grafana configured"
}

start_grafana() {
    log_step "Starting Grafana service"

    execute_command "systemctl daemon-reload"
    execute_command "systemctl enable grafana-server"
    execute_command "systemctl start grafana-server"

    # Wait for Grafana to be ready
    log_info "Waiting for Grafana to be ready..."
    local max_wait=60
    local waited=0

    while [[ ${waited} -lt ${max_wait} ]]; do
        if curl -sf "http://localhost:${GRAFANA_PORT}/api/health" >/dev/null 2>&1; then
            log_info "✓ Grafana is healthy"
            break
        fi
        sleep 1
        ((waited++))
    done

    if [[ ${waited} -ge ${max_wait} ]]; then
        log_error "Grafana failed to start within ${max_wait} seconds"
        log_info "Check logs: journalctl -u grafana-server -n 50"
        exit 1
    fi

    log_info "✓ Grafana service started"
    log_info "  URL: http://localhost:${GRAFANA_PORT}"
    log_info "  Username: admin"
    log_info "  Password: ${GRAFANA_ADMIN_PASSWORD}"
}

###############################################################################
# Alertmanager Installation Functions
###############################################################################

install_alertmanager() {
    log_step "Installing Alertmanager ${ALERTMANAGER_VERSION}"

    # Create alertmanager user
    if ! id -u alertmanager >/dev/null 2>&1; then
        log_info "Creating alertmanager user"
        execute_command "useradd --no-create-home --shell /bin/false alertmanager"
        add_rollback_action "userdel alertmanager"
    fi

    # Create directories
    execute_command "mkdir -p ${ETC_ALERTMANAGER}"
    execute_command "mkdir -p ${VAR_LIB_ALERTMANAGER}"

    # Download Alertmanager
    local download_url="https://github.com/prometheus/alertmanager/releases/download/v${ALERTMANAGER_VERSION}/alertmanager-${ALERTMANAGER_VERSION}.linux-amd64.tar.gz"
    local temp_dir
    temp_dir=$(mktemp -d)

    log_info "Downloading Alertmanager from ${download_url}"
    execute_command "curl -L -o ${temp_dir}/alertmanager.tar.gz ${download_url}"

    # Extract
    log_info "Extracting Alertmanager"
    execute_command "tar -xzf ${temp_dir}/alertmanager.tar.gz -C ${temp_dir}"

    # Install binaries
    log_info "Installing Alertmanager binaries"
    execute_command "cp ${temp_dir}/alertmanager-${ALERTMANAGER_VERSION}.linux-amd64/alertmanager /usr/local/bin/"
    execute_command "cp ${temp_dir}/alertmanager-${ALERTMANAGER_VERSION}.linux-amd64/amtool /usr/local/bin/"

    # Set ownership
    execute_command "chown alertmanager:alertmanager /usr/local/bin/alertmanager"
    execute_command "chown alertmanager:alertmanager /usr/local/bin/amtool"
    execute_command "chown -R alertmanager:alertmanager ${ETC_ALERTMANAGER}"
    execute_command "chown -R alertmanager:alertmanager ${VAR_LIB_ALERTMANAGER}"

    # Cleanup
    rm -rf "${temp_dir}"

    log_info "✓ Alertmanager ${ALERTMANAGER_VERSION} installed"
}

configure_alertmanager() {
    log_step "Configuring Alertmanager"

    local alertmanager_config="${ETC_ALERTMANAGER}/alertmanager.yml"

    # Get notification settings from environment
    local slack_webhook="${ALERTMANAGER_SLACK_WEBHOOK:-}"
    local pagerduty_key="${ALERTMANAGER_PAGERDUTY_KEY:-}"
    local smtp_host="${SMTP_HOST:-smtp.gmail.com}"
    local smtp_port="${SMTP_PORT:-587}"
    local smtp_user="${SMTP_USER:-}"
    local smtp_password="${SMTP_PASSWORD:-}"

    log_info "Creating ${alertmanager_config}"

    cat > "${alertmanager_config}" <<EOF
# Alertmanager Configuration - Context Engine Monitoring
# Generated by ${SCRIPT_NAME} v${SCRIPT_VERSION}
# Date: $(date '+%Y-%m-%d %H:%M:%S')

global:
  resolve_timeout: 5m
EOF

    # Add SMTP config if provided
    if [[ -n "${smtp_user}" ]] && [[ -n "${smtp_password}" ]]; then
        cat >> "${alertmanager_config}" <<EOF
  smtp_smarthost: '${smtp_host}:${smtp_port}'
  smtp_from: 'alerts@luris.ai'
  smtp_auth_username: '${smtp_user}'
  smtp_auth_password: '${smtp_password}'
  smtp_require_tls: true
EOF
    fi

    cat >> "${alertmanager_config}" <<EOF

# Route tree
route:
  group_by: ['alertname', 'service', 'severity']
  group_wait: 10s
  group_interval: 5m
  repeat_interval: 4h
  receiver: 'default'

  routes:
    # Critical alerts -> PagerDuty
    - match:
        severity: critical
      receiver: 'pagerduty-critical'
      continue: false

    # Warning alerts -> Slack
    - match:
        severity: warning
      receiver: 'slack-warnings'
      continue: false

    # Info alerts -> Email
    - match:
        severity: info
      receiver: 'email-info'
      continue: false

# Receivers
receivers:
  - name: 'default'
    # Fallback receiver - logs only

EOF

    # Add PagerDuty receiver if key provided
    if [[ -n "${pagerduty_key}" ]]; then
        cat >> "${alertmanager_config}" <<EOF
  - name: 'pagerduty-critical'
    pagerduty_configs:
      - service_key: '${pagerduty_key}'
        severity: 'critical'
        description: '{{ .CommonAnnotations.summary }}'
        details:
          firing: '{{ .Alerts.Firing | len }}'
          resolved: '{{ .Alerts.Resolved | len }}'

EOF
    else
        cat >> "${alertmanager_config}" <<EOF
  - name: 'pagerduty-critical'
    # PagerDuty not configured - set ALERTMANAGER_PAGERDUTY_KEY environment variable

EOF
    fi

    # Add Slack receiver if webhook provided
    if [[ -n "${slack_webhook}" ]]; then
        cat >> "${alertmanager_config}" <<EOF
  - name: 'slack-warnings'
    slack_configs:
      - api_url: '${slack_webhook}'
        channel: '#luris-alerts'
        username: 'Alertmanager'
        icon_emoji: ':warning:'
        title: 'Context Engine Alert'
        text: '{{ range .Alerts }}{{ .Annotations.summary }}\n{{ end }}'

EOF
    else
        cat >> "${alertmanager_config}" <<EOF
  - name: 'slack-warnings'
    # Slack not configured - set ALERTMANAGER_SLACK_WEBHOOK environment variable

EOF
    fi

    # Add email receiver if SMTP configured
    if [[ -n "${smtp_user}" ]] && [[ -n "${smtp_password}" ]]; then
        cat >> "${alertmanager_config}" <<EOF
  - name: 'email-info'
    email_configs:
      - to: 'devops@yourcompany.com'
        headers:
          Subject: '[Luris Alert] {{ .CommonLabels.alertname }}'

EOF
    else
        cat >> "${alertmanager_config}" <<EOF
  - name: 'email-info'
    # Email not configured - set SMTP_* environment variables

EOF
    fi

    # Inhibit rules
    cat >> "${alertmanager_config}" <<EOF
# Inhibition rules
inhibit_rules:
  - source_match:
      severity: 'critical'
    target_match:
      severity: 'warning'
    equal: ['alertname', 'service']
EOF

    execute_command "chown alertmanager:alertmanager ${alertmanager_config}"

    # Validate configuration
    if command_exists amtool; then
        log_info "Validating Alertmanager configuration"
        if amtool check-config "${alertmanager_config}" >> "${DEPLOYMENT_LOG}" 2>&1; then
            log_info "✓ Alertmanager configuration validated"
        else
            log_error "Alertmanager configuration validation failed"
            exit 1
        fi
    fi

    log_info "✓ Alertmanager configured"
}

create_alertmanager_service() {
    log_step "Creating Alertmanager systemd service"

    local service_file="/etc/systemd/system/alertmanager.service"

    log_info "Creating ${service_file}"

    cat > "${service_file}" <<EOF
[Unit]
Description=Prometheus Alertmanager
Documentation=https://prometheus.io/docs/alerting/latest/alertmanager/
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=alertmanager
Group=alertmanager
ExecStart=/usr/local/bin/alertmanager \\
  --config.file=/etc/alertmanager/alertmanager.yml \\
  --storage.path=/var/lib/alertmanager/ \\
  --web.listen-address=0.0.0.0:${ALERTMANAGER_PORT} \\
  --cluster.listen-address=

Restart=always
RestartSec=5s

[Install]
WantedBy=multi-user.target
EOF

    execute_command "systemctl daemon-reload"
    execute_command "systemctl enable alertmanager"
    execute_command "systemctl start alertmanager"

    # Verify
    sleep 2
    if curl -sf "http://localhost:${ALERTMANAGER_PORT}/-/healthy" >/dev/null 2>&1; then
        log_info "✓ Alertmanager service started"
        log_info "  URL: http://localhost:${ALERTMANAGER_PORT}"
    else
        log_error "Alertmanager failed to start"
        exit 1
    fi
}

###############################################################################
# Monitoring Stack Target
###############################################################################

create_monitoring_target() {
    log_step "Creating luris-monitoring.target"

    local target_file="/etc/systemd/system/luris-monitoring.target"

    cat > "${target_file}" <<EOF
[Unit]
Description=Luris Monitoring Stack
Wants=prometheus.service grafana-server.service alertmanager.service node_exporter.service
After=network-online.target

[Install]
WantedBy=multi-user.target
EOF

    execute_command "systemctl daemon-reload"
    execute_command "systemctl enable luris-monitoring.target"

    log_info "✓ Monitoring target created"
    log_info "  Start all: systemctl start luris-monitoring.target"
    log_info "  Stop all: systemctl stop luris-monitoring.target"
}

###############################################################################
# Verification Functions
###############################################################################

verify_prometheus() {
    log_info "Verifying Prometheus..."

    # Check service
    if ! systemctl is-active --quiet prometheus; then
        log_error "Prometheus service not running"
        return 1
    fi

    # Check health
    if ! curl -sf "http://localhost:${PROMETHEUS_PORT}/-/healthy" >/dev/null 2>&1; then
        log_error "Prometheus health check failed"
        return 1
    fi

    # Check targets
    local targets_response
    targets_response=$(curl -s "http://localhost:${PROMETHEUS_PORT}/api/v1/targets")
    local targets_up
    targets_up=$(echo "${targets_response}" | grep -c '"health":"up"' || true)

    log_info "  Service: ✓ Running"
    log_info "  Health: ✓ Healthy"
    log_info "  Targets up: ${targets_up}"

    return 0
}

verify_grafana() {
    log_info "Verifying Grafana..."

    # Check service
    if ! systemctl is-active --quiet grafana-server; then
        log_error "Grafana service not running"
        return 1
    fi

    # Check health
    if ! curl -sf "http://localhost:${GRAFANA_PORT}/api/health" >/dev/null 2>&1; then
        log_error "Grafana health check failed"
        return 1
    fi

    log_info "  Service: ✓ Running"
    log_info "  Health: ✓ Healthy"

    return 0
}

verify_alertmanager() {
    log_info "Verifying Alertmanager..."

    # Check service
    if ! systemctl is-active --quiet alertmanager; then
        log_error "Alertmanager service not running"
        return 1
    fi

    # Check health
    if ! curl -sf "http://localhost:${ALERTMANAGER_PORT}/-/healthy" >/dev/null 2>&1; then
        log_error "Alertmanager health check failed"
        return 1
    fi

    log_info "  Service: ✓ Running"
    log_info "  Health: ✓ Healthy"

    return 0
}

verify_node_exporter() {
    log_info "Verifying Node Exporter..."

    # Check service
    if ! systemctl is-active --quiet node_exporter; then
        log_error "Node Exporter service not running"
        return 1
    fi

    # Check metrics
    if ! curl -sf "http://localhost:${NODE_EXPORTER_PORT}/metrics" >/dev/null 2>&1; then
        log_error "Node Exporter metrics not available"
        return 1
    fi

    log_info "  Service: ✓ Running"
    log_info "  Metrics: ✓ Available"

    return 0
}

###############################################################################
# Uninstall Functions
###############################################################################

uninstall_monitoring() {
    log_step "Uninstalling monitoring stack"

    if ! prompt_user "Are you sure you want to uninstall the monitoring stack?"; then
        log_info "Uninstall cancelled"
        exit 0
    fi

    # Stop services
    log_info "Stopping services..."
    systemctl stop prometheus grafana-server alertmanager node_exporter 2>/dev/null || true
    systemctl disable prometheus grafana-server alertmanager node_exporter 2>/dev/null || true

    # Remove systemd units
    log_info "Removing systemd units..."
    rm -f /etc/systemd/system/prometheus.service
    rm -f /etc/systemd/system/alertmanager.service
    rm -f /etc/systemd/system/node_exporter.service
    rm -f /etc/systemd/system/luris-monitoring.target
    systemctl daemon-reload

    # Backup data if requested
    if prompt_user "Backup data before removal?"; then
        local backup_dir="/backup/monitoring-$(date +%Y%m%d-%H%M%S)"
        mkdir -p "${backup_dir}"

        log_info "Backing up to ${backup_dir}..."
        cp -r "${ETC_PROMETHEUS}" "${backup_dir}/" 2>/dev/null || true
        cp -r "${ETC_ALERTMANAGER}" "${backup_dir}/" 2>/dev/null || true
        cp -r "${VAR_LIB_PROMETHEUS}" "${backup_dir}/" 2>/dev/null || true
        cp -r "${VAR_LIB_ALERTMANAGER}" "${backup_dir}/" 2>/dev/null || true

        log_info "✓ Backup saved to ${backup_dir}"
    fi

    # Remove binaries
    if prompt_user "Remove installed binaries?"; then
        log_info "Removing binaries..."
        rm -f /usr/local/bin/prometheus /usr/local/bin/promtool
        rm -f /usr/local/bin/alertmanager /usr/local/bin/amtool
        rm -f /usr/local/bin/node_exporter
    fi

    # Remove configuration
    if prompt_user "Remove configuration files?"; then
        log_info "Removing configuration..."
        rm -rf "${ETC_PROMETHEUS}"
        rm -rf "${ETC_ALERTMANAGER}"
    fi

    # Remove data
    if prompt_user "Remove data directories? (WARNING: This deletes all metrics data)"; then
        log_info "Removing data..."
        rm -rf "${VAR_LIB_PROMETHEUS}"
        rm -rf "${VAR_LIB_ALERTMANAGER}"
    fi

    # Remove Grafana
    if prompt_user "Remove Grafana?"; then
        log_info "Removing Grafana..."
        apt-get remove -y grafana 2>/dev/null || true
        rm -rf "${ETC_GRAFANA}"
        rm -rf "${VAR_LIB_GRAFANA}"
    fi

    # Remove users
    log_info "Removing system users..."
    userdel prometheus 2>/dev/null || true
    userdel alertmanager 2>/dev/null || true
    userdel node_exporter 2>/dev/null || true

    log_info "✓ Uninstall completed"
}

###############################################################################
# Summary Report
###############################################################################

print_summary() {
    local server_ip
    server_ip=$(hostname -I | awk '{print $1}')

    echo ""
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}  Monitoring Stack Deployment Summary${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    echo -e "${BLUE}Services Installed:${NC}"

    if [[ "${COMPONENT}" == "all" ]] || [[ "${COMPONENT}" == "prometheus" ]]; then
        echo -e "  ${GREEN}✓${NC} Prometheus ${PROMETHEUS_VERSION}"
        echo -e "    URL: http://${server_ip}:${PROMETHEUS_PORT}"
        echo -e "    Status: $(systemctl is-active prometheus)"
    fi

    if [[ "${COMPONENT}" == "all" ]] || [[ "${COMPONENT}" == "grafana" ]]; then
        echo -e "  ${GREEN}✓${NC} Grafana ${GRAFANA_VERSION}"
        echo -e "    URL: http://${server_ip}:${GRAFANA_PORT}"
        echo -e "    Username: admin"
        echo -e "    Password: ${GRAFANA_ADMIN_PASSWORD}"
        echo -e "    Status: $(systemctl is-active grafana-server)"
    fi

    if [[ "${COMPONENT}" == "all" ]] || [[ "${COMPONENT}" == "alertmanager" ]]; then
        echo -e "  ${GREEN}✓${NC} Alertmanager ${ALERTMANAGER_VERSION}"
        echo -e "    URL: http://${server_ip}:${ALERTMANAGER_PORT}"
        echo -e "    Status: $(systemctl is-active alertmanager)"
    fi

    if [[ "${COMPONENT}" == "all" ]]; then
        echo -e "  ${GREEN}✓${NC} Node Exporter ${NODE_EXPORTER_VERSION}"
        echo -e "    URL: http://${server_ip}:${NODE_EXPORTER_PORT}/metrics"
        echo -e "    Status: $(systemctl is-active node_exporter)"
    fi

    echo ""
    echo -e "${BLUE}Next Steps:${NC}"
    echo "  1. Verify all services are running:"
    echo "     systemctl status prometheus grafana-server alertmanager"
    echo ""
    echo "  2. Access Grafana dashboard:"
    echo "     http://${server_ip}:${GRAFANA_PORT}"
    echo ""
    echo "  3. Check Prometheus targets:"
    echo "     http://${server_ip}:${PROMETHEUS_PORT}/targets"
    echo ""
    echo "  4. View logs:"
    echo "     journalctl -u prometheus -f"
    echo "     journalctl -u grafana-server -f"
    echo "     journalctl -u alertmanager -f"
    echo ""
    echo "  5. Manage all services:"
    echo "     systemctl start luris-monitoring.target"
    echo "     systemctl stop luris-monitoring.target"
    echo ""
    echo -e "${BLUE}Documentation:${NC}"
    echo "  Grafana Setup: ${SCRIPT_DIR}/GRAFANA_SETUP.md"
    echo "  Alert Rules: ${ETC_PROMETHEUS}/rules/prometheus-alerts-context-engine.yml"
    echo "  Deployment Log: ${DEPLOYMENT_LOG}"
    echo ""
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

###############################################################################
# Main Function
###############################################################################

main() {
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --dry-run)
                DRY_RUN=1
                log_info "Dry run mode enabled"
                shift
                ;;
            --verbose)
                VERBOSE=1
                log_info "Verbose mode enabled"
                shift
                ;;
            --component=*)
                COMPONENT="${1#*=}"
                if [[ ! "${COMPONENT}" =~ ^(all|prometheus|grafana|alertmanager)$ ]]; then
                    log_error "Invalid component: ${COMPONENT}"
                    log_info "Valid components: all, prometheus, grafana, alertmanager"
                    exit 1
                fi
                shift
                ;;
            --uninstall)
                UNINSTALL=1
                shift
                ;;
            --help)
                cat <<EOF
Usage: ${SCRIPT_NAME} [OPTIONS]

Automated deployment of monitoring stack for Context Engine Service.

OPTIONS:
  --component=COMPONENT    Component to install (all|prometheus|grafana|alertmanager)
  --dry-run               Show what would be done without making changes
  --verbose               Enable verbose output
  --uninstall             Uninstall monitoring stack
  --help                  Show this help message

ENVIRONMENT VARIABLES:
  PROMETHEUS_VERSION       Prometheus version (default: ${PROMETHEUS_VERSION})
  GRAFANA_ADMIN_PASSWORD   Grafana admin password (prompted if not set)
  ALERTMANAGER_SLACK_WEBHOOK   Slack webhook URL for notifications
  ALERTMANAGER_PAGERDUTY_KEY   PagerDuty integration key
  SMTP_HOST               SMTP server host (default: smtp.gmail.com)
  SMTP_PORT               SMTP server port (default: 587)
  SMTP_USER               SMTP username
  SMTP_PASSWORD           SMTP password

EXAMPLES:
  # Install all components
  sudo ${SCRIPT_NAME} --component=all

  # Install only Prometheus
  sudo ${SCRIPT_NAME} --component=prometheus

  # Dry run (show what would be done)
  sudo ${SCRIPT_NAME} --dry-run --component=all

  # Uninstall everything
  sudo ${SCRIPT_NAME} --uninstall

  # Verbose output
  sudo ${SCRIPT_NAME} --verbose --component=grafana

EOF
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                log_info "Use --help for usage information"
                exit 1
                ;;
        esac
    done

    # Create log directory
    mkdir -p "${LOG_DIR}"

    # Print banner
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}  Context Engine - Monitoring Stack Deployment${NC}"
    echo -e "${BLUE}  Version: ${SCRIPT_VERSION}${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    # Handle uninstall
    if [[ ${UNINSTALL} -eq 1 ]]; then
        uninstall_monitoring
        exit 0
    fi

    # Prerequisites
    check_root
    check_ubuntu_version
    check_systemd
    check_network
    check_disk_space
    check_ports

    # Set up error handling
    trap 'execute_rollback' ERR

    # Install components
    if [[ "${COMPONENT}" == "all" ]] || [[ "${COMPONENT}" == "prometheus" ]]; then
        install_prometheus
        configure_prometheus
        create_prometheus_service
        install_node_exporter
        start_prometheus
        verify_prometheus
    fi

    if [[ "${COMPONENT}" == "all" ]] || [[ "${COMPONENT}" == "grafana" ]]; then
        install_grafana
        configure_grafana
        start_grafana
        verify_grafana
    fi

    if [[ "${COMPONENT}" == "all" ]] || [[ "${COMPONENT}" == "alertmanager" ]]; then
        install_alertmanager
        configure_alertmanager
        create_alertmanager_service
        verify_alertmanager
    fi

    # Create monitoring target
    if [[ "${COMPONENT}" == "all" ]]; then
        create_monitoring_target
    fi

    # Final verification
    log_step "Final Verification"

    local all_ok=1

    if [[ "${COMPONENT}" == "all" ]] || [[ "${COMPONENT}" == "prometheus" ]]; then
        verify_prometheus || all_ok=0
    fi

    if [[ "${COMPONENT}" == "all" ]] || [[ "${COMPONENT}" == "grafana" ]]; then
        verify_grafana || all_ok=0
    fi

    if [[ "${COMPONENT}" == "all" ]] || [[ "${COMPONENT}" == "alertmanager" ]]; then
        verify_alertmanager || all_ok=0
    fi

    if [[ "${COMPONENT}" == "all" ]]; then
        verify_node_exporter || all_ok=0
    fi

    if [[ ${all_ok} -eq 1 ]]; then
        log_info "✓ All verification checks passed"
    else
        log_warn "Some verification checks failed - review logs"
    fi

    # Print summary
    print_summary

    log_info "Deployment completed successfully!"
    log_info "Deployment log: ${DEPLOYMENT_LOG}"
}

###############################################################################
# Script Entry Point
###############################################################################

main "$@"
