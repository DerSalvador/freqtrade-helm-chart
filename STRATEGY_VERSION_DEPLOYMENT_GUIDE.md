# Strategy Version Deployment Guide

## Overview

This guide explains how to ensure the latest strategy version is always deployed using the `strategy_version` attribute in your Helm chart configuration.

## How It Works

### 1. **Strategy Version Tracking**

Every strategy now logs its version at the start of each bot loop:

```python
def bot_loop_start(self, current_time: datetime, **kwargs) -> None:
    """
    Called when the bot loop starts (every iteration).
    Logs the current strategy version for tracking deployments.
    """
    # Log strategy version at the very beginning
    strategy_version = self.config.get('strategy_version', 'unknown')
    logger.info(f'🔄 Bot Loop Start - Strategy Version: {strategy_version} - Time: {current_time}')
```

**Updated Strategies:**
- ✅ `ClaudiusCryptoStrategyEnhancedBinance`
- ✅ `ClaudiusCryptoStrategyEnhanced`
- ✅ `ClaudiusCryptoStrategy`
- ✅ `MultiMetricStrategyHF`
- ✅ `MultiMetricStrategy`

### 2. **Configuration Setup**

The `strategy_version` is defined in `chart/values-base.yaml`:

```yaml
configcreds:
  # ⚠️ IMPORTANT: Increment this version to force new deployment with latest strategy
  # Format: YYYY-MM-DD-HH:MM or any unique identifier
  # This value is logged in bot_loop_start() for all strategies
  strategy_version: "2025-10-30-14:00"
```

### 3. **Kubernetes Pod Annotation**

The deployment template (`chart/templates/deployment.yaml`) includes the strategy version as a pod annotation:

```yaml
template:
  metadata:
    annotations:
      # Force pod restart when strategy version changes
      strategy.version: "{{ .Values.configcreds.strategy_version }}"
      # Also track config changes
      checksum/config: {{ include (print $.Template.BasePath "/configmap.yaml") . | sha256sum }}
      checksum/configcreds: {{ include (print $.Template.BasePath "/configmapcreds.yaml") . | sha256sum }}
    labels:
      strategy-version: "{{ .Values.configcreds.strategy_version }}"
```

**Key Benefits:**
- When `strategy_version` changes, Kubernetes detects a different pod template
- Automatic rolling update is triggered
- Old pods are terminated, new pods are created
- Zero downtime deployment

### 4. **Image Pull Policy**

The deployment already has `imagePullPolicy: Always` set, ensuring the latest Docker image is always pulled:

```yaml
imagePullPolicy: Always
```

## Deployment Workflow

### Step 1: Update Your Strategy Code

Make changes to your strategy files in:
```
/Users/msantana/dersalvador/freqtrading/freqtrade/extra_strategies/
```

### Step 2: Update the Strategy Version

Edit `chart/values-base.yaml`:

```yaml
configcreds:
  strategy_version: "2025-10-30-15:30"  # ← Change this timestamp
```

**Recommended Format:**
- `YYYY-MM-DD-HH:MM` - Timestamp format (easy to track)
- `v1.2.3` - Semantic versioning
- `feature-xyz-v1` - Feature-based versioning
- `git-commit-sha` - Git commit hash

### Step 3: Deploy with Helm

```bash
# Deploy to your namespace
helm upgrade freqtrade ./chart \
  -f chart/values-base.yaml \
  -f chart/values-binance-futures.yaml \
  --namespace binance-futures \
  --install

# Watch the rollout
kubectl rollout status deployment/freqtrade-binance-futures -n binance-futures
```

### Step 4: Verify the Deployment

```bash
# Check pod annotations
kubectl get pods -n binance-futures -o jsonpath='{.items[*].metadata.annotations.strategy\.version}'

# Check pod labels
kubectl get pods -n binance-futures --show-labels | grep strategy-version

# View logs to see strategy version
kubectl logs -n binance-futures deployment/freqtrade-binance-futures -f | grep "Bot Loop Start"
```

**Expected Log Output:**
```
2025-10-30 14:05:12 INFO - 🔄 Bot Loop Start - Strategy Version: 2025-10-30-14:00 - Time: 2025-10-30 14:05:12
```

## Automatic Rollout Triggers

The deployment will automatically trigger a rollout when:

1. ✅ **Strategy Version Changes** - `strategy_version` in values-base.yaml is modified
2. ✅ **Config Changes** - Any change in `config` section (detected via checksum)
3. ✅ **ConfigCreds Changes** - Any change in `configcreds` section (detected via checksum)
4. ✅ **Image Tag Changes** - Image tag is updated in values file

## CI/CD Integration

### Option A: Manual Version Update

```bash
# Edit values-base.yaml manually
vim chart/values-base.yaml
# Change: strategy_version: "2025-10-30-14:00"
# To:     strategy_version: "2025-10-30-15:30"

# Deploy
helm upgrade freqtrade ./chart \
  -f chart/values-base.yaml \
  -f chart/values-binance-futures.yaml \
  --namespace binance-futures
```

### Option B: Automated with Git Commit SHA

```bash
#!/bin/bash
# get-strategy-version.sh

STRATEGY_VERSION=$(git rev-parse --short HEAD)
echo "Deploying strategy version: ${STRATEGY_VERSION}"

helm upgrade freqtrade ./chart \
  -f chart/values-base.yaml \
  -f chart/values-binance-futures.yaml \
  --set configcreds.strategy_version="${STRATEGY_VERSION}" \
  --namespace binance-futures
```

### Option C: Automated with Timestamp

