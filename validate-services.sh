#!/bin/bash

# ==============================================================================
# Freqtrade Kubernetes Services Validation Script
# ==============================================================================
# This script validates service configuration and connectivity for Freqtrade
# bot deployments in Kubernetes
# ==============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
NAMESPACE="${1:-default}"
VERBOSE="${VERBOSE:-false}"

# Helper functions
print_header() {
    echo -e "\n${BLUE}===================================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}===================================================================${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

# Usage
usage() {
    cat << EOF
Usage: $0 [NAMESPACE] [OPTIONS]

Validates Kubernetes services for Freqtrade bot deployments.

Arguments:
  NAMESPACE    Kubernetes namespace to validate (default: current namespace)

Options:
  -v, --verbose    Enable verbose output
  -h, --help       Show this help message
  -a, --all        Validate all namespaces with freqtrade deployments

Examples:
  $0 bot-ssc-01                    # Validate services in bot-ssc-01 namespace
  $0 bot-ssc-02 --verbose          # Validate with verbose output
  $0 --all                         # Validate all freqtrade namespaces

Environment Variables:
  VERBOSE=true $0 bot-ssc-01       # Enable verbose mode

EOF
    exit 0
}

# Parse arguments
ALL_NAMESPACES=false
while [[ $# -gt 0 ]]; do
    case $1 in
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -a|--all)
            ALL_NAMESPACES=true
            shift
            ;;
        -h|--help)
            usage
            ;;
        *)
            NAMESPACE="$1"
            shift
            ;;
    esac
done

# Check if kubectl is installed
if ! command -v kubectl &> /dev/null; then
    print_error "kubectl is not installed. Please install kubectl first."
    exit 1
fi

# Check if jq is installed (optional but recommended)
if ! command -v jq &> /dev/null; then
    print_warning "jq is not installed. Some features will be limited."
    print_info "Install jq for better output: https://stedolan.github.io/jq/"
    HAS_JQ=false
else
    HAS_JQ=true
fi

