# Kubernetes Services - Quick Reference

## Service Access Patterns

### Internal (ClusterIP)
```
http://freqtrade-clusterip-<namespace>.<namespace>.svc.cluster.local:<listen_port>
```

### External (NodePort)
```
http://<node-ip>:<nodePort>
```

### External (LoadBalancer)
```
http://<load-balancer-ip>:<listen_port>
```

## Quick Commands

### Deploy a bot with NodePort
```bash
helm install <release-name> ./chart \
  -f values-binance-futures.yaml \
  -f values-<bot>-creds.yaml \
  --namespace <namespace> \
  --create-namespace
```

### List all services
```bash
kubectl get svc --all-namespaces | grep freqtrade
```

### Get service details
```bash
kubectl describe svc freqtrade-clusterip-<namespace> -n <namespace>
```

### Test API endpoint
```bash
# Internal
kubectl run curl-test --image=curlimages/curl -i --tty --rm --restart=Never -- \
  curl http://freqtrade:password@freqtrade-clusterip-<namespace>.<namespace>.svc.cluster.local:8084/api/v1/ping

# External (NodePort)
curl http://freqtrade:password@<node-ip>:<nodePort>/api/v1/status
```

### Get NodePort
```bash
kubectl get svc freqtrade-nodeport-<namespace> -n <namespace> -o jsonpath='{.spec.ports[0].nodePort}'
```

### Get LoadBalancer IP
```bash
kubectl get svc freqtrade-loadbalancer-<namespace> -n <namespace> -o jsonpath='{.status.loadBalancer.ingress[0].ip}'
```

## Configuration Templates

### Enable NodePort
```yaml
kubernetes:
  nodePort: 32084  # Range: 30000-32767
```

### Enable LoadBalancer
```yaml
ingress:
  enabled: true
  type: LoadBalancer
  loadBalancerIP: "203.0.113.1"  # Optional
```

### API Configuration
```yaml
config:
  api_server:
    enabled: true
    listen_ip_address: 0.0.0.0
    listen_port: 8084
    username: freqtrade
    password: "your-secure-password"
```

## Common Port Assignments

| Bot Name              | Namespace              | NodePort | API Port |
|-----------------------|------------------------|----------|----------|
| bot-ssc-01            | bot-ssc-01             | 32381    | 8084     |
| bot-ssc-02            | bot-ssc-02             | 32382    | 8084     |
| multimetricstrategy   | multimetricstrategy    | 32392    | 8084     |
| bot-mssm-02           | bot-mssm-02            | 32372    | 8084     |

## Troubleshooting

### Service not found
```bash
kubectl get svc -n <namespace>
kubectl get endpoints -n <namespace>
```

### Check pod labels
```bash
kubectl get pods -n <namespace> --show-labels
```

### Port conflicts
```bash
kubectl get svc --all-namespaces -o json | \
  jq '.items[] | select(.spec.type=="NodePort") | {name:.metadata.name, nodePort:.spec.ports[0].nodePort}'
```

### View service logs
```bash
kubectl logs -n <namespace> -l app=freqtrade-<namespace> --tail=100 -f
```

## API Endpoints

### Common endpoints
- `/api/v1/ping` - Health check
- `/api/v1/status` - Bot status
- `/api/v1/balance` - Account balance
- `/api/v1/trades` - Active trades
- `/api/v1/profit` - Profit information
- `/api/v1/forceenter` - Force entry (POST)
- `/api/v1/forceexit` - Force exit (POST)

### Example API calls
```bash
# Get status
curl -u freqtrade:password http://<service-url>:8084/api/v1/status

# Get balance
curl -u freqtrade:password http://<service-url>:8084/api/v1/balance

# Force entry (POST)
curl -X POST -u freqtrade:password \
  -H "Content-Type: application/json" \
  -d '{"pair": "BTC/USDT:USDT", "side": "long"}' \
  http://<service-url>:8084/api/v1/forceenter
```

## Service Discovery

### From within a pod
```bash
# Using service name (recommended)
curl http://freqtrade-clusterip-bot-ssc-02.bot-ssc-02.svc.cluster.local:8084/api/v1/ping

# Using short name (same namespace only)
curl http://freqtrade-clusterip-bot-ssc-02:8084/api/v1/ping
```

### Environment variables
```bash
# Get all service environment variables in a pod
kubectl exec -it <pod-name> -n <namespace> -- env | grep SERVICE
```

## Security Best Practices

1. **Use ClusterIP for internal communication**
   ```yaml
   # Example: hedging bot calling spot bot
   spot_bot_api: "http://freqtrade:password@freqtrade-clusterip-bot-ssc-01.bot-ssc-01.svc.cluster.local:8084/api/v1/forceenter"
   ```

2. **Restrict NodePort access with NetworkPolicy**
   ```yaml
   apiVersion: networking.k8s.io/v1
   kind: NetworkPolicy
   metadata:
     name: restrict-nodeport
   spec:
     podSelector:
       matchLabels:
         app: freqtrade-<namespace>
     ingress:
     - from:
       - ipBlock:
           cidr: 10.0.0.0/8  # Only allow internal network
   ```

3. **Use strong passwords**
   ```yaml
   config:
     api_server:
       password: "$(openssl rand -base64 32)"
   ```

4. **Enable HTTPS with Ingress**
   ```yaml
   apiVersion: networking.k8s.io/v1
   kind: Ingress
   metadata:
     name: freqtrade-ingress
     annotations:
       cert-manager.io/cluster-issuer: "letsencrypt-prod"
   spec:
     tls:
     - hosts:
       - bot.example.com
       secretName: freqtrade-tls
   ```

## Upgrade Notes

### From old service config
```bash
# 1. Backup current configuration
kubectl get svc -A -o yaml > services-backup.yaml

# 2. Update Helm chart
helm upgrade <release-name> ./chart \
  -f values-binance-futures.yaml \
  -f values-<bot>-creds.yaml \
  --namespace <namespace>

# 3. Verify services
kubectl get svc -n <namespace>
```

### Update inter-bot URLs
```yaml
# Old format (if using direct pod IPs - not recommended)
spot_bot_api: "http://freqtrade:password@10.244.0.5:8084/api/v1/status"

# New format (using service names)
spot_bot_api: "http://freqtrade:password@freqtrade-clusterip-bot-ssc-01.bot-ssc-01.svc.cluster.local:8084/api/v1/status"
```

## Monitoring

### Watch service endpoints
```bash
kubectl get endpoints -n <namespace> -w
```

### Monitor service traffic
```bash
kubectl top pods -n <namespace>
```

### Service metrics (if metrics-server is installed)
```bash
kubectl get --raw /apis/metrics.k8s.io/v1beta1/namespaces/<namespace>/pods
```


