# Bot MSSM-02 Service Configuration

## Summary

Successfully configured Kubernetes services for the `bot-mssm-02` deployment with support for multiple access patterns.

## Configuration Added

**File:** `chart/values-bot-mssm-02-creds.yaml`

### Services Created

#### 1. ClusterIP Service (Always Active) ✅
```yaml
Service Name: freqtrade-clusterip-bot-mssm-02
Namespace: bot-mssm-02
Internal DNS: freqtrade-clusterip-bot-mssm-02.bot-mssm-02.svc.cluster.local
Port: 8084
```

**Use Case:** Internal cluster communication, bot-to-bot communication

**Access from within cluster:**
```bash
curl http://freqtrade:password@freqtrade-clusterip-bot-mssm-02.bot-mssm-02.svc.cluster.local:8084/api/v1/status
```

#### 2. NodePort Service (Active) ✅
```yaml
Service Name: freqtrade-nodeport-bot-mssm-02
Namespace: bot-mssm-02
NodePort: 32372
Port: 8084
```

**Use Case:** Direct external access without cloud load balancer

**Access from outside cluster:**
```bash
# Get node IP
kubectl get nodes -o wide

# Access the API
curl http://freqtrade:password@<node-ip>:32372/api/v1/status
```

#### 3. LoadBalancer Service (Optional) ✅
```yaml
Service Name: freqtrade-loadbalancer-bot-mssm-02
Namespace: bot-mssm-02
Type: LoadBalancer
Port: 8084
Status: Disabled by default (set ingress.enabled: true to activate)
```

**Use Case:** Production cloud deployments with cloud provider load balancers

**To Enable:**
```yaml
# In values-bot-mssm-02-creds.yaml
ingress:
  enabled: true  # Change this to true
  type: LoadBalancer
```

**Access after enabling:**
```bash
# Get LoadBalancer IP
kubectl get svc freqtrade-loadbalancer-bot-mssm-02 -n bot-mssm-02

# Access the API
curl http://freqtrade:password@<load-balancer-ip>:8084/api/v1/status
```

## Current Configuration

```yaml
kubernetes:
  nodePort: 32372  # NodePort for external access

ingress:
  enabled: false  # Set to true to enable LoadBalancer
  type: LoadBalancer
  annotations: {}
    # Cloud provider annotations:
    # GCP:
    #  cloud.google.com/load-balancer-type: "Internal"
    #  networking.gke.io/load-balancer-type: "Internal"
    # AWS:
    #  service.beta.kubernetes.io/aws-load-balancer-type: "nlb"
    #  service.beta.kubernetes.io/aws-load-balancer-internal: "true"
    # Azure:
    #  service.beta.kubernetes.io/azure-load-balancer-internal: "true"
  loadBalancerIP: ""  # Optional static IP
```

## Bot Details

- **Bot Name:** multimetricstrategy (bot-mssm-02)
- **Strategy:** MultiMetricStrategyHF
- **Trading Mode:** Futures
- **Margin Mode:** Isolated
- **Pair:** ETH/USDT:USDT
- **Namespace:** bot-mssm-02

## Deployment

### Standard Deployment (ClusterIP + NodePort)
```bash
helm install bot-mssm-02 ./chart \
  -f values-binance-futures.yaml \
  -f values-bot-mssm-02-creds.yaml \
  --namespace bot-mssm-02 \
  --create-namespace
```

**Services created:**
- ✅ `freqtrade-clusterip-bot-mssm-02` (ClusterIP)
- ✅ `freqtrade-nodeport-bot-mssm-02` (NodePort: 32372)

### Deployment with LoadBalancer
```bash
helm install bot-mssm-02 ./chart \
  -f values-binance-futures.yaml \
  -f values-bot-mssm-02-creds.yaml \
  --set ingress.enabled=true \
  --namespace bot-mssm-02 \
  --create-namespace
```

**Services created:**
- ✅ `freqtrade-clusterip-bot-mssm-02` (ClusterIP)
- ✅ `freqtrade-nodeport-bot-mssm-02` (NodePort: 32372)
- ✅ `freqtrade-loadbalancer-bot-mssm-02` (LoadBalancer)

### Upgrade Existing Deployment
```bash
helm upgrade bot-mssm-02 ./chart \
  -f values-binance-futures.yaml \
  -f values-bot-mssm-02-creds.yaml \
  --namespace bot-mssm-02
```

## Validation

### Validate Services
```bash
# Run validation script
./validate-services.sh bot-mssm-02

# Or with verbose output
./validate-services.sh bot-mssm-02 --verbose
```

### Check Services Manually
```bash
# List all services
kubectl get svc -n bot-mssm-02

# Describe ClusterIP service
kubectl describe svc freqtrade-clusterip-bot-mssm-02 -n bot-mssm-02

# Describe NodePort service
kubectl describe svc freqtrade-nodeport-bot-mssm-02 -n bot-mssm-02

# Check endpoints
kubectl get endpoints -n bot-mssm-02

# Check pod status
kubectl get pods -n bot-mssm-02
```

## Testing API Access

### Internal Access (ClusterIP)
```bash
# Create a test pod
kubectl run curl-test --image=curlimages/curl -i --tty --rm --restart=Never -n bot-mssm-02 -- \
  curl http://freqtrade:password@freqtrade-clusterip-bot-mssm-02.bot-mssm-02.svc.cluster.local:8084/api/v1/ping
```

