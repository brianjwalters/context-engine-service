# Context Engine Service - Monitoring & Metrics Guide

**Version:** 1.0.0
**Port:** 8015
**Metrics Endpoint:** `/metrics`

---

## Overview

The Context Engine Service provides comprehensive observability through:
- **Prometheus metrics** for request tracking and performance
- **Health check endpoints** for service status
- **Structured logging** via journald/syslog
- **Cache statistics** for performance monitoring

---

## Table of Contents

- [Prometheus Metrics](#prometheus-metrics)
- [Health Check Endpoints](#health-check-endpoints)
- [Cache Performance Monitoring](#cache-performance-monitoring)
- [Grafana Dashboards](#grafana-dashboards)
- [Alerting Rules](#alerting-rules)
- [Log Monitoring](#log-monitoring)
- [Performance Baselines](#performance-baselines)

---

## Prometheus Metrics

### Metrics Endpoint

**URL:** `http://localhost:8015/metrics`

**Example scrape configuration** (`prometheus.yml`):

```yaml
scrape_configs:
  - job_name: 'context-engine'
    static_configs:
      - targets: ['localhost:8015']
    metrics_path: '/metrics'
    scrape_interval: 15s
```

### Available Metrics

#### 1. Request Counter

**Metric:** `context_engine_requests_total`
**Type:** Counter
**Labels:** `endpoint`, `method`
**Description:** Total number of HTTP requests received

**Example queries:**

```promql
# Total requests
sum(context_engine_requests_total)

# Requests per endpoint
sum by (endpoint) (context_engine_requests_total)

# Request rate (requests/second)
rate(context_engine_requests_total[5m])

# Top endpoints by request count
topk(10, sum by (endpoint) (context_engine_requests_total))
```

#### 2. Request Latency

**Metric:** `context_engine_request_latency_seconds`
**Type:** Histogram
**Labels:** `endpoint`
**Description:** HTTP request latency in seconds

**Buckets:** 0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0

**Example queries:**

```promql
# P95 latency for all endpoints
histogram_quantile(0.95, sum by (le, endpoint) (
  rate(context_engine_request_latency_seconds_bucket[5m])
))

# P99 latency
histogram_quantile(0.99, sum by (le) (
  rate(context_engine_request_latency_seconds_bucket[5m])
))

# Average latency
avg(rate(context_engine_request_latency_seconds_sum[5m]) /
    rate(context_engine_request_latency_seconds_count[5m]))

# Latency SLA compliance (% requests < 2s)
sum(rate(context_engine_request_latency_seconds_bucket{le="2.0"}[5m])) /
sum(rate(context_engine_request_latency_seconds_count[5m]))
```

#### 3. Cache Metrics (Custom)

While not built-in Prometheus metrics, the `/api/v1/cache/stats` endpoint provides:

```json
{
  "memory_hits": 1523,
  "memory_misses": 347,
  "memory_hit_rate": 0.8145,
  "overall_hit_rate": 0.8145,
  "memory_cache": {
    "size": 847,
    "max_size": 1000,
    "utilization": 0.847
  }
}
```

**To export as Prometheus metrics** (future enhancement):
Use custom exporter or prometheus_client in Python to expose these as gauges.

---

## Health Check Endpoints

### 1. Basic Health Check

**Endpoint:** `GET /api/v1/health`
**Response Time:** <10ms
**Use:** Liveness probe (Kubernetes/systemd)

```bash
curl http://localhost:8015/api/v1/health
```

**Expected Response:**
```json
{
  "status": "healthy",
  "service": "context-engine",
  "port": 8015,
  "version": "1.0.0"
}
```

**Monitoring configuration:**

```yaml
# Docker healthcheck
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8015/api/v1/health"]
  interval: 30s
  timeout: 5s
  retries: 3
  start_period: 10s
```

### 2. Cache Health Check

**Endpoint:** `GET /api/v1/cache/health`
**Response Time:** <50ms
**Use:** Cache system status

```bash
curl http://localhost:8015/api/v1/cache/health
```

**Expected Response:**
```json
{
  "status": "healthy",
  "tiers": {
    "memory": {
      "status": "healthy",
      "utilization": 0.847,
      "hit_rate": 0.8145
    },
    "redis": {"status": "disabled"},
    "database": {"status": "disabled"}
  },
  "overall_hit_rate": 0.8145
}
```

**Alert Conditions:**
- `status != "healthy"` → Critical alert
- `overall_hit_rate < 0.5` → Warning (cache degraded)
- `memory.utilization > 0.95` → Warning (cache near full)

### 3. Root Endpoint

**Endpoint:** `GET /`
**Response Time:** <10ms
**Use:** Service discovery

```bash
curl http://localhost:8015/
```

**Expected Response:**
```json
{
  "service": "context-engine-service",
  "version": "1.0.0",
  "port": 8015,
  "status": "running",
  "description": "Case-centric context retrieval using WHO/WHAT/WHERE/WHEN/WHY framework",
  "endpoints": {
    "docs": "/docs",
    "redoc": "/redoc",
    "health": "/api/v1/health",
    "metrics": "/metrics"
  }
}
```

---

## Cache Performance Monitoring

### Cache Statistics Endpoint

**Endpoint:** `GET /api/v1/cache/stats`

```bash
curl http://localhost:8015/api/v1/cache/stats | jq
```

**Response:**
```json
{
  "memory_hits": 1523,
  "memory_misses": 347,
  "memory_hit_rate": 0.8145,
  "redis_hits": 0,
  "redis_misses": 0,
  "redis_hit_rate": 0.0,
  "db_hits": 0,
  "db_misses": 0,
  "db_hit_rate": 0.0,
  "total_sets": 449,
  "total_deletes": 23,
  "overall_hit_rate": 0.8145,
  "memory_cache": {
    "size": 847,
    "max_size": 1000,
    "utilization": 0.847,
    "total_hits": 1523,
    "expired_entries": 12,
    "default_ttl_seconds": 600
  }
}
```

### Key Metrics to Monitor

| Metric | Target | Alert Threshold |
|--------|--------|-----------------|
| **memory_hit_rate** | >70% | <50% |
| **overall_hit_rate** | >70% | <50% |
| **memory_cache.utilization** | 60-90% | >95% |
| **expired_entries** | <10% of size | >20% |

### Cache Performance Dashboard Queries

**Hit rate over time:**
```bash
# Poll cache stats every 30 seconds
watch -n 30 'curl -s http://localhost:8015/api/v1/cache/stats | jq ".memory_hit_rate"'
```

**Cache utilization:**
```bash
# Monitor cache fullness
watch -n 30 'curl -s http://localhost:8015/api/v1/cache/stats | jq ".memory_cache.utilization"'
```

---

## Grafana Dashboards

### Dashboard Configuration

**File:** `grafana-dashboard.json` (see below)

**Import Instructions:**
1. Open Grafana → Dashboards → Import
2. Upload `grafana-dashboard.json`
3. Select Prometheus data source
4. Click Import

### Key Panels

#### Panel 1: Request Rate
- **Metric:** `rate(context_engine_requests_total[5m])`
- **Type:** Graph
- **Y-axis:** Requests/second
- **Alert:** >100 req/s sustained

#### Panel 2: P95 Latency
- **Metric:** `histogram_quantile(0.95, rate(context_engine_request_latency_seconds_bucket[5m]))`
- **Type:** Graph
- **Y-axis:** Seconds
- **Target:** <2.0s
- **Alert:** >3.0s sustained

#### Panel 3: Error Rate
- **Metric:** `sum(rate(context_engine_requests_total{status=~"5.."}[5m]))`
- **Type:** Graph
- **Y-axis:** Errors/second
- **Alert:** >1% of total requests

#### Panel 4: Top Endpoints
- **Metric:** `topk(10, sum by (endpoint) (rate(context_engine_requests_total[5m])))`
- **Type:** Table
- **Columns:** Endpoint, Requests/sec

---

## Alerting Rules

### Prometheus Alert Rules

**File:** `prometheus-alerts.yml`

```yaml
groups:
  - name: context_engine_alerts
    interval: 30s
    rules:
      # High latency alert
      - alert: ContextEngineHighLatency
        expr: >
          histogram_quantile(0.95,
            rate(context_engine_request_latency_seconds_bucket[5m])
          ) > 3.0
        for: 5m
        labels:
          severity: warning
          service: context-engine
        annotations:
          summary: "Context Engine high latency detected"
          description: "P95 latency is {{ $value }}s (threshold: 3s)"

      # Service down alert
      - alert: ContextEngineDown
        expr: up{job="context-engine"} == 0
        for: 1m
        labels:
          severity: critical
          service: context-engine
        annotations:
          summary: "Context Engine service is down"
          description: "Context Engine has been down for 1 minute"

      # High error rate alert
      - alert: ContextEngineHighErrorRate
        expr: >
          sum(rate(context_engine_requests_total{status=~"5.."}[5m])) /
          sum(rate(context_engine_requests_total[5m])) > 0.05
        for: 5m
        labels:
          severity: warning
          service: context-engine
        annotations:
          summary: "Context Engine error rate >5%"
          description: "Error rate is {{ $value | humanizePercentage }}"

      # Memory usage alert (systemd)
      - alert: ContextEngineHighMemory
        expr: >
          process_resident_memory_bytes{job="context-engine"} > 2e9
        for: 5m
        labels:
          severity: warning
          service: context-engine
        annotations:
          summary: "Context Engine high memory usage"
          description: "Memory usage is {{ $value | humanize1024 }} (threshold: 2GB)"
```

### Alert Notification Channels

**Recommended integrations:**
- Slack webhook for team notifications
- PagerDuty for critical alerts
- Email for warning alerts
- Grafana OnCall for on-call rotation

---

## Log Monitoring

### Structured Logging

Logs are written to systemd journald with structured format:

```bash
# View logs with formatting
sudo journalctl -u luris-context-engine -o json-pretty

# Filter by log level
sudo journalctl -u luris-context-engine -p err  # Errors only
sudo journalctl -u luris-context-engine -p warning  # Warnings and above
```

### Log Patterns to Monitor

#### 1. Error Patterns

```bash
# Count errors in last hour
sudo journalctl -u luris-context-engine --since "1 hour ago" -p err | wc -l

# Find most common errors
sudo journalctl -u luris-context-engine --since "1 day ago" -p err | \
  grep -oP '"message": "\K[^"]+' | sort | uniq -c | sort -rn | head -10
```

#### 2. Performance Patterns

```bash
# Find slow requests (>2s)
sudo journalctl -u luris-context-engine --since "1 hour ago" | \
  grep "execution_time_ms" | awk '$NF > 2000'

# Cache miss patterns
sudo journalctl -u luris-context-engine --since "1 hour ago" | \
  grep "cache miss" | wc -l
```

#### 3. Dependency Health

```bash
# GraphRAG connection errors
sudo journalctl -u luris-context-engine --since "1 hour ago" | \
  grep -i "graphrag.*error"

# Supabase connection errors
sudo journalctl -u luris-context-engine --since "1 hour ago" | \
  grep -i "supabase.*error"
```

### Log Aggregation (ELK Stack)

**Filebeat configuration** for shipping logs to Elasticsearch:

```yaml
filebeat.inputs:
  - type: journald
    id: context-engine-logs
    include_matches:
      - _SYSTEMD_UNIT=luris-context-engine.service

processors:
  - add_fields:
      target: service
      fields:
        name: context-engine
        port: 8015
        environment: production

output.elasticsearch:
  hosts: ["localhost:9200"]
  index: "context-engine-%{+yyyy.MM.dd}"
```

---

## Performance Baselines

### Expected Performance Characteristics

| Metric | Minimal Scope | Standard Scope | Comprehensive Scope |
|--------|--------------|----------------|-------------------|
| **Latency (cache hit)** | <10ms | <10ms | <10ms |
| **Latency (cache miss)** | 50-150ms | 100-500ms | 500-2000ms |
| **Throughput** | 200 req/s | 100 req/s | 50 req/s |
| **Cache hit rate** | 70-80% | 70-80% | 70-80% |
| **Memory usage** | 500MB-1GB | 1GB-2GB | 1GB-2GB |
| **CPU usage** | 50-100% | 100-150% | 150-200% |

### Capacity Planning

**Current capacity (single instance):**
- **Concurrent requests:** 50
- **Daily requests:** ~1M (at 70% cache hit)
- **Peak throughput:** 100 req/s
- **Memory headroom:** 2GB configured, ~1.5GB typical

**Scaling thresholds:**
- Add instance at: 80 req/s sustained for 15min
- Scale out at: 90% memory utilization
- Consider Redis at: >10M daily requests

---

## Monitoring Checklist

### Daily Checks
- [ ] Service health status: `curl http://localhost:8015/api/v1/health`
- [ ] Cache hit rate: `curl http://localhost:8015/api/v1/cache/stats | jq .memory_hit_rate`
- [ ] Error count: `sudo journalctl -u luris-context-engine --since "1 day ago" -p err | wc -l`

### Weekly Checks
- [ ] Review Grafana dashboards for trends
- [ ] Check cache utilization trends
- [ ] Review slow query logs (>2s latency)
- [ ] Verify alerting rules are firing correctly

### Monthly Checks
- [ ] Review capacity planning metrics
- [ ] Update performance baselines
- [ ] Audit log retention policies
- [ ] Test alert notification channels

---

## Troubleshooting Guide

### High Latency Investigation

1. **Check cache hit rate:**
   ```bash
   curl http://localhost:8015/api/v1/cache/stats | jq .memory_hit_rate
   ```
   - If <50%: Consider cache warmup or increasing cache size

2. **Check GraphRAG latency:**
   ```bash
   curl -w "\nTime: %{time_total}s\n" http://10.10.0.87:8010/api/v1/health
   ```
   - If >1s: GraphRAG service needs optimization

3. **Check database latency:**
   ```bash
   psql -h localhost -U postgres -c "EXPLAIN ANALYZE SELECT * FROM client.entities LIMIT 10;"
   ```
   - Review query plans for slow queries

### High Error Rate Investigation

1. **Identify error types:**
   ```bash
   sudo journalctl -u luris-context-engine --since "1 hour ago" -p err | \
     grep -oP '"error_type": "\K[^"]+' | sort | uniq -c | sort -rn
   ```

2. **Check dependency health:**
   ```bash
   # GraphRAG
   curl http://10.10.0.87:8010/api/v1/health

   # Supabase
   psql -h localhost -U postgres -c "SELECT 1;"
   ```

3. **Review recent deployments:**
   ```bash
   # Check recent git commits
   git log --oneline -10

   # Check service restart history
   sudo journalctl -u luris-context-engine --since "1 day ago" | grep "Started\|Stopped"
   ```

---

**Last Updated**: 2025-01-22
**Maintained by**: Context Engine Development Team
