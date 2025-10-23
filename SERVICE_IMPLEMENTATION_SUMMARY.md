# Kubernetes Services Implementation Summary

## Overview

This document summarizes the implementation of Kubernetes services for Freqtrade bot deployments. The new service configuration provides flexible access patterns for bots, supporting internal cluster communication, NodePort external access, and LoadBalancer cloud-native deployments.

## Changes Made

### 1. Enhanced Service Template (`chart/templates/service.yaml`)

**Previous Implementation:**
- Single LoadBalancer service for all deployments
- No namespace isolation
- Limited configuration options

**New Implementation:**
- **ClusterIP Service** (always created): For internal cluster communication
- **NodePort Service** (optional): For direct external access when `kubernetes.nodePort` is defined
- **LoadBalancer Service** (optional): For cloud-native external access when `ingress.enabled` and `ingress.type: LoadBalancer`

**Key Features:**
- Namespace-aware service names: `freqtrade-<type>-<namespace>`
- Proper service discovery for inter-bot communication
- Flexible access patterns based on deployment requirements
- No port conflicts between different bot deployments

### 2. Updated Values Configuration (`values-binance-futures.yaml`)

**Added Sections:**

```yaml
kubernetes:
  # nodePort: 32084  # Optional: Uncomment to enable NodePort service

ingress:
  enabled: false
  type: LoadBalancer
  annotations: {}
  loadBalancerIP: ""
```

**Purpose:**
- Provide clear configuration options for service types
- Include examples and documentation
- Maintain backward compatibility

### 3. Documentation Files Created

#### a. `KUBERNETES_SERVICES_README.md`
Comprehensive guide covering:
- Service type explanations
- Configuration examples
- Multi-bot deployment patterns
- Security best practices
- Troubleshooting guide
- API endpoint reference

#### b. `SERVICE_QUICK_REFERENCE.md`
Quick reference sheet with:
- Access pattern templates
- Common commands
- Configuration snippets
- Port assignment table
- Troubleshooting commands

#### c. `values-service-examples.yaml`
Complete examples for:
- ClusterIP only deployment
- NodePort configuration
- LoadBalancer setup
- Multi-bot configurations
- Production deployment patterns
- Decision tree for service selection

### 4. Validation Script (`validate-services.sh`)

**Features:**
- Validates service configuration
- Checks for port conflicts
- Verifies endpoints and connectivity
- Supports single namespace or all-namespaces validation
- Colorized output for easy reading
- Detailed reporting

**Usage:**
```bash
# Validate single namespace
./validate-services.sh bot-ssc-01

# Validate all namespaces
./validate-services.sh --all

# Verbose mode
./validate-services.sh bot-ssc-02 --verbose
```

## Service Architecture

### Service Types and Their Purposes

```
┌─────────────────────────────────────────────────────────────┐
│                      Kubernetes Cluster                      │
│                                                              │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  Namespace: bot-ssc-01                                │  │
│  │                                                        │  │
│  │  ┌──────────────────┐    ┌──────────────────┐        │  │
│  │  │  Pod             │    │  ClusterIP       │        │  │
│  │  │  freqtrade       │◄───│  Service         │◄─────┐ │  │
│  │  │  (8084)          │    │  (8084)          │      │ │  │
│  │  └──────────────────┘    └──────────────────┘      │ │  │
│  │                               ▲                     │ │  │
│  │                               │                     │ │  │
│  │                               │  Inter-pod          │ │  │
│  │                               │  communication      │ │  │
│  └───────────────────────────────│─────────────────────┘ │  │
│                                  │                       │  │
│  ┌───────────────────────────────│─────────────────────┐ │  │
│  │  Namespace: bot-ssc-02        │                     │ │  │
│  │                               │                     │ │  │
│  │  ┌──────────────────┐    ┌────┴──────────────┐     │ │  │
│  │  │  Pod             │    │  ClusterIP       │     │ │  │
│  │  │  freqtrade       │◄───│  Service         │     │ │  │
│  │  │  (8084)          │    │  (8084)          │─────┘ │  │
│  │  └──────────────────┘    └──────────────────┘       │  │
│  │            ▲                                         │  │
│  │            │                                         │  │
│  │            │                                         │  │
│  │     ┌──────┴──────────┐                             │  │
│  │     │  NodePort       │                             │  │
│  │     │  Service        │                             │  │
│  │     │  (32382)        │                             │  │
│  │     └─────────────────┘                             │  │
│  │            ▲                                         │  │
│  └────────────│─────────────────────────────────────────┘  │
│               │                                            │
└───────────────│─────────────────────────────────────────────┘
                │
                │  External Access
                ▼
        ┌───────────────┐
        │  Node IP:Port │
        │  192.168.1.10 │
        │     :32382    │
        └───────────────┘
```

## Service Discovery

### Internal Communication (ClusterIP)

Services are accessible within the cluster using DNS:

**Format:**
```
<service-name>.<namespace>.svc.cluster.local:<port>
```

