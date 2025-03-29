apply:
	cd chart; helm template -f values-base.yaml -f values-binance-futures.yaml -f values-bot-ananda-creds.yaml . > /tmp/bot-ananda.yaml
	kubectl apply -f /tmp/bot-ananda.yaml

diff:
	cd chart; helm template -f values-base.yaml -f values-binance-futures.yaml -f values-bot-alwaysbuy-creds.yaml . > /tmp/bot-always.yaml
	cd chart; helm template -f values-base.yaml -f values-binance-futures.yaml -f values-bot-ananda-creds.yaml . > /tmp/bot-ananda.yaml
	diff /tmp/bot-always.yaml /tmp/bot-ananda.yaml

