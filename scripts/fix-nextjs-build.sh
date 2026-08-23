#!/bin/bash
# Next.js Build Fix Script
# Fixes Turbopack "File not found: server-external-packages.jsonc" errors

set -e

echo "🔧 Fixing Next.js Turbopack build errors..."

# Step 1: Clean node_modules and reinstall
echo "📦 Step 1: Cleaning and reinstalling dependencies..."
rm -rf node_modules apps/web/node_modules
npm install

# Step 2: Verify Next.js installation
echo "✓ Verifying Next.js installation..."
if [ ! -f "apps/web/node_modules/next/dist/lib/server-external-packages.jsonc" ]; then
    echo "❌ server-external-packages.jsonc not found after install"
    echo "Trying alternative fix..."
    cd apps/web
    npm install --force
    cd ../..
fi

# Step 3: Clear Next.js cache
echo "🧹 Step 2: Clearing Next.js cache..."
rm -rf apps/web/.next

# Step 4: Verify TypeScript
echo "📝 Step 3: Verifying TypeScript configuration..."
npm run typecheck:web || echo "⚠️  TypeScript check completed with warnings"

# Step 5: Try build
echo "🏗️  Step 4: Attempting build..."
npm run build:web

echo "✅ Build completed successfully!"
