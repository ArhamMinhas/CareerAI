# Next.js 15 / Turbopack Build Troubleshooting

## Error: "File not found: server-external-packages.jsonc"

**Cause:** Next.js distribution files are missing or corrupt — typically due to incomplete npm installation.

**Status:** ⚠️ CRITICAL (blocks build)

---

## Quick Fix (All Platforms)

### Option 1: Clean Install (Recommended)

```bash
# PowerShell (Windows)
rm -r node_modules, apps/web/node_modules, apps/web/.next
npm install
npm run build:web

# Bash (macOS/Linux)
rm -rf node_modules apps/web/node_modules apps/web/.next
npm install
npm run build:web
```

### Option 2: Automated Script

**Windows (PowerShell):**
```powershell
.\scripts\fix-nextjs-build.ps1
```

**macOS/Linux (Bash):**
```bash
bash scripts/fix-nextjs-build.sh
```

### Option 3: Force Reinstall with npm

```bash
npm cache clean --force
npm install --force
npm run build:web
```

---

## Why This Happens

1. **Incomplete npm install** — network interruption, disk full
2. **Corrupted node_modules** — partially downloaded files
3. **Version mismatch** — npm workspace resolution issue
4. **Disk space** — insufficient space for full node_modules
5. **Permission issues** — can't write to node_modules directory

---

## Step-by-Step Fix

### Step 1: Clean Everything

```bash
# Remove node_modules
rm -rf node_modules apps/web/node_modules

# Remove cache
rm -rf apps/web/.next
rm -rf apps/web/.turbo

# Clear npm cache
npm cache clean --force
```

### Step 2: Reinstall Dependencies

```bash
# Standard install
npm install

# Or with verbose output (to see issues)
npm install --verbose

# Or force (ignore peer dependency warnings)
npm install --force
```

### Step 3: Verify Installation

```bash
# Check if server-external-packages.jsonc exists
ls -la apps/web/node_modules/next/dist/lib/server-external-packages.jsonc

# Or on Windows PowerShell
Test-Path "apps/web/node_modules/next/dist/lib/server-external-packages.jsonc"
```

### Step 4: Build

```bash
# Type check first
npm run typecheck:web

# Then build
npm run build:web
```

---

## Turbopack-Specific Issues

### Issue: "Turbopack cannot find module X"

**Cause:** Module path alias not resolved in Turbopack

**Fix:** Verify `next.config.ts` has:
```typescript
turbo: {
  resolveAlias: {
    "@/*": "./*",
  },
},
```

### Issue: "Turbopack memory exceeded"

**Cause:** Large monorepo or too many concurrent builds

**Fix:** Increase Node.js memory:
```bash
# Windows (PowerShell)
$env:NODE_OPTIONS = "--max-old-space-size=4096"
npm run build:web

# macOS/Linux (Bash)
export NODE_OPTIONS="--max-old-space-size=4096"
npm run build:web
```

### Issue: "Turbopack cache invalid"

**Cause:** Cache file corruption

**Fix:** Clear Turbopack cache:
```bash
rm -rf apps/web/.next/.turbo
npm run build:web
```

---

## Next.js Version Compatibility

Current setup uses **Next.js 15.5.23** with Turbopack enabled by default.

### Check Version

```bash
npm list next
# Should show: next@15.5.23
```

### If Version Mismatch

```bash
# Update to latest
npm install next@latest eslint-config-next@latest

# Or pin to specific version
npm install next@15.5.23 eslint-config-next@15.5.23
```

---

## Build Optimization

### Enable Turbopack Explicitly

```bash
# In package.json scripts
"dev": "next dev --turbo",
"build": "next build --turbo",
```

Or in `next.config.ts`:
```typescript
export const nextConfig = {
  turbo: {
    cacheOnDisk: true,
  },
};
```

### Optimize Large Projects

For faster builds:

```typescript
// next.config.ts
const nextConfig: NextConfig = {
  experimental: {
    // Optimize imports from these packages
    optimizePackageImports: [
      "@radix-ui/react-accordion",
      "@react-three/fiber",
      "recharts",
    ],
  },
};
```

### Disable Turbopack (Fallback)

If Turbopack still fails, fall back to Webpack:

```bash
# Set environment variable
# Windows (PowerShell)
$env:NEXT_EXPERIMENTAL_TURBOPACK = "false"
npm run build:web

# macOS/Linux (Bash)
export NEXT_EXPERIMENTAL_TURBOPACK=false
npm run build:web
```

Or in `next.config.ts`:
```typescript
const nextConfig: NextConfig = {
  // Disable Turbopack and use Webpack instead
  experimental: {
    turbopack: false,
  },
};
```

---

## TypeScript Issues

### "Cannot find module X"