```bash
#!/bin/bash
# deploy-with-timestamp.sh

STRATEGY_VERSION=$(date +"%Y-%m-%d-%H:%M")
echo "Deploying strategy version: ${STRATEGY_VERSION}"

helm upgrade freqtrade ./chart \
  -f chart/values-base.yaml \
  -f chart/values-binance-futures.yaml \
  --set configcreds.strategy_version="${STRATEGY_VERSION}" \
  --namespace binance-futures
```

### Option D: Update values file with yq

```bash
#!/bin/bash
# update-and-deploy.sh

# Install yq if needed: brew install yq

STRATEGY_VERSION=$(date +"%Y-%m-%d-%H:%M")
echo "Updating strategy version to: ${STRATEGY_VERSION}"

# Update values-base.yaml
yq eval ".configcreds.strategy_version = \"${STRATEGY_VERSION}\"" -i chart/values-base.yaml

# Commit the change
git add chart/values-base.yaml
git commit -m "Update strategy version to ${STRATEGY_VERSION}"

# Deploy
helm upgrade freqtrade ./chart \
  -f chart/values-base.yaml \
  -f chart/values-binance-futures.yaml \
  --namespace binance-futures
```

## Troubleshooting

### Strategy Version Not Showing in Logs

**Problem:** Logs don't show strategy version
```bash
kubectl logs -n binance-futures deployment/freqtrade-binance-futures | grep "Bot Loop Start"
# No output
```

**Solution:**
1. Check if strategy has `bot_loop_start` method
2. Verify `strategy_version` is in configcreds
3. Ensure both config files are loaded in deployment:
   ```yaml
   --config /freqtrade/config/config-{{ .Release.Namespace }}.json
   --config /freqtrade/configcreds/configcreds-{{ .Release.Namespace }}.json
   ```

### Pods Not Restarting After Version Change

**Problem:** Changed `strategy_version` but pods didn't restart

**Solution:**
1. Verify annotation is in deployment template
2. Check if Helm upgrade was executed
3. Force recreation:
   ```bash
   kubectl rollout restart deployment/freqtrade-binance-futures -n binance-futures
   ```

### Version Shows as "unknown"

**Problem:** Logs show `Strategy Version: unknown`

**Solution:**
1. Check `values-base.yaml` has `strategy_version` defined
2. Verify ConfigMap was updated:
   ```bash
   kubectl get configmap freqtrade-config-creds-binance-futures -n binance-futures -o yaml | grep strategy_version
   ```
3. Re-deploy with Helm to update ConfigMap

## Best Practices

### 1. **Use Descriptive Version Names**
```yaml
# ✅ Good
strategy_version: "2025-10-30-14:00-added-rsi-divergence"
strategy_version: "v2.3.1-fixed-stoploss-bug"
strategy_version: "git-abc123f"

# ❌ Bad
strategy_version: "1"
strategy_version: "new"
strategy_version: "test"
```

### 2. **Always Update Version When Changing Strategy**
```bash
# Before making strategy changes
vim extra_strategies/MyStrategy.py

# After making changes - UPDATE VERSION
vim chart/values-base.yaml
# Change: strategy_version: "2025-10-30-14:00"
# To:     strategy_version: "2025-10-30-15:30"
```

### 3. **Document Major Changes**
```yaml
# In values-base.yaml, add comments for major versions
configcreds:
  # v2.0.0 - Major refactor: Added Santiment integration
  # v1.5.2 - Fixed custom_stoploss bug
  # v1.5.1 - Optimized RSI parameters
  strategy_version: "v2.0.0"
```

### 4. **Use Git Tags for Production Releases**
```bash
# Tag your strategy releases
git tag -a strategy-v2.0.0 -m "Strategy v2.0.0 - Santiment integration"
git push origin strategy-v2.0.0

# Deploy with tagged version
yq eval ".configcreds.strategy_version = \"v2.0.0\"" -i chart/values-base.yaml
helm upgrade freqtrade ./chart -f chart/values-base.yaml -f chart/values-binance-futures.yaml -n binance-futures
```

### 5. **Monitor Rollout Status**
```bash
# Watch deployment progress
kubectl rollout status deployment/freqtrade-binance-futures -n binance-futures

# Check if new version is running
kubectl logs -n binance-futures -l app=freqtrade-binance-futures --tail=100 | grep "Bot Loop Start"
```

## Quick Reference

### Check Current Version
```bash
kubectl get pods -n binance-futures -o jsonpath='{.items[0].metadata.annotations.strategy\.version}'
```

### Force Rollout
```bash
kubectl rollout restart deployment/freqtrade-binance-futures -n binance-futures
```

### View Version History
```bash
kubectl rollout history deployment/freqtrade-binance-futures -n binance-futures
```

### Rollback to Previous Version
```bash
kubectl rollout undo deployment/freqtrade-binance-futures -n binance-futures
```

## Summary

✅ **What Was Changed:**
1. Added `bot_loop_start()` method to all 5 strategies
2. Added `strategy_version` logging in each `bot_loop_start()`
3. Added pod annotations in `deployment.yaml` for strategy version
4. Added checksums for config changes
5. Updated `values-base.yaml` with clear instructions

✅ **How to Use:**
1. Update your strategy code
2. Increment `strategy_version` in `values-base.yaml`
3. Run `helm upgrade`
4. Kubernetes automatically creates new pods
5. Verify version in logs

✅ **Benefits:**
- 🚀 Automatic rollouts on strategy changes
- 📝 Version tracking in logs
- 🔄 Zero-downtime deployments
- ✅ Always pulls latest Docker image
- 📊 Easy to verify which version is running

---

**Need Help?**
Check logs: `kubectl logs -n binance-futures deployment/freqtrade-binance-futures -f | grep "Bot Loop Start"`