**Examples:**
```
freqtrade-clusterip-bot-ssc-01.bot-ssc-01.svc.cluster.local:8084
freqtrade-clusterip-bot-ssc-02.bot-ssc-02.svc.cluster.local:8084
freqtrade-clusterip-multimetricstrategy.multimetricstrategy.svc.cluster.local:8084
```

### External Access (NodePort)

Services are accessible from outside the cluster using any node's IP:

**Format:**
```
<node-ip>:<nodePort>
```

**Examples:**
```
192.168.1.100:32381  # bot-ssc-01
192.168.1.100:32382  # bot-ssc-02
192.168.1.101:32392  # multimetricstrategy
```

### External Access (LoadBalancer)

Services are accessible via the load balancer's assigned IP or hostname:

**Format:**
```
<load-balancer-ip>:<port>
<load-balancer-hostname>:<port>
```

## Port Management

### Current Port Allocations

| Bot Name              | Namespace              | NodePort | API Port | Status |
|-----------------------|------------------------|----------|----------|--------|
| bot-ssc-01            | bot-ssc-01             | 32381    | 8084     | Active |
| bot-ssc-02            | bot-ssc-02             | 32382    | 8084     | Active |
| bot-mssm-02           | bot-mssm-02            | 32372    | 8084     | Active |
| multimetricstrategy   | multimetricstrategy    | 32392    | 8084     | Active |

### Port Range Guidelines

```
30000-30999: Reserved for system services
31000-31999: Available for general use
32000-32099: Reserved for infrastructure
32100-32199: Production bots
32200-32299: Staging bots
32300-32399: Development/testing bots (current allocations)
32400-32499: Monitoring/observability
32500-32767: Available for special use cases
```

## Configuration Patterns

### Pattern 1: Internal-Only Bot

```yaml
# No kubernetes or ingress section needed
config:
  api_server:
    listen_port: 8084
```

**Result:** ClusterIP service only

### Pattern 2: Development Bot with External Access

```yaml
config:
  api_server:
    listen_port: 8084

kubernetes:
  nodePort: 32384
```

**Result:** ClusterIP + NodePort services

### Pattern 3: Production Bot on Cloud

```yaml
config:
  api_server:
    listen_port: 8084

ingress:
  enabled: true
  type: LoadBalancer
  annotations:
    service.beta.kubernetes.io/aws-load-balancer-type: "nlb"
```

**Result:** ClusterIP + LoadBalancer services

### Pattern 4: Hedging Strategy (Multi-Bot)

**Bot 1 (Spot):**
```yaml
kubernetes:
  nodePort: 32381
config:
  api_server:
    listen_port: 8084
```

**Bot 2 (Futures - references Bot 1):**
```yaml
kubernetes:
  nodePort: 32382
config:
  api_server:
    listen_port: 8084
configcreds:
  dersalvador:
    hedging:
      spot_bot_api: "http://freqtrade:password@freqtrade-clusterip-bot-ssc-01.bot-ssc-01.svc.cluster.local:8084/api/v1/forceenter"
```

**Result:** Both bots have ClusterIP + NodePort, Bot 2 can communicate with Bot 1 internally

## Deployment Workflow

### 1. Single Bot Deployment

```bash
# Deploy with default ClusterIP
helm install my-bot ./chart \
  -f values-binance-futures.yaml \
  -f values-my-bot-creds.yaml \
  --namespace my-bot \
  --create-namespace
```

### 2. Multi-Bot Deployment

```bash
# Deploy first bot
helm install bot-ssc-01 ./chart \
  -f values-binance-futures.yaml \
  -f values-bot-ssc-01-creds.yaml \
  --namespace bot-ssc-01 \
  --create-namespace

# Deploy second bot (can reference first bot)
helm install bot-ssc-02 ./chart \
  -f values-binance-futures.yaml \
  -f values-bot-ssc-02-creds.yaml \
  --namespace bot-ssc-02 \
  --create-namespace
```

### 3. Validation

```bash
# Validate services
./validate-services.sh --all

# Check specific namespace
./validate-services.sh bot-ssc-01 --verbose
```

### 4. Testing

```bash
# Test internal connectivity
kubectl run curl-test --image=curlimages/curl -i --tty --rm --restart=Never -n bot-ssc-01 -- \
  curl http://freqtrade:password@freqtrade-clusterip-bot-ssc-01.bot-ssc-01.svc.cluster.local:8084/api/v1/ping

# Test external connectivity (NodePort)
curl http://freqtrade:password@<node-ip>:32381/api/v1/status
```

## Migration Guide

### For Existing Deployments

**Step 1: Backup Current Configuration**
```bash
kubectl get services --all-namespaces -o yaml > services-backup.yaml
kubectl get deployments --all-namespaces -o yaml > deployments-backup.yaml
```

**Step 2: Update Helm Chart**
```bash
helm upgrade <release-name> ./chart \
  -f values-binance-futures.yaml \
  -f values-<bot>-creds.yaml \
  --namespace <namespace>
```

**Step 3: Verify Services**
```bash
./validate-services.sh <namespace>
```

**Step 4: Update Inter-Bot URLs**

If you have bots that communicate with each other, update their configuration to use the new service names:

```yaml
# Old (if using direct pod IPs - not recommended)
spot_bot_api: "http://freqtrade:password@10.244.0.5:8084/api/v1/status"

# New (using service DNS)
spot_bot_api: "http://freqtrade:password@freqtrade-clusterip-bot-ssc-01.bot-ssc-01.svc.cluster.local:8084/api/v1/status"
```

**Step 5: Test Connectivity**
```bash
# Test each bot's API
for ns in bot-ssc-01 bot-ssc-02 multimetricstrategy; do
  echo "Testing $ns..."
  ./validate-services.sh $ns
done
```

## Security Considerations

### 1. Network Policies

Consider implementing Kubernetes NetworkPolicies to restrict traffic:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: freqtrade-network-policy
  namespace: bot-ssc-02
spec:
  podSelector:
    matchLabels:
      app: freqtrade-bot-ssc-02
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: bot-ssc-01  # Allow from specific namespace
    - podSelector:
        matchLabels:
          app: monitoring  # Allow from monitoring tools
    ports:
    - protocol: TCP
      port: 8084
```

### 2. Authentication

Always use strong passwords:
```yaml
config:
  api_server:
    username: freqtrade
    password: "$(openssl rand -base64 32)"  # Generate strong password
```

### 3. TLS/SSL

For production, consider adding TLS termination via Ingress:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: freqtrade-ingress
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
    nginx.ingress.kubernetes.io/backend-protocol: "HTTP"
spec:
  tls:
  - hosts:
    - bot.example.com
    secretName: freqtrade-tls
  rules:
  - host: bot.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: freqtrade-clusterip-bot-ssc-01
            port:
              number: 8084
```

## Monitoring and Observability

### Service Monitoring

```bash
# Watch service status
kubectl get svc --all-namespaces -w | grep freqtrade

# Monitor endpoints
kubectl get endpoints --all-namespaces -w | grep freqtrade

# Check service metrics
kubectl top pods --all-namespaces -l app=freqtrade
```

### Health Checks

Services automatically route traffic based on pod readiness. Ensure your deployment has proper health checks:

```yaml
# In deployment.yaml
containers:
- name: freqtrade
  ports:
  - name: api
    containerPort: 8084
  livenessProbe:
    httpGet:
      path: /api/v1/ping
      port: api
    initialDelaySeconds: 30
    periodSeconds: 10
  readinessProbe:
    httpGet:
      path: /api/v1/ping
      port: api
    initialDelaySeconds: 10
    periodSeconds: 5
```

## Troubleshooting

### Service Not Accessible

1. **Check service exists:**
   ```bash
   kubectl get svc -n <namespace>
   ```

2. **Check endpoints:**
   ```bash
   kubectl get endpoints -n <namespace>
   ```

3. **Check pod labels match service selector:**
   ```bash
   kubectl get pods -n <namespace> --show-labels
   ```

4. **Check pod logs:**
   ```bash
   kubectl logs -n <namespace> -l app=freqtrade-<namespace>
   ```

### Port Conflicts

```bash
# List all NodePort allocations
kubectl get svc --all-namespaces -o json | \
  jq '.items[] | select(.spec.type=="NodePort") | {name:.metadata.name, namespace:.metadata.namespace, nodePort:.spec.ports[0].nodePort}'
```

### DNS Issues

```bash
# Test DNS resolution from within a pod
kubectl run dns-test --image=busybox:1.28 -i --tty --rm --restart=Never -- \
  nslookup freqtrade-clusterip-bot-ssc-01.bot-ssc-01.svc.cluster.local
```

## Best Practices

1. **Use ClusterIP for internal communication** - More secure and doesn't require external port allocations
2. **Document port allocations** - Keep track of NodePort assignments to avoid conflicts
3. **Implement NetworkPolicies** - Restrict traffic to only necessary sources
4. **Use LoadBalancers in production** - More reliable than NodePort for external access
5. **Enable monitoring** - Use Prometheus/Grafana to monitor service health
6. **Test after deployment** - Always validate services work as expected
7. **Use DNS names over IPs** - Services and pods can move, DNS is stable
8. **Implement health checks** - Ensure services only route to healthy pods

## Resources

- **Main Documentation**: `KUBERNETES_SERVICES_README.md`
- **Quick Reference**: `SERVICE_QUICK_REFERENCE.md`
- **Configuration Examples**: `values-service-examples.yaml`
- **Validation Script**: `validate-services.sh`

## Summary

The new service implementation provides:
- ✅ Flexible access patterns (ClusterIP, NodePort, LoadBalancer)
- ✅ Namespace isolation and proper service discovery
- ✅ Support for multi-bot deployments and inter-bot communication
- ✅ No port conflicts between deployments
- ✅ Cloud-native and on-premises deployment support
- ✅ Comprehensive documentation and validation tools
- ✅ Security best practices and examples
- ✅ Easy migration path from existing deployments

## Version Information

- **Implementation Date**: October 13, 2025
- **Helm Chart Version**: Compatible with existing chart
- **Kubernetes Version**: 1.20+
- **Backward Compatibility**: Yes (ClusterIP always created, other services optional)