### External Access (NodePort)
```bash
# Get node IP
NODE_IP=$(kubectl get nodes -o jsonpath='{.items[0].status.addresses[?(@.type=="ExternalIP")].address}')
# Or use internal IP if external not available
NODE_IP=$(kubectl get nodes -o jsonpath='{.items[0].status.addresses[?(@.type=="InternalIP")].address}')

# Test API
curl http://freqtrade:password@${NODE_IP}:32372/api/v1/ping
curl http://freqtrade:password@${NODE_IP}:32372/api/v1/status
curl http://freqtrade:password@${NODE_IP}:32372/api/v1/balance
```

### External Access (LoadBalancer - if enabled)
```bash
# Get LoadBalancer IP
LB_IP=$(kubectl get svc freqtrade-loadbalancer-bot-mssm-02 -n bot-mssm-02 -o jsonpath='{.status.loadBalancer.ingress[0].ip}')

# Test API
curl http://freqtrade:password@${LB_IP}:8084/api/v1/ping
```

## Service Architecture

```
┌─────────────────────────────────────────────────────────────┐
│              Kubernetes Cluster (bot-mssm-02)               │
│                                                             │
│  ┌────────────────────────────────────────────────────┐    │
│  │  Pod: freqtrade-bot-mssm-02                        │    │
│  │  Strategy: MultiMetricStrategyHF                   │    │
│  │  Container Port: 8084                              │    │
│  └──────────────────▲───────────────────────────────┘     │
│                     │                                      │
│                     │                                      │
│       ┌─────────────┼────────────────┐                     │
│       │             │                │                     │
│  ┌────▼─────┐  ┌────▼──────┐  ┌─────▼────────┐           │
│  │ClusterIP │  │ NodePort  │  │LoadBalancer  │           │
│  │  :8084   │  │ :32372    │  │   :8084      │           │
│  │(Internal)│  │(External) │  │  (External)  │           │
│  └──────────┘  └───────────┘  └──────────────┘           │
│                     │                │                     │
└─────────────────────┼────────────────┼─────────────────────┘
                      │                │
                      ▼                ▼
                ┌──────────┐    ┌─────────────┐
                │ Node IP  │    │Cloud LoadLB │
                │ :32372   │    │    :8084    │
                └──────────┘    └─────────────┘
```

## Inter-Bot Communication

If other bots need to communicate with bot-mssm-02, use the ClusterIP service:

```yaml
# In another bot's configuration
configcreds:
  bot_name: other-bot
  dersalvador:
    api_endpoints:
      bot_mssm_02_api: "http://freqtrade:password@freqtrade-clusterip-bot-mssm-02.bot-mssm-02.svc.cluster.local:8084/api/v1/status"
      bot_mssm_02_forceenter: "http://freqtrade:password@freqtrade-clusterip-bot-mssm-02.bot-mssm-02.svc.cluster.local:8084/api/v1/forceenter"
```

## Security Notes

1. **Use ClusterIP for internal communication** - More secure than exposing via NodePort
2. **NodePort is already enabled** (32372) - Use for development/testing access
3. **Enable LoadBalancer for production** - Better reliability and security
4. **Protect API credentials** - Use strong passwords in `api_server.password`
5. **Consider NetworkPolicies** - Restrict traffic to only necessary sources

## Port Allocation

| Bot              | Namespace      | NodePort | API Port | Status |
|------------------|----------------|----------|----------|--------|
| bot-ssc-01       | bot-ssc-01     | 32381    | 8084     | Active |
| **bot-mssm-02**  | **bot-mssm-02**| **32372**| **8084** |**Active**|
| bot-ssc-02       | bot-ssc-02     | 32382    | 8084     | Active |
| multimetric...   | multimetric... | 32392    | 8084     | Active |

## Troubleshooting

### Service not accessible
```bash
# Check if services exist
kubectl get svc -n bot-mssm-02

# Check if pods are running
kubectl get pods -n bot-mssm-02

# Check service endpoints
kubectl get endpoints -n bot-mssm-02

# Check pod logs
kubectl logs -n bot-mssm-02 -l app=freqtrade-bot-mssm-02 --tail=50
```

### NodePort not accessible
```bash
# Check if NodePort service exists
kubectl get svc freqtrade-nodeport-bot-mssm-02 -n bot-mssm-02

# Verify the port is correct
kubectl get svc freqtrade-nodeport-bot-mssm-02 -n bot-mssm-02 -o jsonpath='{.spec.ports[0].nodePort}'

# Check for firewall rules blocking port 32372
```

### LoadBalancer pending
```bash
# Check LoadBalancer status
kubectl get svc freqtrade-loadbalancer-bot-mssm-02 -n bot-mssm-02

# Describe to see events
kubectl describe svc freqtrade-loadbalancer-bot-mssm-02 -n bot-mssm-02

# Note: LoadBalancer IP assignment can take 2-5 minutes
```

## Additional Resources

- **Full Documentation:** `/freqtrade-helm-chart/KUBERNETES_SERVICES_README.md`
- **Quick Reference:** `/freqtrade-helm-chart/SERVICE_QUICK_REFERENCE.md`
- **Implementation Summary:** `/freqtrade-helm-chart/SERVICE_IMPLEMENTATION_SUMMARY.md`
- **Examples:** `/freqtrade-helm-chart/chart/values-service-examples.yaml`
- **Validation Script:** `./validate-services.sh`

## Status

✅ **Configuration Complete**
✅ **Templates Validated**
✅ **Ready for Deployment**

---

**Bot:** bot-mssm-02  
**Strategy:** MultiMetricStrategyHF  
**Namespace:** bot-mssm-02  
**NodePort:** 32372  
**Configuration File:** `values-bot-mssm-02-creds.yaml`  
**Date:** October 13, 2025  


