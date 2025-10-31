# Quick Start: Strategy Version Deployment

## ✅ Setup Complete!

Your freqtrade Helm chart now automatically tracks and deploys strategy versions.

## 🚀 How to Deploy a New Strategy Version

### 3-Step Process

#### Step 1: Update Your Strategy
```bash
# Edit any strategy file
vim extra_strategies/ClaudiusCryptoStrategyEnhancedBinance.py
# Make your changes...
```

#### Step 2: Increment Version
```bash
# Edit values-base.yaml
vim chart/values-base.yaml
```

Change this line:
```yaml
configcreds:
  strategy_version: "2025-10-30-14:00"  # ← Change this!
```

To:
```yaml
configcreds:
  strategy_version: "2025-10-30-16:45"  # ← New version!
```

#### Step 3: Deploy
```bash
helm upgrade freqtrade ./chart \
  -f chart/values-base.yaml \
  -f chart/values-binance-futures.yaml \
  --namespace binance-futures
```

### ✅ Verify Deployment
```bash
# Watch the rollout
kubectl rollout status deployment/freqtrade-binance-futures -n binance-futures

# Check logs for new version
kubectl logs -n binance-futures deployment/freqtrade-binance-futures -f | grep "Bot Loop Start"
```

**Expected output:**
```
🔄 Bot Loop Start - Strategy Version: 2025-10-30-16:45 - Time: 2025-10-30 16:45:12
```

## 🎯 What Happens Automatically

When you change `strategy_version` and run `helm upgrade`:

1. ✅ Helm updates the ConfigMap with new version
2. ✅ Kubernetes detects changed pod annotation
3. ✅ New pods are created with updated config
4. ✅ Old pods are gracefully terminated
5. ✅ Each strategy logs its version on every loop

## 📋 One-Command Deployment Script

Create this script for quick deployments:

```bash
#!/bin/bash
# File: deploy-strategy.sh

# Get new version (timestamp)
NEW_VERSION=$(date +"%Y-%m-%d-%H:%M")

echo "📦 Deploying Strategy Version: ${NEW_VERSION}"

# Update version in values file
sed -i.bak "s/strategy_version: \".*\"/strategy_version: \"${NEW_VERSION}\"/" chart/values-base.yaml

# Deploy
helm upgrade freqtrade ./chart \
  -f chart/values-base.yaml \
  -f chart/values-binance-futures.yaml \
  --namespace binance-futures \
  --install

# Watch rollout
kubectl rollout status deployment/freqtrade-binance-futures -n binance-futures

# Show version in logs
echo "✅ Checking deployed version..."
sleep 5
kubectl logs -n binance-futures deployment/freqtrade-binance-futures --tail=20 | grep "Bot Loop Start" | tail -1

echo "🎉 Deployment Complete!"
```

**Usage:**
```bash
chmod +x deploy-strategy.sh
./deploy-strategy.sh
```

## 🔍 Useful Commands

### Check Current Version
```bash
# From pod annotation
kubectl get pods -n binance-futures \
  -o jsonpath='{.items[0].metadata.annotations.strategy\.version}' && echo

# From logs
kubectl logs -n binance-futures deployment/freqtrade-binance-futures \
  --tail=100 | grep "Bot Loop Start" | tail -1
```

### Force Rollout (without version change)
```bash
kubectl rollout restart deployment/freqtrade-binance-futures -n binance-futures
```

### Rollback to Previous Version
```bash
kubectl rollout undo deployment/freqtrade-binance-futures -n binance-futures
```

### View Rollout History
```bash
kubectl rollout history deployment/freqtrade-binance-futures -n binance-futures
```

## 📊 All Modified Strategies

These strategies now log their version on every bot loop:

1. ✅ `ClaudiusCryptoStrategyEnhancedBinance` (updated existing method)
2. ✅ `ClaudiusCryptoStrategyEnhanced` (added new method)
3. ✅ `ClaudiusCryptoStrategy` (added new method)
4. ✅ `MultiMetricStrategyHF` (added new method)
5. ✅ `MultiMetricStrategy` (added new method)

## ⚠️ Important Notes

1. **Always increment version** when changing strategy code
2. **Use descriptive versions** like `2025-10-30-15:30-fixed-stoploss`
3. **Watch rollout progress** to ensure successful deployment
4. **Check logs** to verify new version is running

## 📚 Documentation

- **Detailed Guide:** [STRATEGY_VERSION_DEPLOYMENT_GUIDE.md](./STRATEGY_VERSION_DEPLOYMENT_GUIDE.md)
- **Changes Summary:** [CHANGES_STRATEGY_VERSION.md](./CHANGES_STRATEGY_VERSION.md)

## 🎉 Ready to Use!

Your deployment system is now configured to:
- ✅ Track strategy versions
- ✅ Auto-rollout on version changes
- ✅ Log version information
- ✅ Enable easy rollbacks
- ✅ Support zero-downtime deployments

**Happy Trading! 🚀📈**

