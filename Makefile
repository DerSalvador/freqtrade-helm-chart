manifest-test:
	cd chart; helm template -f values-base.yaml -f values-binance-futures.yaml -f values-bot-ananda-creds.yaml -f values-bot-nisham-test.yaml . > /tmp/bot-ananda.yaml

manifest:
	cd chart; helm template -f values-base.yaml -f values-binance-futures.yaml -f values-bot-ananda-creds.yaml . > /tmp/bot-ananda.yaml

apply: manifest-test
	kubectl apply -f /tmp/bot-ananda.yaml

diff:
	cd chart; helm template -f values-base.yaml -f values-binance-futures.yaml -f values-bot-alwaysbuy-creds.yaml . > /tmp/bot-always.yaml
	cd chart; helm template -f values-base.yaml -f values-binance-futures.yaml -f values-bot-ananda-creds.yaml . > /tmp/bot-ananda.yaml
	diff /tmp/bot-always.yaml /tmp/bot-ananda.yaml
# 	

copy-from:
	cp ~/workspace/personal/crypto/AnandaStrategySplit.py /tmp/AnandaStrategySplit.py

NAMESPACE:=$(shell kubectl config view --minify -o jsonpath='{.contexts[0].context.namespace}')
POD:=$(shell kubectl get pods -l app=freqtrade-$(NAMESPACE) -o jsonpath="{.items[0].metadata.name}")
FILE:=AnandaStrategySplit
download:
	kubectl cp $(POD):/freqtrade/user_data/strategies/$(FILE).py /tmp/$(FILE).py -c freqtrade

upload: copy-from
	kubectl cp /tmp/$(FILE).py $(POD):/freqtrade/user_data/strategies/$(FILE).py -c freqtrade