# Function to validate a single namespace
validate_namespace() {
    local ns=$1
    
    print_header "Validating Namespace: $ns"
    
    # Check if namespace exists
    if ! kubectl get namespace "$ns" &> /dev/null; then
        print_error "Namespace '$ns' does not exist"
        return 1
    fi
    print_success "Namespace exists"
    
    # Check for Freqtrade deployment
    print_info "Checking for Freqtrade deployments..."
    DEPLOYMENTS=$(kubectl get deployments -n "$ns" -l app=freqtrade -o name 2>/dev/null || echo "")
    if [ -z "$DEPLOYMENTS" ]; then
        print_warning "No Freqtrade deployments found in namespace '$ns'"
        return 0
    fi
    
    for deployment in $DEPLOYMENTS; do
        DEPLOY_NAME=$(echo "$deployment" | cut -d'/' -f2)
        print_success "Found deployment: $DEPLOY_NAME"
        
        # Check deployment status
        REPLICAS=$(kubectl get deployment "$DEPLOY_NAME" -n "$ns" -o jsonpath='{.status.replicas}' 2>/dev/null || echo "0")
        READY=$(kubectl get deployment "$DEPLOY_NAME" -n "$ns" -o jsonpath='{.status.readyReplicas}' 2>/dev/null || echo "0")
        
        if [ "$REPLICAS" -eq "$READY" ] && [ "$READY" -gt 0 ]; then
            print_success "Deployment is ready ($READY/$REPLICAS replicas)"
        else
            print_error "Deployment is not ready ($READY/$REPLICAS replicas)"
        fi
    done
    
    # Check for services
    print_info "Checking for services..."
    
    # ClusterIP Service
    CLUSTERIP_SVC="freqtrade-clusterip-$ns"
    if kubectl get service "$CLUSTERIP_SVC" -n "$ns" &> /dev/null; then
        print_success "ClusterIP service found: $CLUSTERIP_SVC"
        
        # Get service details
        CLUSTER_IP=$(kubectl get service "$CLUSTERIP_SVC" -n "$ns" -o jsonpath='{.spec.clusterIP}')
        CLUSTER_PORT=$(kubectl get service "$CLUSTERIP_SVC" -n "$ns" -o jsonpath='{.spec.ports[0].port}')
        print_info "  Cluster IP: $CLUSTER_IP:$CLUSTER_PORT"
        print_info "  FQDN: $CLUSTERIP_SVC.$ns.svc.cluster.local:$CLUSTER_PORT"
        
        # Check endpoints
        ENDPOINTS=$(kubectl get endpoints "$CLUSTERIP_SVC" -n "$ns" -o jsonpath='{.subsets[*].addresses[*].ip}' 2>/dev/null || echo "")
        if [ -n "$ENDPOINTS" ]; then
            ENDPOINT_COUNT=$(echo "$ENDPOINTS" | wc -w)
            print_success "  Endpoints ready: $ENDPOINT_COUNT"
            if [ "$VERBOSE" = true ]; then
                for ep in $ENDPOINTS; do
                    print_info "    - $ep"
                done
            fi
        else
            print_error "  No endpoints ready for service"
        fi
    else
        print_error "ClusterIP service not found: $CLUSTERIP_SVC"
    fi
    
    # NodePort Service
    NODEPORT_SVC="freqtrade-nodeport-$ns"
    if kubectl get service "$NODEPORT_SVC" -n "$ns" &> /dev/null; then
        print_success "NodePort service found: $NODEPORT_SVC"
        
        NODE_PORT=$(kubectl get service "$NODEPORT_SVC" -n "$ns" -o jsonpath='{.spec.ports[0].nodePort}')
        print_info "  NodePort: $NODE_PORT"
        
        # Get node IPs
        NODE_IPS=$(kubectl get nodes -o jsonpath='{.items[*].status.addresses[?(@.type=="ExternalIP")].address}')
        if [ -z "$NODE_IPS" ]; then
            NODE_IPS=$(kubectl get nodes -o jsonpath='{.items[*].status.addresses[?(@.type=="InternalIP")].address}')
        fi
        
        if [ -n "$NODE_IPS" ]; then
            print_info "  Access via:"
            for node_ip in $NODE_IPS; do
                print_info "    http://$node_ip:$NODE_PORT"
            done
        fi
        
        # Check for port conflicts
        print_info "  Checking for NodePort conflicts..."
        CONFLICTS=$(kubectl get services --all-namespaces -o json | \
            grep -v "$ns" | \
            grep "nodePort.*$NODE_PORT" || echo "")
        if [ -n "$CONFLICTS" ]; then
            print_error "  NodePort $NODE_PORT is used in other namespaces!"
        else
            print_success "  No NodePort conflicts detected"
        fi
    else
        print_info "NodePort service not configured (optional)"
    fi
    
    # LoadBalancer Service
    LB_SVC="freqtrade-loadbalancer-$ns"
    if kubectl get service "$LB_SVC" -n "$ns" &> /dev/null; then
        print_success "LoadBalancer service found: $LB_SVC"
        
        LB_IP=$(kubectl get service "$LB_SVC" -n "$ns" -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "")
        LB_HOSTNAME=$(kubectl get service "$LB_SVC" -n "$ns" -o jsonpath='{.status.loadBalancer.ingress[0].hostname}' 2>/dev/null || echo "")
        
        if [ -n "$LB_IP" ]; then
            print_success "  LoadBalancer IP: $LB_IP"
            LB_PORT=$(kubectl get service "$LB_SVC" -n "$ns" -o jsonpath='{.spec.ports[0].port}')
            print_info "  Access via: http://$LB_IP:$LB_PORT"
        elif [ -n "$LB_HOSTNAME" ]; then
            print_success "  LoadBalancer Hostname: $LB_HOSTNAME"
            LB_PORT=$(kubectl get service "$LB_SVC" -n "$ns" -o jsonpath='{.spec.ports[0].port}')
            print_info "  Access via: http://$LB_HOSTNAME:$LB_PORT"
        else
            print_warning "  LoadBalancer IP/Hostname not yet assigned (may take a few minutes)"
        fi
    else
        print_info "LoadBalancer service not configured (optional)"
    fi
    
    # Test connectivity (if requested)
    if [ "$VERBOSE" = true ]; then
        print_info "Testing API connectivity..."
        
        # Create a temporary pod for testing
        TEST_POD="curl-test-$$"
        kubectl run "$TEST_POD" -n "$ns" --image=curlimages/curl --rm -i --restart=Never --command -- \
            curl -s -o /dev/null -w "%{http_code}" --max-time 5 \
            "http://$CLUSTERIP_SVC.$ns.svc.cluster.local:$CLUSTER_PORT/api/v1/ping" 2>/dev/null || true &
        
        sleep 2
        
        # Clean up test pod if still running
        kubectl delete pod "$TEST_POD" -n "$ns" --ignore-not-found=true &> /dev/null || true
    fi
    
    # Summary
    echo ""
    print_success "Validation completed for namespace: $ns"
    echo ""
}

