# Pairlist Quick Reference

## ✅ What Changed

**Replaced**: `StaticPairList` → `VolumePairList` + Quality Filters

**Files Updated:**
- ✅ `values-multimetricstrategy-creds.yaml`
- ✅ `values-bot-mssm-04-creds.yaml`

---

## 📊 Current Configuration

### VolumePairList
```yaml
- method: VolumePairList
  number_assets: 10          # Top 10 pairs by volume
  sort_key: quoteVolume      # Ranked by USDT volume
  refresh_period: 1800       # Update every 30 minutes
  lookback_days: 1           # Last 24 hours volume
```

**Selects**: Top 10 highest-volume trading pairs automatically

---

## 🛡️ Quality Filters Applied

| Filter | Purpose | Threshold |
|--------|---------|-----------|
| **AgeFilter** | Block new listings | > 10 days old |
| **PrecisionFilter** | Ensure compatibility | Auto |
| **PriceFilter** | Block cheap coins | > 1% of BTC price |
| **SpreadFilter** | Ensure liquidity | < 0.5% spread |
| **RangeStabilityFilter** | Block stablecoins | > 1% movement/3 days |

---

## 🎯 Expected Pairs

**Typical Selection:**
1. BTC/USDT:USDT (always)
2. ETH/USDT:USDT (always)
3-10. Varies: SOL, XRP, DOGE, ADA, AVAX, MATIC, DOT, LINK, etc.

**Updates**: Every 30 minutes based on volume changes

---

## ⚠️ API Limit Warning

**Current Setup:**
- 10 pairs × 4 metrics = 40 API calls per analysis
- 1-minute timeframe = ~57,600 calls/day

**Santiment Limit**: 1,000 calls/day (FREE tier)

**Solutions:**
1. **Reduce pairs**: Change `number_assets: 10` to `5-6`
2. **Upgrade Santiment**: Get paid plan
3. **Increase cache**: Already at 300s (5 min)

---

## 🔧 Quick Adjustments

### Fewer Pairs (Reduce API calls):
```yaml
number_assets: 5  # Only top 5 pairs
```

### More Pairs (More opportunities):
```yaml
number_assets: 15  # Top 15 pairs
```

### Faster Updates:
```yaml
refresh_period: 900  # Every 15 minutes
```

### Slower Updates:
```yaml
refresh_period: 3600  # Every hour
```

---

## 🚀 Benefits

✅ **Automatic** - No manual updates
✅ **Dynamic** - Adapts to market
✅ **Quality** - Only liquid pairs
✅ **Safe** - Filters risky coins
✅ **Optimal** - Always best pairs

---

## 📞 View Current Pairs

```bash
# Check what pairs are selected
freqtrade list-pairs --config your-config.yaml
```

Or check logs for:
```
Whitelist: ['BTC/USDT:USDT', 'ETH/USDT:USDT', 'SOL/USDT:USDT', ...]
```

---

**Status**: ✅ Ready to deploy with market-based pair selection!

