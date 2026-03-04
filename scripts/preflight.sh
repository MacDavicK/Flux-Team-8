#!/bin/bash
# Run from ~/Downloads/Flux

echo "=== PRE-FLIGHT CHECKS ==="

# 1. Backend deps
echo "[1/6] Backend dependencies..."
cd backend
source venv/bin/activate 2>/dev/null || source .venv/bin/activate 2>/dev/null
pip install -r requirements.txt --quiet
python -c "import jwt; import openai; import pinecone; print('✅ Backend deps OK')" 2>&1 || echo "❌ Missing backend deps"

# 2. Frontend deps
echo "[2/6] Frontend dependencies..."
cd ../frontend
npm install --silent 2>/dev/null
npx tsc --noEmit 2>&1 | tail -1 && echo "✅ TypeScript OK" || echo "❌ TypeScript errors"

# 3. Env files
echo "[3/6] Backend .env..."
cd ../backend
for var in SUPABASE_URL SUPABASE_KEY OPEN_ROUTER_API_KEY PINECONE_API_KEY; do
  grep -q "$var" .env 2>/dev/null && echo "  ✅ $var set" || echo "  ❌ $var MISSING"
done

echo "[4/6] Frontend .env..."
cd ../frontend
grep -q "VITE_API_URL" .env 2>/dev/null && echo "  ✅ VITE_API_URL set" || echo "  ❌ VITE_API_URL MISSING"
grep -q "VITE_USE_MOCK=false" .env 2>/dev/null && echo "  ✅ VITE_USE_MOCK=false" || echo "  ⚠️  VITE_USE_MOCK is not false"

# 4. Supabase migration
echo "[5/6] Supabase migration..."
cd ..
ls supabase/migrations/*analytics* 2>/dev/null && echo "  ✅ Analytics migration file exists" || echo "  ⚠️  No analytics migration found"
echo "  ⚠️  Reminder: Run 'supabase db push' or apply migration manually if not done"

# 5. Heatmap URL check (the open question)
echo "[6/6] Heatmap API path check..."
grep -n "analyticsHeatmap" frontend/src/utils/api.ts
echo "  ↑ Verify this hits /analytics/overview (not /analytics/heatmap)"
echo ""
echo "=== PRE-FLIGHT COMPLETE ==="
