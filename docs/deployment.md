# Context Engine Service - Deployment Guide

**Version:** 1.0.0
**Port:** 8015
**Service Name:** luris-context-engine

---

## Table of Contents

- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Service Management](#service-management)
- [Monitoring](#monitoring)
- [Troubleshooting](#troubleshooting)
- [Rollback Procedures](#rollback-procedures)

---

## Prerequisites

### System Requirements

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| **OS** | Ubuntu 20.04+ | Ubuntu 22.04 LTS |
| **Python** | 3.11+ | 3.12+ |
| **CPU** | 2 cores | 4 cores |
| **RAM** | 2GB | 4GB |
| **Disk** | 5GB | 10GB |
| **Network** | 10Mbps | 100Mbps |

### Required Services

| Service | Status | Port | Purpose |
|---------|--------|------|---------|
| **GraphRAG Service** | REQUIRED | 8010 | Knowledge graph queries |
| **Supabase/PostgreSQL** | REQUIRED | 5432/54321 | Database access |
| **vLLM Services** | OPTIONAL | 8080, 8082 | Via GraphRAG |
| **Redis** | OPTIONAL | 6379 | Tier 2 caching (future) |

### Dependency Services Check

```bash
# Check GraphRAG service
curl -s http://10.10.0.87:8010/api/v1/health || echo "GraphRAG not available"

# Check Supabase
psql -h localhost -U postgres -c "SELECT version();" || echo "Supabase not available"
```

---

## Installation

### Step 1: Clone Repository

```bash
# Navigate to Luris backend directory
cd /srv/luris/be

# Clone repository (if not already present)
git clone https://github.com/brianjwalters/context-engine-service.git
cd context-engine-service
```

### Step 2: Create Virtual Environment

```bash
# Create venv (IMPORTANT: Only if it doesn't exist!)
python3 -m venv venv

# Activate venv
source venv/bin/activate

# Verify activation
which python  # Should show: /srv/luris/be/context-engine-service/venv/bin/python
```

### Step 3: Install Dependencies

```bash
# Ensure venv is activated
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install requirements
pip install -r requirements.txt

# Verify installation
python -c "from src.api.main import app; print('✅ Imports working')"
```

### Step 4: Configure Environment

```bash
# Create .env file from template
cp .env.example .env

# Edit .env with production values
nano .env
```

**Example `.env` file:**

```bash
# Service Configuration
PORT=8015
SERVICE_NAME=context-engine
LOG_LEVEL=INFO

# GraphRAG Integration
GRAPHRAG_BASE_URL=http://10.10.0.87:8010
GRAPHRAG_TIMEOUT=20

# Supabase Integration (SENSITIVE!)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-service-role-key-here

# Cache Configuration
ENABLE_MEMORY_CACHE=true
ENABLE_REDIS_CACHE=false
ENABLE_DB_CACHE=false
CACHE_MEMORY_TTL=600
CACHE_ACTIVE_CASE_TTL=3600
CACHE_CLOSED_CASE_TTL=86400
CACHE_MAX_SIZE=1000
```

**Security Note**: Ensure `.env` is in `.gitignore` and has restrictive permissions:

```bash
# Restrict .env permissions
chmod 600 .env

# Verify it's not tracked by git
git check-ignore .env  # Should output: .env
```

### Step 5: Run Tests (Verification)

```bash
# Activate venv
source venv/bin/activate

# Run unit tests
pytest tests/unit/ -v

# Run integration tests (requires GraphRAG/Supabase)
pytest tests/integration/ -v

# Run all tests with coverage
pytest tests/ --cov=src --cov-report=term-missing
```

### Step 6: Test Manual Startup

```bash
# Activate venv
source venv/bin/activate

# Start service manually
python run.py

# In another terminal, test health endpoint
curl http://localhost:8015/api/v1/health
```

**Expected response:**
```json
{
  "status": "healthy",
  "service": "context-engine",
  "port": 8015,
  "version": "1.0.0"
}
```

---

## Configuration

### systemd Service File

**Location:** `/etc/systemd/system/luris-context-engine.service`

**Installation:**

```bash
# Copy service file to systemd directory
sudo cp luris-context-engine.service /etc/systemd/system/

# Reload systemd to recognize new service
sudo systemctl daemon-reload

# Enable service to start on boot
sudo systemctl enable luris-context-engine

# Verify service file is valid
sudo systemctl status luris-context-engine
```

### Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `PORT` | No | 8015 | Service listening port |
| `SERVICE_NAME` | No | context-engine | Service identifier |
| `LOG_LEVEL` | No | INFO | Logging level (DEBUG/INFO/WARNING/ERROR) |
| `GRAPHRAG_BASE_URL` | Yes | - | GraphRAG service URL |
| `GRAPHRAG_TIMEOUT` | No | 20 | GraphRAG request timeout (seconds) |
| `SUPABASE_URL` | Yes | - | Supabase project URL |
| `SUPABASE_KEY` | Yes | - | Supabase service role key |
| `ENABLE_MEMORY_CACHE` | No | true | Enable in-memory cache |
| `ENABLE_REDIS_CACHE` | No | false | Enable Redis cache (future) |
| `ENABLE_DB_CACHE` | No | false | Enable database cache (future) |
| `CACHE_MEMORY_TTL` | No | 600 | Memory cache TTL (seconds) |
| `CACHE_ACTIVE_CASE_TTL` | No | 3600 | Active case cache TTL |
| `CACHE_CLOSED_CASE_TTL` | No | 86400 | Closed case cache TTL |
| `CACHE_MAX_SIZE` | No | 1000 | Max memory cache entries |

---

## Service Management

### Starting the Service

```bash
# Start service
sudo systemctl start luris-context-engine

# Verify it started successfully
sudo systemctl status luris-context-engine

# Check logs for startup messages
sudo journalctl -u luris-context-engine -n 50 --no-pager
```

**Expected startup logs:**
```
Jan 22 10:00:00 systemd[1]: Started Luris Context Engine Service (Port 8015).
Jan 22 10:00:01 luris-context-engine: INFO:     Started server process [12345]
Jan 22 10:00:01 luris-context-engine: INFO:     Waiting for application startup.
Jan 22 10:00:01 luris-context-engine: INFO:     Application startup complete.
Jan 22 10:00:01 luris-context-engine: INFO:     Uvicorn running on http://0.0.0.0:8015
```

### Stopping the Service

```bash
# Stop service gracefully
sudo systemctl stop luris-context-engine

# Verify it stopped
sudo systemctl status luris-context-engine
```

### Restarting the Service

```bash
# Restart service (stop + start)
sudo systemctl restart luris-context-engine

# Or reload (if supported - graceful restart)
sudo systemctl reload luris-context-engine

# Check status after restart
sudo systemctl status luris-context-engine
```

### Viewing Service Status

```bash
# Detailed status
sudo systemctl status luris-context-engine

# Check if enabled for boot
sudo systemctl is-enabled luris-context-engine

# Check if currently active
sudo systemctl is-active luris-context-engine
```

### Viewing Logs

```bash
# Real-time logs (follow mode)
sudo journalctl -u luris-context-engine -f

# Last 100 lines
sudo journalctl -u luris-context-engine -n 100 --no-pager

# Logs since 1 hour ago
sudo journalctl -u luris-context-engine --since "1 hour ago"

# Logs for specific date
sudo journalctl -u luris-context-engine --since "2025-01-22 00:00:00"

# Logs with priority level
sudo journalctl -u luris-context-engine -p err  # Errors only
```

### Enabling/Disabling Auto-Start

```bash
# Enable (start on boot)
sudo systemctl enable luris-context-engine

# Disable (don't start on boot)
sudo systemctl disable luris-context-engine

# Check current state
sudo systemctl is-enabled luris-context-engine
```

---

## Monitoring

### Health Checks

**Primary Health Endpoint:**
```bash
# Basic health check
curl http://localhost:8015/api/v1/health

# Expected response:
# {"status": "healthy", "service": "context-engine", "port": 8015, "version": "1.0.0"}
```

**Cache Health:**
```bash
# Check cache system health
curl http://localhost:8015/api/v1/cache/health

# Expected response:
# {"status": "healthy", "tiers": {...}, "overall_hit_rate": 0.75}
```

**Cache Statistics:**
```bash
# Get cache performance metrics
curl http://localhost:8015/api/v1/cache/stats

# Expected response:
# {"memory_hits": 1523, "memory_hit_rate": 0.8145, ...}
```

### Prometheus Metrics

**Metrics Endpoint:**
```bash
# Prometheus metrics
curl http://localhost:8015/metrics

# Expected output (Prometheus format):
# # HELP context_engine_requests_total Total requests to Context Engine
# # TYPE context_engine_requests_total counter
# context_engine_requests_total{endpoint="/api/v1/health",method="GET"} 100.0
```

### Performance Monitoring

**Key Metrics to Monitor:**

| Metric | Threshold | Alert Condition |
|--------|-----------|-----------------|
| **Request Latency (p95)** | <2000ms | >3000ms |
| **Cache Hit Rate** | >70% | <50% |
| **Error Rate** | <1% | >5% |
| **Memory Usage** | <2GB | >3GB |
| **CPU Usage** | <200% | >300% |

**Query Performance:**
```bash
# Monitor request duration
curl -w "\nTime: %{time_total}s\n" http://localhost:8015/api/v1/health
```

### Resource Usage

```bash
# Check service resource consumption
systemd-cgtop | grep luris-context-engine

# Check memory usage
ps aux | grep context-engine

# Check open file descriptors
sudo lsof -p $(pgrep -f "context-engine") | wc -l
```

---

## Troubleshooting

### Service Won't Start

**Check 1: Port already in use**
```bash
# Check if port 8015 is already bound
sudo lsof -i :8015

# Kill conflicting process
sudo kill $(sudo lsof -t -i:8015)
```

**Check 2: Python/Dependencies issues**
```bash
# Verify Python version
/srv/luris/be/context-engine-service/venv/bin/python --version

# Verify imports work
/srv/luris/be/context-engine-service/venv/bin/python -c "from src.api.main import app"
```

**Check 3: Environment variables**
```bash
# Check .env file exists
ls -la /srv/luris/be/context-engine-service/.env

# Verify required env vars are set
sudo systemctl show luris-context-engine --property=Environment
```

**Check 4: Permissions**
```bash
# Verify ubuntu user owns files
ls -la /srv/luris/be/context-engine-service

# Fix ownership if needed
sudo chown -R ubuntu:ubuntu /srv/luris/be/context-engine-service
```

### Service Crashes/Restarts

**Check crash logs:**
```bash
# View crash logs
sudo journalctl -u luris-context-engine -p err --no-pager

# Check for OOM (out of memory) kills
sudo journalctl | grep -i "killed process.*context-engine"
```

**Common crash causes:**

1. **Out of Memory:** Increase MemoryMax in service file
2. **Dependency Unavailable:** GraphRAG or Supabase not reachable
3. **Configuration Error:** Invalid environment variables

### High Latency

**Diagnose slow requests:**

```bash
# Check cache hit rate
curl http://localhost:8015/api/v1/cache/stats | jq '.memory_hit_rate'

# Check GraphRAG service health
curl http://10.10.0.87:8010/api/v1/health

# Check database connections
psql -h localhost -U postgres -c "SELECT count(*) FROM pg_stat_activity WHERE datname = 'postgres';"
```

**Optimization steps:**

1. **Warm cache:** `curl -X POST http://localhost:8015/api/v1/cache/warmup`
2. **Clear old cache:** `curl -X DELETE http://localhost:8015/api/v1/cache/invalidate?case_id=...`
3. **Check GraphRAG latency:** Might need to optimize GraphRAG service

### High Error Rate

**Check error distribution:**
```bash
# Count error types in logs
sudo journalctl -u luris-context-engine --since "1 hour ago" | grep -i error | sort | uniq -c
```

**Common errors:**

| Error | Cause | Solution |
|-------|-------|----------|
| `Connection refused (GraphRAG)` | GraphRAG service down | Start GraphRAG service |
| `Database connection failed` | Supabase unreachable | Check Supabase status |
| `Context retrieval failed` | Missing case data | Verify case exists in DB |
| `Cache invalidation failed` | Cache corruption | Restart service to reset cache |

---

## Rollback Procedures

### Rollback to Previous Version

```bash
# Stop current service
sudo systemctl stop luris-context-engine

# Navigate to service directory
cd /srv/luris/be/context-engine-service

# Checkout previous version (replace with actual commit/tag)
git checkout v1.0.0  # Or specific commit hash

# Reinstall dependencies (in case they changed)
source venv/bin/activate
pip install -r requirements.txt

# Restart service
sudo systemctl start luris-context-engine

# Verify rollback successful
curl http://localhost:8015/api/v1/health
```

### Emergency Stop

```bash
# Immediate stop
sudo systemctl kill luris-context-engine

# Disable auto-restart
sudo systemctl disable luris-context-engine

# Verify stopped
sudo systemctl status luris-context-engine
```

---

## Backup and Recovery

### Configuration Backup

```bash
# Backup service file
sudo cp /etc/systemd/system/luris-context-engine.service \
     /etc/systemd/system/luris-context-engine.service.backup

# Backup .env file
cp /srv/luris/be/context-engine-service/.env \
   /srv/luris/be/context-engine-service/.env.backup
```

### Service Recovery

```bash
# Restore service file
sudo cp /etc/systemd/system/luris-context-engine.service.backup \
     /etc/systemd/system/luris-context-engine.service

# Reload systemd
sudo systemctl daemon-reload

# Restore .env
cp /srv/luris/be/context-engine-service/.env.backup \
   /srv/luris/be/context-engine-service/.env

# Restart service
sudo systemctl restart luris-context-engine
```

---

## Performance Tuning

### Memory Optimization

**Adjust cache size:**
```bash
# Edit .env
nano /srv/luris/be/context-engine-service/.env

# Modify:
CACHE_MAX_SIZE=2000  # Increase from 1000

# Restart service
sudo systemctl restart luris-context-engine
```

### CPU Optimization

**Increase worker processes:**
```python
# Edit run.py
uvicorn.run(
    "src.api.main:app",
    host="0.0.0.0",
    port=8015,
    workers=4,  # Add multiple workers
    log_level="info"
)
```

**Adjust systemd CPU quota:**
```bash
# Edit service file
sudo nano /etc/systemd/system/luris-context-engine.service

# Modify:
CPUQuota=400%  # Increase from 200%

# Reload and restart
sudo systemctl daemon-reload
sudo systemctl restart luris-context-engine
```

---

## Production Checklist

Before deploying to production, verify:

- [ ] All dependencies installed (`pip install -r requirements.txt`)
- [ ] `.env` file configured with production values
- [ ] GraphRAG service (port 8010) is running and healthy
- [ ] Supabase database is accessible
- [ ] Unit tests pass (`pytest tests/unit/`)
- [ ] Integration tests pass (`pytest tests/integration/`)
- [ ] Service file copied to `/etc/systemd/system/`
- [ ] systemd service enabled (`sudo systemctl enable luris-context-engine`)
- [ ] Service starts successfully (`sudo systemctl start luris-context-engine`)
- [ ] Health endpoint returns 200 (`curl http://localhost:8015/api/v1/health`)
- [ ] Logs show no errors (`sudo journalctl -u luris-context-engine -n 50`)
- [ ] Monitoring configured (Prometheus/Grafana)
- [ ] Backup procedures documented
- [ ] Rollback plan tested

---

**Last Updated**: 2025-01-22
**Maintained by**: Context Engine Development Team
**Support**: engineering@luris.ai (future)
