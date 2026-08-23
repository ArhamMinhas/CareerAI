# Docker Verification Checklist

Use this checklist to verify all Docker fixes are working correctly.

---

## Pre-Flight Checks

- [ ] Docker Desktop is running
- [ ] `docker --version` shows version 20.10+
- [ ] `docker-compose --version` shows version 1.29+
- [ ] Sufficient disk space: `docker system df`
- [ ] BuildKit enabled: `export DOCKER_BUILDKIT=1`

---

## Build Verification

```bash
# Clean build (no cache)
docker-compose down -v --remove-images
docker-compose build --no-cache

# Expected output:
# [+] Building 0.1s (XX/XX)
# => careerai-api:dev
# => careerai-web:dev
# => careerai-worker:dev
```

**Checklist:**
- [ ] Build completes without errors
- [ ] No "permission denied" errors
- [ ] All three images built (web, api, worker)
- [ ] BuildKit steps shown (cache mounting worked)

---

## Container Start Verification

```bash
docker-compose up -d
sleep 10  # Wait for startup
docker-compose ps
```

**Expected output:**
```
NAME                COMMAND                  STATUS       PORTS
careerai-postgres-1 "docker-entrypoint..."  Up (healthy) 0.0.0.0:5432->5432/tcp
careerai-redis-1    "redis-server --appen" Up (healthy) 0.0.0.0:6379->6379/tcp
careerai-api-1      "uvicorn app.main..."   Up (healthy) 0.0.0.0:8000->8000/tcp
careerai-worker-1   "celery -A app.worker"  Up (healthy)
careerai-web-1      "npm run dev"           Up (healthy) 0.0.0.0:3000->3000/tcp
```

**Checklist:**
- [ ] All 5 services in "Up" status
- [ ] All services show "(healthy)" after ~40s
- [ ] No services restarting or crashing
- [ ] Ports correctly mapped (5432, 6379, 8000, 3000)

---

## Health Check Verification

```bash
# Check postgres
docker-compose exec postgres pg_isready -U careerai -d careerai
# Expected: accepting connections

# Check redis
docker-compose exec redis redis-cli ping
# Expected: PONG

# Check API health
curl http://localhost:8000/api/v1/health
# Expected: {"status": "ok"} or similar JSON response

# Check web
curl http://localhost:3000 -I
# Expected: HTTP/1.1 200 or 304 (not 500, not refused)
```

**Checklist:**
- [ ] Postgres responds to pg_isready
- [ ] Redis responds with PONG
- [ ] API returns successful response (200-level)
- [ ] Web returns successful response (200-level)

---

## Log Verification

```bash
# View all logs
docker-compose logs

# API should show startup without errors
docker-compose logs api | grep -i "error\|critical\|failed" | head -5
# Should return nothing (or safe warnings only)

# Web should show "ready" message
docker-compose logs web | grep -i "ready\|listening"

# Worker should show startup
docker-compose logs worker | grep -i "connected\|worker started"
```

**Checklist:**
- [ ] No ERROR or CRITICAL messages in API logs
- [ ] Web shows "ready" or "listening"
- [ ] Worker shows connection established
- [ ] All services log normally (no repeated errors)

---

## Security Verification

```bash
# Verify non-root user
docker-compose exec api whoami
# Expected: appuser

docker-compose exec web whoami
# Expected: nextjs

docker-compose exec worker whoami
# Expected: appuser

# Verify no-new-privileges
docker inspect careerai-api-1 | grep -i "no-new-privileges"
# Expected: "no-new-privileges": true
```

**Checklist:**
- [ ] API runs as appuser (not root)
- [ ] Web runs as nextjs (not root)
- [ ] Worker runs as appuser (not root)
- [ ] All services have no-new-privileges enabled

---

## Cache Verification

Clean rebuild should be faster (demonstrating cache hits):

```bash
# First build (cold cache)
docker-compose build --no-cache api 2>&1 | tee build1.log
# Time the output

# Second build (warm cache)
docker-compose build api 2>&1 | tee build2.log
# Time should be significantly less

# Compare logs
grep "cache" build1.log | wc -l
grep "cache" build2.log | wc -l
# Second should have more cache hits
```

**Checklist:**
- [ ] First build takes ~2-3 minutes
- [ ] Second build takes ~30-60 seconds
- [ ] Second build shows more cache hits
- [ ] Times are reproducible

---

## Volume & Persistence Verification

```bash
# Create test data
docker-compose exec postgres psql -U careerai -d careerai \
  -c "CREATE TABLE test_table AS SELECT 'persistent' AS data;"

# Stop containers (but don't remove volumes)
docker-compose down

# Start containers again
docker-compose up -d

# Verify data persists
docker-compose exec postgres psql -U careerai -d careerai \
  -c "SELECT * FROM test_table;"
# Expected: persistent

# Cleanup
docker-compose exec postgres psql -U careerai -d careerai \
  -c "DROP TABLE test_table;"
```

