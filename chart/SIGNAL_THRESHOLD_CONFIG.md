# Signal Threshold Configuration for Helm Chart

## Overview

The `values-base.yaml` file now includes configurable signal thresholds that control how many signals are required before opening positions. This allows you to adjust trading frequency and quality directly from your Helm chart values.

## Configuration Location

All signal threshold parameters are in the `configcreds` section of `values-base.yaml`:

```yaml
configcreds:
  strategy_version: "2025-10-30-14:00"
  
  # Signal thresholds
  min_long_signals: 2
  min_short_signals: 2
  required_signals: 3
  min_long_score: 70
  min_short_score: 55
  min_long_score_hf: 55
  min_short_score_hf: 55
```

## Available Parameters

### Claudius Strategies (Count-Based)

| Parameter | Strategy | Default | Range | Description |
|-----------|----------|---------|-------|-------------|
| `min_long_signals` | All Claudius | 2 | 1-4 | Minimum bullish patterns for LONG entry |
| `min_short_signals` | All Claudius | 2 | 1-4 | Minimum bearish patterns for SHORT entry |
| `required_signals` | ClaudiusCryptoStrategy | 3 | 1-5 | Alternative threshold parameter |

**Applies to:**
- ClaudiusCryptoStrategy
- ClaudiusCryptoStrategyEnhanced
- ClaudiusCryptoStrategyEnhancedBinance

### MultiMetric Strategies (Score-Based)

| Parameter | Strategy | Default | Range | Description |
|-----------|----------|---------|-------|-------------|
| `min_long_score` | MultiMetricStrategy | 70 | 60-80 | Minimum score for LONG entry |
| `min_short_score` | MultiMetricStrategy | 55 | 50-70 | Minimum score for SHORT entry |
| `min_long_score_hf` | MultiMetricStrategyHF | 55 | 50-75 | Minimum score for LONG entry (HF) |
| `min_short_score_hf` | MultiMetricStrategyHF | 55 | 50-75 | Minimum score for SHORT entry (HF) |

**Applies to:**
- MultiMetricStrategy
- MultiMetricStrategyHF

## Preset Configurations

### Conservative Mode (Fewer, Higher Quality Trades)

```yaml
configcreds:
  # Claudius strategies
  min_long_signals: 3
  min_short_signals: 3
  
  # MultiMetric strategies
  min_long_score: 75
  min_short_score: 65
  min_long_score_hf: 70
  min_short_score_hf: 70
```

**Expected Result:**
- Lower trade frequency
- Higher quality signals
- Better win rate
- Fewer false signals

### Balanced Mode (Default)

```yaml
configcreds:
  # Claudius strategies
  min_long_signals: 2
  min_short_signals: 2
  
  # MultiMetric strategies
  min_long_score: 70
  min_short_score: 55
  min_long_score_hf: 55
  min_short_score_hf: 55
```

**Expected Result:**
- Moderate trade frequency
- Good signal quality
- Balanced risk/reward
- **Recommended starting point**

### Aggressive Mode (More Trades, Lower Quality)

```yaml
configcreds:
  # Claudius strategies
  min_long_signals: 1
  min_short_signals: 1
  
  # MultiMetric strategies
  min_long_score: 50
  min_short_score: 50
  min_long_score_hf: 50
  min_short_score_hf: 50
```

**Expected Result:**
- Higher trade frequency
- Lower quality signals
- More false positives
- Higher risk

## How to Apply Changes

### Method 1: Edit values-base.yaml

```bash
# Edit the values file
nano chart/values-base.yaml

# Modify the signal thresholds
configcreds:
  min_long_signals: 3  # Changed from 2 to 3 for conservative mode
  min_short_signals: 3

# Deploy with Helm
helm upgrade freqtrade-bot ./chart -f chart/values-base.yaml
```

### Method 2: Override with Custom Values File

```bash
# Create a custom values file
cat > chart/values-custom.yaml <<EOF
configcreds:
  min_long_signals: 3
  min_short_signals: 3
  min_long_score: 75
  min_short_score: 65
EOF

# Deploy with both values files (custom overrides base)
helm upgrade freqtrade-bot ./chart \
  -f chart/values-base.yaml \
  -f chart/values-custom.yaml
```

### Method 3: Command-Line Override

```bash
# Override specific values on the command line
helm upgrade freqtrade-bot ./chart \
  -f chart/values-base.yaml \
  --set configcreds.min_long_signals=3 \
  --set configcreds.min_short_signals=3
```

## Verification

After deployment, check the pod logs to verify the configuration was loaded:

```bash
# Get pod name
kubectl get pods -n <namespace>

# Check logs for configuration confirmation
kubectl logs <pod-name> -n <namespace> | grep "overridden from config"
```

**Expected output for Claudius strategies:**
```
INFO - min_long_signals overridden from config: 3
INFO - min_short_signals overridden from config: 3
```

