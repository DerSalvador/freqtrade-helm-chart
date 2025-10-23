# Kubernetes Services Configuration Guide

## Overview

This Helm chart now supports multiple service types to expose your Freqtrade bot deployments. Each bot deployment can be accessed through different service types depending on your requirements.

## Service Types

### 1. ClusterIP Service (Always Created)

**Service Name:** `freqtrade-clusterip-<namespace>`

This is the default service type created for every bot deployment. It allows internal cluster communication between pods.

**Use Case:**
- Inter-bot communication (e.g., hedging strategies)
- Internal monitoring tools
- Service mesh communication

**Access URL Format:**
```
http://freqtrade-clusterip-<namespace>.<namespace>.svc.cluster.local:<listen_port>
```

**Example:**
```bash
# Access bot-ssc-02 from another pod in the cluster
curl http://freqtrade:password@freqtrade-clusterip-bot-ssc-02.bot-ssc-02.svc.cluster.local:8084/api/v1/status
```

### 2. NodePort Service (Optional)

**Service Name:** `freqtrade-nodeport-<namespace>`

This service type exposes the bot on each node's IP at a static port. Enabled when `kubernetes.nodePort` is defined in your values file.

**Configuration:**
```yaml
kubernetes:
  nodePort: 32084  # Must be in range 30000-32767
```

**Use Case:**
- Direct external access without load balancer
- Development/testing environments
- Cost-effective external access

**Access URL Format:**
```
http://<node-ip>:<nodePort>
```

**Example:**
```bash
# Access from outside the cluster
curl http://freqtrade:password@192.168.1.100:32084/api/v1/status
```

### 3. LoadBalancer Service (Optional)

**Service Name:** `freqtrade-loadbalancer-<namespace>`

This service type provisions an external load balancer (cloud provider specific). Enabled when `ingress.enabled: true` and `ingress.type: LoadBalancer`.

**Configuration:**
```yaml
ingress:
  enabled: true
  type: LoadBalancer
  annotations:
    service.beta.kubernetes.io/aws-load-balancer-type: "nlb"  # AWS example
  loadBalancerIP: "203.0.113.1"  # Optional static IP
```

**Use Case:**
- Production deployments
- High availability requirements
- Cloud-native deployments (AWS, GCP, Azure)

**Access URL Format:**
```
http://<load-balancer-ip>:<listen_port>
```

## Configuration Examples

### Example 1: Basic Deployment with ClusterIP Only

**values-basic-bot.yaml:**
```yaml
config:
  api_server:
    listen_port: 8084
    username: freqtrade
    password: "secure_password"

# No kubernetes or ingress section needed
# ClusterIP service will be created automatically
```

**Access:**
- Internal only: `http://freqtrade-clusterip-basic-bot.basic-bot.svc.cluster.local:8084`

### Example 2: Deployment with NodePort

**values-bot-with-nodeport.yaml:**
```yaml
config:
  api_server:
    listen_port: 8084
    username: freqtrade
    password: "secure_password"

kubernetes:
  nodePort: 32084
```

**Services Created:**
1. `freqtrade-clusterip-bot-with-nodeport` (ClusterIP)
2. `freqtrade-nodeport-bot-with-nodeport` (NodePort: 32084)

**Access:**
- Internal: `http://freqtrade-clusterip-bot-with-nodeport.bot-with-nodeport.svc.cluster.local:8084`
- External: `http://<node-ip>:32084`

### Example 3: Deployment with LoadBalancer

**values-production-bot.yaml:**
```yaml
config:
  api_server:
    listen_port: 8084
    username: freqtrade
    password: "secure_password"

ingress:
  enabled: true
  type: LoadBalancer
  annotations:
    service.beta.kubernetes.io/aws-load-balancer-type: "nlb"
    service.beta.kubernetes.io/aws-load-balancer-cross-zone-load-balancing-enabled: "true"
  loadBalancerIP: "203.0.113.1"  # Optional
```

**Services Created:**
1. `freqtrade-clusterip-production-bot` (ClusterIP)
2. `freqtrade-loadbalancer-production-bot` (LoadBalancer)

**Access:**
- Internal: `http://freqtrade-clusterip-production-bot.production-bot.svc.cluster.local:8084`
- External: `http://203.0.113.1:8084` (or assigned LB IP)

### Example 4: Multi-Bot Hedging Strategy

**values-spot-bot.yaml:**
```yaml
configcreds:
  bot_name: bot-ssc-01

config:
  api_server:
    listen_port: 8084

kubernetes:
  nodePort: 32381
```

**values-futures-bot.yaml:**
```yaml
configcreds:
  bot_name: bot-ssc-02
  dersalvador:
    hedging:
      spot_bot_api_status: "http://freqtrade:password@freqtrade-clusterip-bot-ssc-01.bot-ssc-01.svc.cluster.local:8084/api/v1/status"
      spot_bot_api_forceenter: "http://freqtrade:password@freqtrade-clusterip-bot-ssc-01.bot-ssc-01.svc.cluster.local:8084/api/v1/forceenter"

config:
  api_server:
    listen_port: 8084

kubernetes:
  nodePort: 32382
```