**Checklist:**
- [ ] Data persists after container restart
- [ ] Postgres volume mounted correctly
- [ ] Redis volume mounted correctly
- [ ] No "permission denied" errors

---

## Graceful Shutdown Verification

```bash
# Check dumb-init in web (should be PID 1)
docker-compose exec web ps aux | grep dumb-init
# Expected: /usr/bin/dumb-init -- node apps/web/server.js

# Stop containers and watch for clean exit
docker-compose down 2>&1 | tee shutdown.log

# Verify no "killed" or "forcefully stopped"
grep -i "killed\|forcefully" shutdown.log
# Should return nothing
```

**Checklist:**
- [ ] dumb-init is entrypoint
- [ ] Shutdown logs show "Stopping" (SIGTERM), not "Killing" (SIGKILL)
- [ ] All containers exit cleanly within 10s
- [ ] No errors in shutdown output

---

## File Ownership Verification

```bash
# Check API files ownership
docker-compose exec api ls -la /app
# Expected: appuser:appuser (not root:root)

# Check Web files ownership
docker-compose exec web ls -la /repo
# Expected: nextjs:nodejs (not root:root)

# Test write permission (worker writes temp files)
docker-compose exec api touch /app/test-write.txt && rm /app/test-write.txt
# Should succeed (not "permission denied")
```

**Checklist:**
- [ ] API files owned by appuser:appuser
- [ ] Web files owned by nextjs:nodejs
- [ ] Non-root users can write to application directories
- [ ] No "permission denied" errors

---

## Signal Handling Verification

```bash
# Get API container ID
CONTAINER=$(docker-compose ps -q api)

# Send SIGTERM (graceful shutdown signal)
docker kill --signal SIGTERM $CONTAINER

# Should exit cleanly, not be forcefully killed
sleep 1
docker-compose ps | grep api
# Container should be stopped (not running)
```

**Checklist:**
- [ ] Container responds to SIGTERM
- [ ] Graceful shutdown (not forced)
- [ ] Application has time to clean up
- [ ] No "Container killed" messages (unless forced)

---

## Integration Verification

```bash
# Test web → API connection
docker-compose exec web curl http://api:8000/api/v1/health
# Expected: successful response (shows internal DNS works)

# Test API → Database connection
docker-compose exec api python -c "from app.main import app; print('App loaded')"
# Expected: App loaded (no connection errors)

# Test API → Redis connection
docker-compose exec api python -c "import redis; r=redis.from_url('redis://redis:6379/0'); print(r.ping())"
# Expected: True
```

**Checklist:**
- [ ] Web can reach API via Docker network
- [ ] API can reach Postgres
- [ ] API can reach Redis
- [ ] Internal DNS resolution works

---

## Performance Verification

```bash
# Monitor resource usage
docker stats

# Expected (steady state after ~1min):
# - API: ~50-100MB memory, <1% CPU
# - Web: ~100-150MB memory, <1% CPU
# - Worker: ~80-120MB memory, <1% CPU
# - Postgres: ~50-100MB memory, <1% CPU
# - Redis: ~20-50MB memory, <1% CPU

# Stop monitoring (Ctrl+C)
```

**Checklist:**
- [ ] No memory leaks (stable after 1 min)
- [ ] Low CPU usage (idle state)
- [ ] All containers under 500MB each
- [ ] Redis memory bounded at 256MB

---

## Cleanup & Final Check

```bash
# Stop all services
docker-compose down

# Remove all volumes (clean slate)
docker-compose down -v

# Remove images
docker-compose down --remove-images

# Verify cleanup
docker ps -a | grep careerai
# Expected: (empty)

docker images | grep careerai
# Expected: (empty)
```

**Checklist:**
- [ ] All containers removed
- [ ] All volumes removed
- [ ] All images removed
- [ ] Clean state for fresh start

---

## Sign-Off

After completing all checks:

- [ ] All 5 services start and show "healthy"
- [ ] All health checks pass (postgres, redis, api, web)
- [ ] Non-root users verified
- [ ] Security options verified
- [ ] Graceful shutdown confirmed
- [ ] No permission errors
- [ ] Data persists across restarts
- [ ] Resource usage is bounded
- [ ] Signal handling is correct

**Status:** ✅ Docker configuration is correct and production-ready

---

## Troubleshooting

If any check fails, refer to:
- `docs/DOCKER.md` — Detailed issue descriptions
- `DOCKER_QUICK_REF.md` — Common commands and fixes
- `docker-compose logs -f` — Real-time logs

---

**Date Verified:** [Fill in date]
**Verified By:** [Your name]
**Next Review:** Phase 16 (production deployment)
