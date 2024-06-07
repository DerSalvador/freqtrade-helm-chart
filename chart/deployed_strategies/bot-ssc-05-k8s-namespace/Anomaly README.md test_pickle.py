kubectl --context=gke_vaulted-gift-406223_europe-west1-b_private-cluster-3 -n bot-ssc-05 exec -it pod/freqtrade-bot-ssc-05-8567c779fd-t948m -c freqtrade -- cat /freqtrade/user_data/strategies/Anomaly README.md test_pickle.py
cat: /freqtrade/user_data/strategies/Anomaly: Is a directory
cat: README.md: No such file or directory
cat: test_pickle.py: No such file or directory