# Main execution
print_header "Freqtrade Kubernetes Services Validator"

if [ "$ALL_NAMESPACES" = true ]; then
    print_info "Validating all namespaces with Freqtrade deployments..."
    
    # Find all namespaces with freqtrade deployments
    NAMESPACES=$(kubectl get deployments --all-namespaces -l app=freqtrade -o jsonpath='{.items[*].metadata.namespace}' | tr ' ' '\n' | sort -u)
    
    if [ -z "$NAMESPACES" ]; then
        print_warning "No Freqtrade deployments found in any namespace"
        exit 0
    fi
    
    for ns in $NAMESPACES; do
        validate_namespace "$ns"
    done
else
    validate_namespace "$NAMESPACE"
fi

# Additional checks
print_header "Additional Checks"

# Check for NodePort conflicts across all namespaces
if [ "$HAS_JQ" = true ]; then
    print_info "Checking for NodePort conflicts..."
    
    NODEPORTS=$(kubectl get services --all-namespaces -o json | \
        jq -r '.items[] | select(.spec.type=="NodePort") | "\(.spec.ports[0].nodePort) \(.metadata.namespace) \(.metadata.name)"' | \
        sort -n)
    
    if [ -n "$NODEPORTS" ]; then
        echo ""
        echo "NodePort Allocations:"
        echo "====================="
        printf "%-10s %-30s %-40s\n" "Port" "Namespace" "Service"
        echo "---------------------------------------------------------------------"
        echo "$NODEPORTS" | while read -r port namespace service; do
            printf "%-10s %-30s %-40s\n" "$port" "$namespace" "$service"
        done
        echo ""
    fi
fi

# Network policy check
print_info "Checking for NetworkPolicies..."
NP_COUNT=$(kubectl get networkpolicies --all-namespaces 2>/dev/null | grep -c "freqtrade" || echo "0")
if [ "$NP_COUNT" -gt 0 ]; then
    print_success "Found $NP_COUNT NetworkPolicy resources"
else
    print_warning "No NetworkPolicies found. Consider implementing network policies for security."
fi

print_header "Validation Complete"

echo -e "
${GREEN}Validation completed successfully!${NC}

For more information, see:
  - KUBERNETES_SERVICES_README.md
  - SERVICE_QUICK_REFERENCE.md
  - values-service-examples.yaml

To test API access:
  kubectl run curl-test --image=curlimages/curl -i --tty --rm --restart=Never -n $NAMESPACE -- \\
    curl http://freqtrade:password@freqtrade-clusterip-$NAMESPACE.$NAMESPACE.svc.cluster.local:8084/api/v1/ping
"

exit 0


