# Grafana Dashboard Setup Guide
## Context Engine Service - Production Monitoring

This guide provides comprehensive instructions for importing and configuring the Context Engine Service Grafana dashboard in production environments.

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Dashboard Import](#2-dashboard-import)
3. [Data Source Configuration](#3-data-source-configuration)
4. [Alert Configuration](#4-alert-configuration)
5. [Panel Customization](#5-panel-customization)
6. [Variables & Templating](#6-variables--templating)
7. [Troubleshooting](#7-troubleshooting)
8. [Maintenance](#8-maintenance)
9. [Advanced Features](#9-advanced-features)
10. [Quick Start](#10-quick-start)

---

## 1. Prerequisites

### Required Software Versions

- **Grafana**: 9.0.0 or higher (tested with 9.5.0)
- **Prometheus**: 2.30.0 or higher
- **Context Engine Service**: Must be instrumented with Prometheus metrics
- **Network Access**: Grafana must be able to reach Prometheus data source

### Required Permissions

- **Grafana Admin** or **Editor** role to import dashboards
- **Prometheus Data Source** access with read permissions
- **Alert Manager** access (optional, for alert notifications)

### Prometheus Metrics Availability

Verify that the Context Engine service is exposing metrics:

```bash
# Test metrics endpoint
curl http://10.10.0.87:8015/metrics

# Expected output should include:
# - context_engine_requests_total
# - context_engine_request_latency_seconds_bucket
# - context_engine_cache_hits_total
# - context_engine_dependency_health
# - process_cpu_seconds_total
# - process_resident_memory_bytes
```

### Prometheus Scrape Configuration

Ensure Prometheus is configured to scrape the Context Engine service:

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'context-engine'
    static_configs:
      - targets: ['10.10.0.87:8015']
    scrape_interval: 15s
    scrape_timeout: 10s
    metrics_path: '/metrics'
```

**Recommended Scrape Interval**: 15 seconds for production monitoring

---

## 2. Dashboard Import

### Method 1: Import via JSON File (Recommended)

**Step 1**: Access Grafana UI
- Navigate to your Grafana instance: `https://grafana.yourdomain.com`
- Log in with Admin or Editor credentials

**Step 2**: Navigate to Import Page
- Click the **"+"** icon in the left sidebar
- Select **"Import"** from the dropdown menu
- Or navigate directly to: `/dashboard/import`

**Step 3**: Upload JSON File
- Click **"Upload JSON file"** button
- Select the file: `/srv/luris/be/context-engine-service/monitoring/grafana-dashboard.json`
- Alternatively, copy-paste the entire JSON content into the text area

**Step 4**: Configure Import Settings
- **Name**: "Context Engine Service - Production Monitoring" (pre-filled)
- **Folder**: Select appropriate folder (e.g., "Luris Services" or "Production")
- **UID**: `context-engine-prod` (pre-filled, ensures unique dashboard ID)
- **Data Source**: Select your Prometheus data source from dropdown

**Step 5**: Complete Import
- Click **"Import"** button
- Dashboard will load automatically
- Verify all panels are displaying data

### Method 2: Import via Grafana.com (Future)

Once published to Grafana.com:

```bash
# Import by dashboard ID
Dashboard ID: [To be assigned after publication]

# Or via API
curl -X POST http://grafana:3000/api/dashboards/import \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <API_KEY>" \
  -d @grafana-dashboard.json
```

### Method 3: Automated Import via API

For infrastructure-as-code deployments:

```bash
# Set variables
GRAFANA_URL="http://grafana:3000"
API_KEY="your-grafana-api-key"
DASHBOARD_JSON="/srv/luris/be/context-engine-service/monitoring/grafana-dashboard.json"

# Import dashboard
curl -X POST "${GRAFANA_URL}/api/dashboards/db" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${API_KEY}" \
  -d @"${DASHBOARD_JSON}"

# Verify import
curl -X GET "${GRAFANA_URL}/api/dashboards/uid/context-engine-prod" \
  -H "Authorization: Bearer ${API_KEY}"
```

### Verification After Import

**Check 1**: All Panels Load Data
- Verify that all 29 panels display metrics (not "No data")
- If panels show "No data", check Prometheus data source connection

**Check 2**: Template Variables Work
- Click the **"Data Source"** dropdown at the top
- Verify Prometheus is selected
- Click **"Environment"** dropdown
- Verify production/staging/development options appear

**Check 3**: Time Range Selector
- Default range should be **"Last 6 hours"**
- Verify you can change to 1h, 3h, 12h, 24h, 7d

**Check 4**: Auto-Refresh
- Dashboard should auto-refresh every **30 seconds**
- Verify refresh dropdown shows 30s selected

---

## 3. Data Source Configuration

### Prometheus Data Source Setup

**Step 1**: Navigate to Data Sources
- Go to **Configuration** → **Data Sources**
- Click **"Add data source"**
- Select **"Prometheus"**

**Step 2**: Configure Connection
```yaml
Name: Prometheus
Default: ✓ (check if primary data source)
URL: http://prometheus:9090
  # Or internal IP: http://10.10.0.87:9090
  # Adjust to your Prometheus instance
Access: Server (default)
  # Use "Browser" only for development/testing
```

**Step 3**: Authentication (if required)
```yaml
# For basic auth
Basic Auth: ✓
User: prometheus-user
Password: [your-password]

# For custom headers (optional)
Custom HTTP Headers:
  - Header: Authorization
    Value: Bearer <token>
```

**Step 4**: Advanced Settings
```yaml
Scrape interval: 15s
  # Must match your Prometheus configuration

Query timeout: 60s
  # Increase for complex queries

HTTP Method: POST
  # Recommended for long queries
```

**Step 5**: Test & Save
- Click **"Save & Test"**
- Expected response: **"Data source is working"**
- If test fails, check network connectivity and Prometheus URL

### Multiple Data Source Support

The dashboard supports multiple Prometheus instances via the `$datasource` variable:

```yaml
# Production Prometheus
Name: Prometheus-Prod
URL: http://prometheus-prod:9090

# Staging Prometheus
Name: Prometheus-Staging
URL: http://prometheus-staging:9090

# Development Prometheus
Name: Prometheus-Dev
URL: http://prometheus-dev:9090
```

Users can switch between data sources using the dropdown at the top of the dashboard.

---

## 4. Alert Configuration

### Linking Prometheus Alerts to Grafana

The dashboard includes visual indicators for active alerts. To enable:

**Step 1**: Configure Alertmanager in Grafana

Navigate to **Alerting** → **Alerting** → **Alert Rules**

**Step 2**: Add Prometheus Alert Rules

Import the Context Engine alert rules:

```bash
# Copy alert rules to Prometheus
sudo cp /srv/luris/be/context-engine-service/monitoring/prometheus-alerts-context-engine.yml \
  /etc/prometheus/rules/context-engine.yml

# Update prometheus.yml
rule_files:
  - '/etc/prometheus/rules/context-engine.yml'

# Reload Prometheus
sudo systemctl reload prometheus

# Verify rules loaded
curl http://prometheus:9090/api/v1/rules | jq '.data.groups[].name'
```

**Step 3**: Configure Notification Channels

#### Slack Notifications

```yaml
# Grafana UI: Alerting → Contact points → New contact point
Name: luris-slack-alerts
Type: Slack
Webhook URL: https://hooks.slack.com/services/YOUR/WEBHOOK/URL
Channel: #luris-alerts
Username: Grafana
Icon Emoji: :grafana:
```

#### PagerDuty Notifications

```yaml
Name: luris-pagerduty-critical
Type: PagerDuty
Integration Key: [Your PagerDuty integration key]
Severity: critical
Auto resolve: ✓
```

#### Email Notifications

```yaml
Name: luris-email-alerts
Type: Email
Addresses: devops@yourcompany.com, oncall@yourcompany.com
Subject: [Luris Alert] Context Engine - {{ .RuleName }}
```

**Step 4**: Create Notification Policies

```yaml
# Navigate to: Alerting → Notification policies

# Policy 1: Critical Alerts
Label matchers:
  - severity = critical
Contact point: luris-pagerduty-critical
Group by: [alertname, service]
Group wait: 10s
Group interval: 5m
Repeat interval: 4h

# Policy 2: Warning Alerts
Label matchers:
  - severity = warning
Contact point: luris-slack-alerts
Group by: [alertname, service]
Group wait: 30s
Group interval: 5m
Repeat interval: 12h

# Policy 3: Info Alerts
Label matchers:
  - severity = info
Contact point: luris-email-alerts
Group by: [alertname]
Group wait: 1m
Group interval: 15m
Repeat interval: 24h
```

### Alert Routing Rules

Configure routing based on alert severity and component:

```yaml
# High priority: Service down, dependencies failed
routes:
  - match:
      component: availability
    receiver: pagerduty-critical
    continue: true

  - match:
      component: dependencies
      severity: critical
    receiver: pagerduty-critical
    continue: true

  - match:
      severity: warning
    receiver: slack-alerts
    continue: false

  - match:
      severity: info
    receiver: email-alerts
    continue: false
```

### Testing Alerts

**Test 1**: Simulate Service Down
```bash
# Stop Context Engine service
sudo systemctl stop luris-context-engine

# Wait 1 minute (alert threshold)
# Check PagerDuty for alert

# Restart service
sudo systemctl start luris-context-engine
```

**Test 2**: Simulate High Latency
```bash
# Use load testing tool to create slow requests
# Alert should trigger after 5 minutes
```

**Test 3**: Test Notification Channels
```yaml
# Grafana UI: Alerting → Contact points
# Click "Test" button for each contact point
# Verify notifications received
```

---

## 5. Panel Customization

### Modifying Panel Queries

**Step 1**: Enter Edit Mode
- Click panel title
- Select **"Edit"** from dropdown
- Or click the panel and press `e`

**Step 2**: Modify Prometheus Query
```promql
# Example: Change request rate time window
# Original:
sum(rate(context_engine_requests_total[5m]))

# Modified for 1-minute rate:
sum(rate(context_engine_requests_total[1m]))

# Add dimension filter:
sum(rate(context_engine_requests_total{dimension="who"}[5m]))

# Add environment filter:
sum(rate(context_engine_requests_total{environment="$environment"}[5m]))
```

**Step 3**: Adjust Visualization Settings
```yaml
# For time series panels:
Legend: Table (shows min/max/avg)
Tooltip: All series
Graph styles: Lines, Bars, Points
Fill opacity: 10 (default)
Line width: 2 (default)

# For gauge panels:
Show threshold markers: ✓
Show threshold labels: ✓
Orientation: Auto

# For stat panels:
Graph mode: Area
Color mode: Background
Text mode: Value and name
```

**Step 4**: Save Changes
- Click **"Apply"** to save panel changes
- Click **"Save dashboard"** (disk icon) to persist

### Adjusting Thresholds

**Example: CPU Usage Panel**

Current thresholds:
```yaml
Green: 0% - 120%
Yellow: 120% - 160%
Orange: 160% - 180%
Red: 180%+
```

To modify:
1. Edit panel
2. Navigate to **"Thresholds"** in right sidebar
3. Click threshold value to edit
4. Add/remove thresholds as needed
5. Click **"Apply"**

**Example: Error Rate Panel**

```yaml
# Original thresholds (percentage)
Green: 0% - 1%
Yellow: 1% - 5%
Red: 5%+

# Stricter thresholds for SLA compliance
Green: 0% - 0.5%
Yellow: 0.5% - 1%
Orange: 1% - 2%
Red: 2%+
```

### Adding Custom Panels

**Step 1**: Add New Panel
- Click **"Add panel"** button (top right)
- Select **"Add a new panel"**

**Step 2**: Configure Query
```promql
# Example: Add dimension-specific latency panel
histogram_quantile(0.95,
  sum by (le, dimension) (
    rate(context_engine_request_latency_seconds_bucket{dimension="who"}[5m])
  )
)
```

**Step 3**: Configure Visualization
- Panel type: Time series
- Title: "WHO Dimension P95 Latency"
- Unit: seconds (s)
- Legend: Show, placement bottom

**Step 4**: Position Panel
- Drag panel to desired location
- Resize using corner handles
- Typical sizes:
  - Full width: w=24
  - Half width: w=12
  - Quarter width: w=6
  - Height: h=6 to h=12

---

## 6. Variables & Templating

### Using the `$datasource` Variable

The dashboard includes a pre-configured data source variable:

```yaml
Name: datasource
Type: Data source
Query: prometheus
Multi-value: No
Include All: No
```

**Usage in Panels**:
All panels automatically reference `${datasource}` for the data source.

### Using the `$environment` Variable

Switch between production/staging/development:

```yaml
Name: environment
Type: Custom
Values: production,staging,development
Current: production
```

**To filter queries by environment**:
```promql
# Before (queries all environments)
sum(rate(context_engine_requests_total[5m]))

# After (queries specific environment)
sum(rate(context_engine_requests_total{environment="$environment"}[5m]))
```

**Note**: Requires environment label on Prometheus metrics.

### Using the `$service` Variable (Hidden)

Pre-configured to filter for context-engine:

```yaml
Name: service
Type: Custom
Values: context-engine
Hide: Yes (hidden from UI)
```

### Adding Custom Variables

**Example: Add Client ID Filter**

**Step 1**: Open Dashboard Settings
- Click gear icon (⚙️) in top right
- Select **"Variables"**

**Step 2**: Add New Variable
```yaml
Name: client_id
Type: Query
Label: Client ID
Data source: ${datasource}
Query: label_values(context_engine_requests_total, client_id)
Multi-value: Yes
Include All option: Yes
Refresh: On Dashboard Load
Sort: Alphabetical (asc)
```

**Step 3**: Use in Panel Queries
```promql
sum(rate(context_engine_requests_total{client_id=~"$client_id"}[5m]))
```

**Example: Add Dimension Filter**

```yaml
Name: dimension
Type: Custom
Values: who,what,where,when,why
Multi-value: Yes
Include All option: Yes
```

**Usage**:
```promql
sum by (dimension) (
  rate(context_engine_requests_total{dimension=~"$dimension"}[5m])
)
```

---

## 7. Troubleshooting

### Common Import Errors

#### Error: "Dashboard JSON is invalid"

**Cause**: JSON syntax error or corrupted file

**Solution**:
```bash
# Validate JSON syntax
jq . /srv/luris/be/context-engine-service/monitoring/grafana-dashboard.json

# If validation fails, re-download or recreate file
```

#### Error: "Data source not found"

**Cause**: Dashboard references data source that doesn't exist

**Solution**:
1. Import dashboard without data source
2. Edit dashboard settings
3. Update `${datasource}` variable to use existing Prometheus data source

#### Error: "UID already exists"

**Cause**: Dashboard with UID `context-engine-prod` already imported

**Solution**:
```yaml
Option 1: Delete existing dashboard
  - Navigate to existing dashboard
  - Click settings (⚙️) → Delete Dashboard

Option 2: Change UID during import
  - Modify UID field during import
  - Use: context-engine-prod-v2
```

### Data Source Connection Issues

#### Symptom: "No data" on all panels

**Check 1**: Verify Prometheus is running
```bash
curl http://prometheus:9090/-/healthy
# Expected: Prometheus is Healthy
```

**Check 2**: Verify Prometheus has data
```bash
curl 'http://prometheus:9090/api/v1/query?query=up{job="context-engine"}'
# Expected: "value":[timestamp,"1"]
```

**Check 3**: Check Grafana data source
```bash
# In Grafana UI
Configuration → Data Sources → Prometheus → Test
# Expected: "Data source is working"
```

**Check 4**: Network connectivity
```bash
# From Grafana container/host
curl http://prometheus:9090/api/v1/label/__name__/values | jq
# Should return list of metrics
```

#### Symptom: "Server error" on specific panels

**Cause**: Query timeout or invalid query

**Solution**:
1. Edit panel
2. Check query syntax
3. Reduce query time range
4. Increase data source timeout:
   - Configuration → Data Sources → Prometheus
   - Query timeout: 120s

### Missing Metrics Debugging

#### Check if Context Engine is exposing metrics

```bash
# Test metrics endpoint
curl http://10.10.0.87:8015/metrics | grep context_engine

# Expected metrics:
# context_engine_requests_total
# context_engine_request_latency_seconds_bucket
# context_engine_cache_hits_total
# context_engine_dependency_health
```

#### Verify Prometheus is scraping

```bash
# Check Prometheus targets
curl http://prometheus:9090/api/v1/targets | jq '.data.activeTargets[] | select(.labels.job=="context-engine")'

# Expected:
# "health": "up"
# "lastScrape": "2025-10-23T..."
```

#### Common missing metrics and solutions

| Metric Missing | Cause | Solution |
|----------------|-------|----------|
| `context_engine_requests_total` | Service not running | `sudo systemctl start luris-context-engine` |
| `context_engine_cache_*` | Cache not initialized | Send requests to warm up cache |
| `context_engine_dependency_health` | Dependency checks disabled | Enable health checks in service config |
| `process_cpu_seconds_total` | Prometheus client not configured | Check service instrumentation |

### Query Performance Optimization

#### Symptom: Dashboard slow to load

**Optimization 1**: Reduce scrape interval
```yaml
# prometheus.yml
scrape_interval: 30s  # Instead of 15s
```

**Optimization 2**: Use recording rules
```yaml
# prometheus-rules.yml
groups:
  - name: context_engine_aggregations
    interval: 30s
    rules:
      - record: context_engine:request_rate:5m
        expr: sum(rate(context_engine_requests_total[5m]))

      - record: context_engine:error_rate:5m
        expr: sum(rate(context_engine_requests_total{status=~"5.."}[5m])) / sum(rate(context_engine_requests_total[5m]))
```

**Optimization 3**: Reduce query time ranges
```promql
# Before (slow)
sum(rate(context_engine_requests_total[1h]))

# After (faster)
sum(rate(context_engine_requests_total[5m]))
```

**Optimization 4**: Limit panel refresh
- Edit panel
- Panel options → Query options
- Relative time: Override to "Last 1 hour"
- Min interval: 30s

---

## 8. Maintenance

### Dashboard Versioning

**Enable Version History**:
1. Dashboard settings (⚙️) → Versions
2. All saves are automatically versioned
3. Compare versions and restore previous versions

**Best Practices**:
```yaml
Version naming convention:
  - v1.0 - Initial production release
  - v1.1 - Added test quality panels
  - v1.2 - Adjusted CPU threshold
  - v2.0 - Major redesign

Change notes:
  - Always add description when saving
  - Tag versions: "production", "testing", "rollback"
```

### Backup and Restore

#### Manual Backup

**Export via UI**:
1. Open dashboard
2. Click share icon (📤)
3. Select **"Export"** tab
4. Click **"Save to file"**
5. Store in version control

**Export via API**:
```bash
# Export dashboard
curl -H "Authorization: Bearer ${API_KEY}" \
  http://grafana:3000/api/dashboards/uid/context-engine-prod \
  | jq . > context-engine-backup-$(date +%Y%m%d).json

# Backup all dashboards
curl -H "Authorization: Bearer ${API_KEY}" \
  http://grafana:3000/api/search?type=dash-db \
  | jq -r '.[].uid' \
  | while read uid; do
      curl -H "Authorization: Bearer ${API_KEY}" \
        "http://grafana:3000/api/dashboards/uid/${uid}" \
        > "backup-${uid}-$(date +%Y%m%d).json"
    done
```

#### Automated Backup

**Cron job for daily backups**:
```bash
# /etc/cron.daily/grafana-backup
#!/bin/bash
BACKUP_DIR="/backup/grafana/dashboards"
DATE=$(date +%Y%m%d)

mkdir -p "${BACKUP_DIR}"

curl -H "Authorization: Bearer ${API_KEY}" \
  http://grafana:3000/api/dashboards/uid/context-engine-prod \
  | jq . > "${BACKUP_DIR}/context-engine-${DATE}.json"

# Retain 30 days
find "${BACKUP_DIR}" -name "context-engine-*.json" -mtime +30 -delete
```

#### Restore Dashboard

**Restore via UI**:
1. Navigate to **Dashboards** → **Import**
2. Upload backup JSON file
3. Change UID to avoid conflicts
4. Click **"Import"**

**Restore via API**:
```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${API_KEY}" \
  -d @context-engine-backup-20251023.json \
  http://grafana:3000/api/dashboards/db
```

### Performance Optimization Tips

#### Reduce Dashboard Load Time

1. **Limit panel queries**:
   - Use `$__interval` variable for dynamic aggregation
   - Example: `rate(metric[$__interval])`

2. **Use query caching**:
   ```yaml
   # Data source settings
   Cache timeout: 60  # Cache for 60 seconds
   ```

3. **Optimize legend display**:
   ```yaml
   # Instead of showing all series
   Legend: Hide
   # Or limit to top 10
   topk(10, sum by (label) (metric))
   ```

4. **Reduce dashboard refresh rate**:
   - Change from 30s to 1m for non-critical dashboards

#### Database Cleanup

**Remove old dashboard versions**:
```sql
-- PostgreSQL (Grafana database)
DELETE FROM dashboard_version
WHERE created < NOW() - INTERVAL '90 days';
```

**Compact Prometheus data**:
```bash
# Prometheus data retention (prometheus.yml)
storage:
  tsdb:
    retention.time: 90d  # Keep 90 days
    retention.size: 500GB  # Or size limit
```

---

## 9. Advanced Features

### Creating Custom Panels

#### Example: Add SLA Compliance Panel

**Step 1**: Add new panel

**Step 2**: Configure query
```promql
# SLA target: 99.9% uptime, P95 < 2s
(
  sum(rate(context_engine_requests_total{status!~"5.."}[30d]))
  /
  sum(rate(context_engine_requests_total[30d]))
) * 100
```

**Step 3**: Configure visualization
```yaml
Panel type: Stat
Unit: Percent (0-100)
Thresholds:
  - Red: 0 - 99.0
  - Yellow: 99.0 - 99.9
  - Green: 99.9 - 100
```

### Setting Up Annotations

**Annotation 1: Deployment Events**

```yaml
# Dashboard settings → Annotations → New annotation
Name: Deployments
Data source: Prometheus
Query: ALERTS{alertname="DeploymentEvent"}
Tags to parse: version, environment
Icon color: Blue
```

**Annotation 2: Alert Firing Events**

```yaml
Name: Alert Firing
Data source: Prometheus
Query: ALERTS{job="context-engine",alertstate="firing"}
Tags to parse: alertname, severity
Icon color: Red
```

**Annotation 3: Manual Annotations**

```yaml
# Add via UI
1. Click on graph
2. Select "Add annotation"
3. Enter text
4. Tags: maintenance, incident, deployment
```

### Linking to External Systems

#### Link to Service Logs (Loki)

```yaml
# Panel → Panel options → Links
Title: View Logs
URL: /explore?left=["now-1h","now","Loki",{"expr":"{job=\"context-engine\"}"}]
Open in new tab: ✓
```

#### Link to Prometheus Alert Rules

```yaml
Title: Alert Rules
URL: http://prometheus:9090/alerts?search=context_engine
```

#### Link to Runbook

```yaml
Title: Runbook
URL: https://docs.luris.ai/runbooks/context-engine
```

### Exporting Data

#### Export Panel as CSV

1. Click panel title
2. Select **"Inspect"** → **"Data"**
3. Click **"Download CSV"**

#### Export via API

```bash
# Query Prometheus directly
curl -G http://prometheus:9090/api/v1/query_range \
  --data-urlencode 'query=sum(rate(context_engine_requests_total[5m]))' \
  --data-urlencode 'start=2025-10-23T00:00:00Z' \
  --data-urlencode 'end=2025-10-23T23:59:59Z' \
  --data-urlencode 'step=15s' \
  | jq -r '.data.result[0].values[] | @csv' \
  > context_engine_metrics.csv
```

---

## 10. Quick Start

### One-Command Dashboard Import

For rapid deployment in new environments:

```bash
#!/bin/bash
# quick-import.sh

# Configuration
GRAFANA_URL="${GRAFANA_URL:-http://grafana:3000}"
GRAFANA_API_KEY="${GRAFANA_API_KEY:-}"
DASHBOARD_FILE="/srv/luris/be/context-engine-service/monitoring/grafana-dashboard.json"

# Validate
if [ -z "${GRAFANA_API_KEY}" ]; then
  echo "Error: GRAFANA_API_KEY not set"
  exit 1
fi

if [ ! -f "${DASHBOARD_FILE}" ]; then
  echo "Error: Dashboard file not found: ${DASHBOARD_FILE}"
  exit 1
fi

# Import dashboard
echo "Importing Context Engine dashboard..."
response=$(curl -s -X POST \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${GRAFANA_API_KEY}" \
  -d @"${DASHBOARD_FILE}" \
  "${GRAFANA_URL}/api/dashboards/db")

# Check result
if echo "${response}" | jq -e '.status == "success"' > /dev/null; then
  dashboard_url=$(echo "${response}" | jq -r '.url')
  echo "✅ Dashboard imported successfully!"
  echo "🔗 URL: ${GRAFANA_URL}${dashboard_url}"
else
  echo "❌ Import failed:"
  echo "${response}" | jq
  exit 1
fi
```

**Usage**:
```bash
export GRAFANA_API_KEY="your-api-key"
export GRAFANA_URL="http://grafana:3000"
bash quick-import.sh
```

### Minimal Configuration for Testing

**For local development/testing**:

1. **Start Prometheus** (minimal config):
```yaml
# prometheus-minimal.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'context-engine'
    static_configs:
      - targets: ['localhost:8015']
```

2. **Start Grafana** (Docker):
```bash
docker run -d \
  --name=grafana \
  -p 3000:3000 \
  -e "GF_SECURITY_ADMIN_PASSWORD=admin" \
  grafana/grafana:latest
```

3. **Import dashboard**:
```bash
# Default credentials: admin/admin
# Navigate to http://localhost:3000
# Import dashboard JSON via UI
```

### Production Deployment Checklist

Complete this checklist before deploying to production:

**Pre-Deployment**:
- [ ] Grafana 9.0+ installed and accessible
- [ ] Prometheus data source configured and tested
- [ ] Context Engine service exposing metrics on port 8015
- [ ] Prometheus scraping Context Engine (verify targets)
- [ ] Dashboard JSON file validated (`jq . grafana-dashboard.json`)
- [ ] Alert rules deployed to Prometheus
- [ ] Notification channels configured (Slack, PagerDuty, Email)

**Import**:
- [ ] Dashboard imported via JSON file
- [ ] All 29 panels loading data (no "No data" errors)
- [ ] Template variables working (datasource, environment)
- [ ] Time range selector functional
- [ ] Auto-refresh enabled (30s)
- [ ] Dashboard saved to appropriate folder

**Post-Deployment**:
- [ ] Test all panels for data accuracy
- [ ] Verify thresholds match SLA requirements
- [ ] Test alert notifications (trigger test alert)
- [ ] Verify links to external systems (logs, runbooks)
- [ ] Create initial backup of dashboard
- [ ] Document dashboard URL for team
- [ ] Add dashboard to monitoring runbook
- [ ] Schedule regular dashboard review (monthly)

**Security**:
- [ ] Restrict dashboard edit permissions (Editor role required)
- [ ] Enable audit logging for dashboard changes
- [ ] Rotate Grafana API keys quarterly
- [ ] Review data source permissions
- [ ] Verify Prometheus metrics don't expose sensitive data

---

## Appendix A: Dashboard Panel Reference

### Complete Panel Inventory (29 Panels)

| Panel ID | Title | Type | Row | Purpose |
|----------|-------|------|-----|---------|
| 1 | Service Status | Stat | Health Overview | UP/DOWN indicator |
| 2 | Request Rate | Time Series | Health Overview | Requests/sec (1m, 5m, 15m) |
| 3 | Error Rate % | Gauge | Health Overview | Error percentage (5m) |
| 4 | Active Connections | Time Series | Health Overview | Current active connections |
| 5 | Response Status Distribution | Pie Chart | Health Overview | Status code breakdown |
| 6 | Request Latency Percentiles | Time Series | Performance | P50/P95/P99 latency |
| 7 | Throughput by Dimension | Time Series | Performance | WHO/WHAT/WHERE/WHEN/WHY |
| 8 | Response Time Distribution | Heatmap | Performance | Latency heatmap |
| 9 | WHO Dimension | Time Series | Dimensions | WHO requests + success rate |
| 10 | WHAT Dimension | Time Series | Dimensions | WHAT requests + success rate |
| 11 | WHERE Dimension | Time Series | Dimensions | WHERE requests + success rate |
| 12 | WHEN Dimension | Time Series | Dimensions | WHEN requests + success rate |
| 13 | WHY Dimension | Time Series | Dimensions | WHY requests + success rate |
| 14 | Cache Hit Rate % | Gauge | Cache | Cache hit percentage |
| 15 | Cache Size | Time Series | Cache | Current cache entries |
| 16 | Cache Eviction Rate | Time Series | Cache | Evictions per second |
| 17 | Cache Miss Latency | Time Series | Cache | P95 miss latency |
| 18 | GraphRAG Service | Stat | Dependencies | GraphRAG health status |
| 19 | Prompt Service | Stat | Dependencies | Prompt service health |
| 20 | Supabase Database | Stat | Dependencies | Supabase health status |
| 21 | Dependency Error Rates | Time Series | Dependencies | Errors by dependency |
| 22 | CPU Usage % | Gauge | Resources | CPU utilization |
| 23 | Memory Usage | Gauge | Resources | Memory usage (2GB limit) |
| 24 | Network I/O | Time Series | Resources | Network bytes sent/received |
| 25 | Disk I/O | Time Series | Resources | Disk read/write ops |
| 26 | Test Pass Rate % | Gauge | Test Quality | Current test pass rate |
| 27 | Test Coverage % | Time Series | Test Quality | Code coverage over time |
| 28 | Dimension Test Quality | Time Series | Test Quality | Quality scores by dimension |
| 29 | Test Execution Time | Time Series | Test Quality | Test run duration |

---

## Appendix B: Prometheus Metrics Reference

### Core Metrics Used by Dashboard

#### Request Metrics
```promql
context_engine_requests_total{dimension, status, endpoint}
  # Counter: Total requests by dimension and status
  # Labels: dimension (who/what/where/when/why), status (200/500/etc)

context_engine_request_latency_seconds_bucket{le, endpoint}
  # Histogram: Request latency distribution
  # Used for: P50, P95, P99 calculations
```

#### Cache Metrics
```promql
context_engine_cache_hits_total
  # Counter: Cache hits

context_engine_cache_requests_total
  # Counter: Total cache requests

context_engine_cache_size_entries
  # Gauge: Current cache size

context_engine_cache_evictions_total
  # Counter: Cache evictions

context_engine_cache_miss_latency_seconds_bucket{le}
  # Histogram: Cache miss latency
```

#### Dependency Metrics
```promql
context_engine_dependency_health{dependency}
  # Gauge: Dependency health (0=down, 1=up)
  # Labels: dependency (graphrag, prompt-service, supabase)

context_engine_dependency_errors_total{dependency}
  # Counter: Errors per dependency
```

#### System Metrics
```promql
process_cpu_seconds_total{job="context-engine"}
  # Counter: CPU time consumed

process_resident_memory_bytes{job="context-engine"}
  # Gauge: Memory usage in bytes

up{job="context-engine"}
  # Gauge: Service up/down (0=down, 1=up)
```

#### Quality Metrics
```promql
context_engine_test_pass_rate
  # Gauge: Test pass rate (0.0-1.0)

context_engine_test_coverage
  # Gauge: Code coverage (0.0-1.0)

context_engine_dimension_test_quality{dimension}
  # Gauge: Quality score per dimension

context_engine_test_execution_time_seconds
  # Gauge: Test run duration
```

---

## Appendix C: Troubleshooting Decision Tree

```
Dashboard not loading?
├── Check Grafana is running
│   └── systemctl status grafana-server
├── Check browser console for errors
│   └── F12 → Console tab
└── Check Grafana logs
    └── journalctl -u grafana-server -f

All panels show "No data"?
├── Check Prometheus data source
│   ├── Configuration → Data Sources → Test
│   └── Expected: "Data source is working"
├── Check Prometheus is running
│   └── curl http://prometheus:9090/-/healthy
└── Check Prometheus has metrics
    └── curl 'http://prometheus:9090/api/v1/query?query=up{job="context-engine"}'

Some panels show "No data"?
├── Check Context Engine is running
│   └── systemctl status luris-context-engine
├── Check metrics endpoint
│   └── curl http://10.10.0.87:8015/metrics
└── Check Prometheus scraping
    └── http://prometheus:9090/targets

Alerts not triggering?
├── Check alert rules loaded
│   └── curl http://prometheus:9090/api/v1/rules
├── Check Alertmanager running
│   └── systemctl status alertmanager
└── Test notification channels
    └── Grafana UI → Alerting → Contact points → Test

Dashboard slow to load?
├── Reduce query time ranges
│   └── Edit panels: [5m] instead of [1h]
├── Enable query caching
│   └── Data source → Cache timeout: 60s
└── Use recording rules
    └── See § Query Performance Optimization
```

---

## Support & Resources

### Internal Documentation
- **Context Engine API**: `/srv/luris/be/context-engine-service/api.md`
- **Prometheus Alerts**: `/srv/luris/be/context-engine-service/monitoring/prometheus-alerts-context-engine.yml`
- **Service README**: `/srv/luris/be/context-engine-service/README.md`

### External Resources
- **Grafana Documentation**: https://grafana.com/docs/grafana/latest/
- **Prometheus Querying**: https://prometheus.io/docs/prometheus/latest/querying/basics/
- **PromQL Cheat Sheet**: https://promlabs.com/promql-cheat-sheet/

### Getting Help
- **Slack Channel**: #luris-monitoring
- **On-Call Engineer**: PagerDuty rotation
- **DevOps Team**: devops@yourcompany.com

---

**Document Version**: 1.0
**Last Updated**: 2025-10-23
**Author**: Documentation Engineer (Claude)
**Review Cycle**: Quarterly