**Expected output for MultiMetric strategies:**
```
INFO - min_long_score overridden from config: 75
INFO - min_short_score overridden from config: 65
```

## Strategy-Specific Configuration

### For ClaudiusCryptoStrategy

```yaml
configcreds:
  min_long_signals: 2
  min_short_signals: 2
  required_signals: 3
```

### For ClaudiusCryptoStrategyEnhanced

```yaml
configcreds:
  min_long_signals: 2
  min_short_signals: 2
```

### For ClaudiusCryptoStrategyEnhancedBinance

```yaml
configcreds:
  min_long_signals: 2
  min_short_signals: 2
```

### For MultiMetricStrategy

```yaml
configcreds:
  min_long_score: 70
  min_short_score: 55
```

### For MultiMetricStrategyHF

```yaml
configcreds:
  min_long_score_hf: 55
  min_short_score_hf: 55
```

## Tuning Guide

### Getting Too Few Signals?

**Claudius Strategies:**
```yaml
# Decrease by 1
min_long_signals: 1   # Was 2
min_short_signals: 1  # Was 2
```

**MultiMetric Strategies:**
```yaml
# Decrease by 5-10
min_long_score: 60    # Was 70
min_short_score: 50   # Was 55
```

### Getting Too Many Low-Quality Signals?

**Claudius Strategies:**
```yaml
# Increase by 1
min_long_signals: 3   # Was 2
min_short_signals: 3  # Was 2
```

**MultiMetric Strategies:**
```yaml
# Increase by 5-10
min_long_score: 75    # Was 70
min_short_score: 60   # Was 55
```

## Integration with Deployment Scripts

If you're using deployment scripts, you can inject these values:

```bash
#!/bin/bash
# deploy-with-thresholds.sh

THRESHOLD_MODE=${1:-balanced}  # conservative, balanced, or aggressive

case $THRESHOLD_MODE in
  conservative)
    MIN_LONG=3
    MIN_SHORT=3
    LONG_SCORE=75
    SHORT_SCORE=65
    ;;
  balanced)
    MIN_LONG=2
    MIN_SHORT=2
    LONG_SCORE=70
    SHORT_SCORE=55
    ;;
  aggressive)
    MIN_LONG=1
    MIN_SHORT=1
    LONG_SCORE=50
    SHORT_SCORE=50
    ;;
esac

helm upgrade freqtrade-bot ./chart \
  -f chart/values-base.yaml \
  --set configcreds.min_long_signals=$MIN_LONG \
  --set configcreds.min_short_signals=$MIN_SHORT \
  --set configcreds.min_long_score=$LONG_SCORE \
  --set configcreds.min_short_score=$SHORT_SCORE
```

Usage:
```bash
./deploy-with-thresholds.sh conservative
./deploy-with-thresholds.sh balanced
./deploy-with-thresholds.sh aggressive
```

## Rolling Updates

When changing signal thresholds, the pod will need to be restarted:

```bash
# Update values
nano chart/values-base.yaml

# Apply changes (will trigger pod restart)
helm upgrade freqtrade-bot ./chart -f chart/values-base.yaml

# Watch rollout
kubectl rollout status deployment/freqtrade-bot -n <namespace>
```

## Best Practices

1. **Start Conservative**: Begin with higher thresholds and lower them if needed
2. **Monitor for 24-48h**: Give the bot time to generate signals
3. **Backtest First**: Test threshold changes with backtesting before live deployment
4. **Document Changes**: Track which thresholds work best in different market conditions
5. **Version Control**: Keep your values files in git to track configuration history
6. **Gradual Changes**: Adjust thresholds by 1 step at a time, not dramatic jumps
7. **Update strategy_version**: Increment `strategy_version` when changing thresholds

## Troubleshooting

### Configuration Not Applied

**Check 1: Pod Restart**
```bash
# Delete pod to force restart
kubectl delete pod <pod-name> -n <namespace>
```

**Check 2: ConfigMap**
```bash
# Check if ConfigMap has the new values
kubectl get configmap freqtrade-config -n <namespace> -o yaml
```

**Check 3: Logs**
```bash
# Check for errors in logs
kubectl logs <pod-name> -n <namespace> | grep -i error
```

### Values Not Taking Effect

Ensure your strategy is reading from `strategy_config`:
```python
# In strategy __init__
strategy_config = config.get('strategy_config', {})
if 'min_long_signals' in strategy_config:
    self.min_long_signals.value = strategy_config['min_long_signals']
```

## Related Documentation

- `../extra_strategies/CONFIG_FILES_GUIDE.md` - Full configuration guide
- `../extra_strategies/README.md` - Strategy overview
- `../extra_strategies/QUICK_CONFIG_REFERENCE.md` - Quick reference
- `values-base.yaml` - The values file itself

## Questions?

For issues with Helm deployment:
1. Check pod logs for configuration loading
2. Verify ConfigMap contains correct values
3. Ensure pod has been restarted after changes
4. Check that strategy version was incremented

