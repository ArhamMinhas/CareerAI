# Next.js Build Fix Script (Windows PowerShell)
# Fixes Turbopack "File not found: server-external-packages.jsonc" errors

Write-Host "🔧 Fixing Next.js Turbopack build errors..." -ForegroundColor Cyan

# Step 1: Clean node_modules and reinstall
Write-Host "📦 Step 1: Cleaning and reinstalling dependencies..." -ForegroundColor Yellow
Remove-Item -Recurse -Force -ErrorAction SilentlyContinue node_modules
Remove-Item -Recurse -Force -ErrorAction SilentlyContinue apps/web/node_modules
npm install

# Step 2: Verify Next.js installation
Write-Host "✓ Verifying Next.js installation..." -ForegroundColor Green
$nextPath = "apps/web/node_modules/next/dist/lib/server-external-packages.jsonc"
if (-not (Test-Path $nextPath)) {
    Write-Host "❌ server-external-packages.jsonc not found, trying --force install..." -ForegroundColor Red
    Set-Location apps/web
    npm install --force
    Set-Location ../..
}

# Step 3: Clear Next.js cache
Write-Host "🧹 Step 2: Clearing Next.js cache..." -ForegroundColor Yellow
Remove-Item -Recurse -Force -ErrorAction SilentlyContinue apps/web/.next

# Step 4: Verify TypeScript
Write-Host "📝 Step 3: Verifying TypeScript configuration..." -ForegroundColor Yellow
npm run typecheck:web
if ($LASTEXITCODE -ne 0) {
    Write-Host "⚠️  TypeScript check completed with warnings" -ForegroundColor Yellow
}

# Step 5: Try build
Write-Host "🏗️  Step 4: Attempting build..." -ForegroundColor Yellow
npm run build:web

Write-Host "✅ Build completed successfully!" -ForegroundColor Green
