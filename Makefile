apply:
	cd chart; helm template -f values-base.yaml -f values-binance-futures.yaml -f values-bot-ananda-creds.yaml . > /tmp/bot-ananda.yaml
	kubectl apply -f /tmp/bot-ananda.yaml

diff:
	cd chart; helm template -f values-base.yaml -f values-binance-futures.yaml -f values-bot-alwaysbuy-creds.yaml . > /tmp/bot-always.yaml
	cd chart; helm template -f values-base.yaml -f values-binance-futures.yaml -f values-bot-ananda-creds.yaml . > /tmp/bot-ananda.yaml
	diff /tmp/bot-always.yaml /tmp/bot-ananda.yaml
# 	
NAMESPACE:=$(shell kubectl config view --minify -o jsonpath='{.contexts[0].context.namespace}')
POD:=$(shell kubectl get pods -l app=freqtrade-$(NAMESPACE) -o jsonpath="{.items[0].metadata.name}")
download:
	kubectl cp $(POD):/freqtrade/user_data/strategies/$(FILE).py /tmp/$(FILE).py -c freqtrade