**Deployment:**
```bash
# Deploy spot bot
helm install bot-ssc-01 ./chart -f values-binance-futures.yaml -f values-spot-bot.yaml --namespace bot-ssc-01 --create-namespace

# Deploy futures bot (hedger)
helm install bot-ssc-02 ./chart -f values-binance-futures.yaml -f values-futures-bot.yaml --namespace bot-ssc-02 --create-namespace
```

**Services Created:**
- `freqtrade-clusterip-bot-ssc-01` in namespace `bot-ssc-01`
- `freqtrade-nodeport-bot-ssc-01` with NodePort 32381
- `freqtrade-clusterip-bot-ssc-02` in namespace `bot-ssc-02`
- `freqtrade-nodeport-bot-ssc-02` with NodePort 32382

## Port Configuration

The service port is controlled by the `config.api_server.listen_port` value in your configuration:

```yaml
config:
  api_server:
    enabled: true
    listen_ip_address: 0.0.0.0
    listen_port: 8084  # This port is used by all services
    username: freqtrade
    password: "secure_password"
```

All service types (ClusterIP, NodePort, LoadBalancer) will use this port as their `port` and `targetPort: api`.

## Deployment Commands

### List all services
```bash
kubectl get services --all-namespaces -l service-type=api
```

### Get service details for a specific bot
```bash
kubectl get service -n bot-ssc-02
kubectl describe service freqtrade-clusterip-bot-ssc-02 -n bot-ssc-02
```

### Test API access from within cluster
```bash
# Create a test pod
kubectl run curl-test --image=curlimages/curl -i --tty --rm --restart=Never -- sh

# Inside the pod, test the service
curl http://freqtrade:password@freqtrade-clusterip-bot-ssc-02.bot-ssc-02.svc.cluster.local:8084/api/v1/ping
```

### Test API access via NodePort
```bash
# Get node IP
kubectl get nodes -o wide

# Access the API
curl http://freqtrade:password@<node-ip>:32382/api/v1/status
```

### Get LoadBalancer external IP
```bash
kubectl get service freqtrade-loadbalancer-<namespace> -n <namespace>
```

## Security Considerations

1. **Authentication**: Always use strong passwords in `api_server.password`
2. **Network Policies**: Consider implementing Kubernetes Network Policies to restrict access
3. **TLS/SSL**: For production, consider adding an Ingress with TLS termination
4. **NodePort Range**: Ensure NodePort values don't conflict across deployments
5. **Internal Communication**: Use ClusterIP services for inter-bot communication to avoid external exposure

## Troubleshooting

### Service not accessible

```bash
# Check if service exists
kubectl get service -n <namespace>

# Check service endpoints
kubectl get endpoints -n <namespace>

# Check if pods are running
kubectl get pods -n <namespace>

# Check service selector matches pod labels
kubectl get pods -n <namespace> --show-labels
```

### Port conflicts

```bash
# List all NodePort services
kubectl get services --all-namespaces -o json | jq '.items[] | select(.spec.type=="NodePort") | {name:.metadata.name, namespace:.metadata.namespace, nodePort:.spec.ports[0].nodePort}'
```

### API authentication issues

```bash
# Test without authentication
curl http://<service-url>:<port>/api/v1/ping

# Verify credentials
kubectl get configmap freqtrade-config-<namespace> -n <namespace> -o yaml | grep -A5 api_server
```

## Migration Guide

If you're migrating from the old service configuration:

**Old (single LoadBalancer for all bots):**
```yaml
spec:
  type: LoadBalancer
  selector:
    app: freqtrade-{{ .Release.Namespace }}
```

**New (multiple service types per bot):**
```yaml
# ClusterIP (always created)
# NodePort (optional, when kubernetes.nodePort is set)
# LoadBalancer (optional, when ingress.enabled and ingress.type=LoadBalancer)
```

**Action Required:**
1. Review your values files
2. Add `kubernetes.nodePort` if you need external access via NodePort
3. Update any inter-bot communication URLs to use the new ClusterIP service names
4. Test connectivity after deployment

## Reference

### Service Naming Convention

| Service Type  | Name Pattern                          | Example                                   |
|---------------|---------------------------------------|-------------------------------------------|
| ClusterIP     | `freqtrade-clusterip-<namespace>`     | `freqtrade-clusterip-bot-ssc-02`         |
| NodePort      | `freqtrade-nodeport-<namespace>`      | `freqtrade-nodeport-bot-ssc-02`          |
| LoadBalancer  | `freqtrade-loadbalancer-<namespace>`  | `freqtrade-loadbalancer-production-bot`  |

### Labels

All services include standard labels:
```yaml
labels:
  app: freqtrade-<service-type>-<namespace>
  service-type: api|external|loadbalancer
```

### Selectors

All services use the same pod selector:
```yaml
selector:
  app: freqtrade-<namespace>
```

This matches the labels on the Deployment pods.


