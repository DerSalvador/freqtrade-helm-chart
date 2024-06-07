kubectl --context=gke_vaulted-gift-406223_europe-west1-b_private-cluster-3 -n bot-mssm-06 exec -it pod/freqtrade-bot-mssm-06-6956d6fbd8-9lpbg -c freqtrade -- cat /freqtrade/user_data/strategies/FBB_CryptoFrog.json tft_utils.py
{
  "strategy_name": "FBB_CryptoFrog",
  "params": {
    "roi": {
      "0": 100.0
    },
    "stoploss": {
      "stoploss": -0.085
    },
    "trailing": {
      "trailing_stop": false,
      "trailing_stop_positive": null,
      "trailing_stop_positive_offset": 0.0,
      "trailing_only_offset_is_reached": false
    },
    "buy": {
      "buy_bb_gain": 0.06,
      "buy_fisher_wr": -0.48,
      "buy_force_fisher_wr": -0.88
    },
    "sell": {
      "cstp_bail_how": "time",
      "cstp_bail_roc": -0.03,
      "cstp_bail_time": 969,
      "cstp_threshold": -0.042,
      "droi_pullback": true,
      "droi_pullback_amount": 0.005,
      "droi_pullback_respect_table": false,
      "droi_trend_type": "any"
    },
    "protection": {}
  },
  "ft_stratparam_v": 1,
  "export_time": "2022-02-15 08:00:39.633845+00:00"
}cat: tft_utils.py: No such file or directory