**Cause:** TypeScript paths not configured

**Fix:** Verify `tsconfig.json`:
```json
{
  "compilerOptions": {
    "paths": {
      "@/*": ["./*"]
    }
  }
}
```

### "No overload matches"

**Cause:** Type definition mismatch with React 19

**Fix:** Ensure React/React-DOM versions match:
```bash
npm list react react-dom
# Should both be 19.2.8
```

Update if needed:
```bash
npm install react@19.2.8 react-dom@19.2.8 @types/react@19 @types/react-dom@19
```

---

## Docker Build Issues

### In Dockerfile.web

If build fails in Docker, add these to Dockerfile:

```dockerfile
# Increase Node.js memory
ENV NODE_OPTIONS="--max-old-space-size=4096"

# Disable Turbopack if needed (fallback)
ENV NEXT_EXPERIMENTAL_TURBOPACK=false

# Install with verbose output
RUN npm ci --verbose

# Or force install
RUN npm ci --force
```

### Updated Dockerfile

```dockerfile
FROM node:22-slim AS base
WORKDIR /repo
RUN --mount=type=cache,target=/var/cache/apt \
    apt-get update && apt-get install -y --no-install-recommends dumb-init

FROM base AS deps
ENV NODE_OPTIONS="--max-old-space-size=4096"
COPY package.json package-lock.json ./
COPY apps/web/package.json apps/web/package.json
RUN --mount=type=cache,target=/root/.npm \
    npm ci --prefer-offline --no-audit || npm ci --force

FROM deps AS builder
ENV NODE_OPTIONS="--max-old-space-size=4096"
COPY . .
RUN npm run build --workspace=apps/web && npm prune --omit=dev

FROM base AS production
ENV NODE_ENV=production NODE_OPTIONS="--max-old-space-size=2048"
RUN addgroup --system --gid 1001 nodejs && adduser --system --uid 1001 nextjs
COPY --from=builder --chown=nextjs:nodejs /repo/apps/web/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /repo/apps/web/.next/static ./apps/web/.next/static
COPY --from=builder --chown=nextjs:nodejs /repo/apps/web/public ./apps/web/public
USER nextjs
EXPOSE 3000
ENTRYPOINT ["/usr/bin/dumb-init", "--"]
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \
  CMD node -e "require('http').get('http://localhost:3000', (r) => {if (r.statusCode !== 200) throw new Error(r.statusCode)})"
CMD ["node", "apps/web/server.js"]
```

---

## CI/CD Issues

### GitHub Actions Build Fails

In `.github/workflows/ci.yml`, add retry logic:

```yaml
- name: Install dependencies
  run: npm ci
  retries: 3
  retry-wait-seconds: 30

- name: Build
  run: npm run build:web
  env:
    NODE_OPTIONS: "--max-old-space-size=4096"
```

### Increase Node Memory in CI

```yaml
- name: Build
  run: npm run build:web
  env:
    NODE_OPTIONS: "--max-old-space-size=8192"  # 8GB for CI
```

---

## Disk Space Issues

If build fails with "disk full":

```bash
# Check disk usage
df -h

# Or on Windows
Get-Volume

# Clean docker images (if using Docker)
docker system prune -a

# Clean npm cache
npm cache clean --force

# Remove build artifacts
npm run clean:web
```

---

## Permission Issues (Linux/macOS)

```bash
# Fix npm permissions
mkdir ~/.npm-global
npm config set prefix '~/.npm-global'
export PATH=~/.npm-global/bin:$PATH

# Or use sudo (not recommended)
sudo npm install

# Or fix directory ownership
sudo chown -R $(whoami) ~/.npm
```

---

## Verification Checklist

After fixing:

- [ ] `npm list next` shows 15.5.23
- [ ] `ls apps/web/node_modules/next/dist/lib/server-external-packages.jsonc` exists
- [ ] `npm run typecheck:web` passes
- [ ] `npm run build:web` succeeds
- [ ] Build takes <2 minutes (Turbopack) or <5 minutes (Webpack)
- [ ] No TypeScript errors
- [ ] No "File not found" errors

---

## Getting Help

If issues persist:

1. **Check logs:**
   ```bash
   npm run build:web --verbose 2>&1 | tee build.log
   ```

2. **Check Next.js version:**
   ```bash
   npm list next eslint-config-next
   ```

3. **Report to Next.js:**
   - Visit: https://github.com/vercel/next.js/issues
   - Include build log and `npm list` output

4. **Check Turbopack status:**
   - Visit: https://turbo.build/pack
   - Known issues: https://github.com/vercel/turbo/issues

---

**Status:** Phase 1+
**Last Updated:** Phase 6
**Tested:** ✅ Windows, macOS, Linux, Docker
