# Docker Quick Reference

## Local Development

### Start
```bash
# Enable BuildKit (recommended, faster builds)
export DOCKER_BUILDKIT=1

# Start all services
docker-compose up -d

# Start with logs visible
docker-compose up

# Rebuild images
docker-compose up -d --build
```

### Check Health
```bash
# View all services and their health status
docker-compose ps

# View logs
docker-compose logs -f

# View logs for specific service
docker-compose logs -f api
docker-compose logs -f web

# Check health endpoint
curl http://localhost:8000/api/v1/health
curl http://localhost:3000
```

### Stop
```bash
# Stop all services (data persists)
docker-compose down

# Stop and remove volumes (clears database!)
docker-compose down -v

# Stop and remove everything including images
docker-compose down -v --remove-images
```

### Debug
```bash
# Shell into running container
docker-compose exec api bash
docker-compose exec web bash
docker-compose exec postgres psql -U careerai -d careerai

# Run one-off command
docker-compose exec api python -c "from app.main import app; print(app)"

# View container resource usage
docker stats
```

---

## Building Images

### Development
```bash
# Build dev target (includes test tools, hot-reload)
docker build -f infrastructure/docker/Dockerfile.api -t careerai-api:dev --target dev .
docker build -f infrastructure/docker/Dockerfile.web -t careerai-web:dev --target dev .
docker build -f infrastructure/docker/Dockerfile.worker -t careerai-worker:dev --target dev .
```

### Production
```bash
# Build production target (optimized, no dev tools)
docker build -f infrastructure/docker/Dockerfile.api -t careerai-api:latest --target production .
docker build -f infrastructure/docker/Dockerfile.web -t careerai-web:latest --target production .
docker build -f infrastructure/docker/Dockerfile.worker -t careerai-worker:latest --target production .

# With BuildKit cache optimization
docker buildx build -f infrastructure/docker/Dockerfile.api -t careerai-api:latest --target production .
```

### Inspect Image
```bash
# View image layers
docker history careerai-api:latest

# View image size
docker images careerai-api:latest

# Inspect image details
docker inspect careerai-api:latest

# View Dockerfile used to build (if available)
docker run --rm careerai-api:latest cat /Dockerfile
```

---

## Pushing Images

### To Docker Hub
```bash
# Login
docker login

# Tag
docker tag careerai-api:latest myusername/careerai-api:latest
docker tag careerai-api:latest myusername/careerai-api:v1.2.3

# Push
docker push myusername/careerai-api:latest
docker push myusername/careerai-api:v1.2.3
```

### To GitHub Container Registry (GHCR)
```bash
# Login (requires GITHUB_TOKEN with packages scope)
docker login ghcr.io

# Tag
docker tag careerai-api:latest ghcr.io/myorg/careerai-api:latest

# Push
docker push ghcr.io/myorg/careerai-api:latest
```

---

## Troubleshooting

### Container won't start
```bash
# Check logs
docker-compose logs api

# Check if port is in use
lsof -i :8000  # API
lsof -i :3000  # Web
lsof -i :5432  # Postgres

# Check image exists
docker images | grep careerai

# Try without cache
docker-compose build --no-cache api
docker-compose up -d api
```

### Health check failing
```bash
# Check service individually
docker-compose up -d postgres redis
docker-compose up api

# View health check history
docker inspect careerai-api-1 | grep -A 20 '"Health"'

# Manually test health endpoint
docker-compose exec api curl http://localhost:8000/api/v1/health
```

### Database connection error
```bash
# Verify postgres is healthy
docker-compose ps postgres

# Test connection
docker-compose exec postgres psql -U careerai -d careerai -c "SELECT 1"

# Check environment variables
docker-compose exec api env | grep DATABASE_URL
```

### Out of disk space
```bash
# Remove unused images
docker image prune -a

# Remove unused volumes
docker volume prune

# Clear build cache
docker builder prune --all

# Check docker disk usage
docker system df
```

### Permission denied errors
```bash
# Restart docker daemon
sudo systemctl restart docker  # Linux
open /Applications/Docker.app  # macOS
# Restart via UI on Windows

# Or rebuild with fresh user ownership
docker-compose down -v
docker-compose build --no-cache
docker-compose up -d
```

---

## Performance Optimization

### Enable BuildKit (faster builds)
```bash
# Bash/Zsh
export DOCKER_BUILDKIT=1

# Windows (PowerShell)
$env:DOCKER_BUILDKIT="1"

# Permanent (Linux/macOS, add to ~/.bashrc or ~/.zshrc)
export DOCKER_BUILDKIT=1
```

### Monitor Resource Usage
```bash
# Real-time stats
docker stats

# Limit container resources in compose
# services:
#   api:
#     deploy:
#       resources:
#         limits:
#           cpus: '0.5'
#           memory: 512M
```

### Parallel Builds
```bash
# Build multiple images in parallel
docker-compose build --parallel
```

---

## Common Docker Compose Commands

```bash
# General
docker-compose version
docker-compose config          # View resolved config
docker-compose validate        # Validate syntax

# Lifecycle
docker-compose up              # Create + start
docker-compose up -d           # Detached
docker-compose up --no-deps    # Skip dependencies
docker-compose restart         # Restart services
docker-compose down            # Stop + remove
docker-compose stop            # Stop (don't remove)

# Services
docker-compose ps              # List running services
docker-compose logs            # View logs (all)
docker-compose logs -f         # Follow logs
docker-compose exec api bash   # Execute in container

# Building
docker-compose build           # Build images
docker-compose build --no-cache # Ignore cache
docker-compose push            # Push to registry
docker-compose pull            # Pull from registry

# Cleanup
docker-compose down -v         # Remove volumes
docker-compose down --remove-images # Remove images
```

---

## Docker Secrets (Production)

Store sensitive data securely:

```bash
# Create secret
docker secret create api_key -

# Use in compose (with docker stack deploy, not docker-compose)
services:
  api:
    secrets:
      - api_key
```

Or use environment variables with `.env` files (local only, never commit).

---

## Useful Docker Aliases

Add to `~/.bashrc`, `~/.zshrc`, or PowerShell profile:

```bash
alias dc='docker-compose'
alias dcup='docker-compose up -d'
alias dcdown='docker-compose down'
alias dclogs='docker-compose logs -f'
alias dcps='docker-compose ps'
alias dcexec='docker-compose exec'

# Windows PowerShell
function dc { docker-compose @args }
function dcup { docker-compose up -d @args }
function dcdown { docker-compose down @args }
```

---

## Resources

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Reference](https://docs.docker.com/compose/compose-file/)
- [Best Practices](https://docs.docker.com/develop/dev-best-practices/)
- [Security Best Practices](https://docs.docker.com/engine/security/)
