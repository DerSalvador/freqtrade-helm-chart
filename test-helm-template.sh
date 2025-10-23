#!/bin/bash

# ==============================================================================
# Helm Template Validation Script
# ==============================================================================
# Tests if Helm templates render correctly without deploying them
# ==============================================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

print_header() {
    echo -e "\n${BLUE}===================================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}===================================================================${NC}\n"
}

# Check if helm is installed
if ! command -v helm &> /dev/null; then
    print_error "Helm is not installed. Please install Helm first."
    exit 1
fi

CHART_DIR="/Users/msantana/dersalvador/freqtrading/freqtrade-helm-chart/chart"
VALUES_FILE="/Users/msantana/dersalvador/freqtrading/freqtrade-helm-chart/chart/values-binance-futures.yaml"

print_header "Helm Template Validation"

# Test 1: Basic template render
print_info "Test 1: Rendering templates with default values..."
if helm template test-release "$CHART_DIR" -f "$VALUES_FILE" --namespace test > /dev/null 2>&1; then
    print_success "Basic template rendering successful"
else
    print_error "Basic template rendering failed"
    helm template test-release "$CHART_DIR" -f "$VALUES_FILE" --namespace test 2>&1 | head -20
    exit 1
fi

# Test 2: Template with NodePort
print_info "Test 2: Rendering templates with NodePort enabled..."
if helm template test-release "$CHART_DIR" \
    -f "$VALUES_FILE" \
    --set kubernetes.nodePort=32084 \
    --namespace test > /dev/null 2>&1; then
    print_success "NodePort template rendering successful"
else
    print_error "NodePort template rendering failed"
    exit 1
fi

# Test 3: Template with LoadBalancer
print_info "Test 3: Rendering templates with LoadBalancer enabled..."
if helm template test-release "$CHART_DIR" \
    -f "$VALUES_FILE" \
    --set ingress.enabled=true \
    --set ingress.type=LoadBalancer \
    --namespace test > /dev/null 2>&1; then
    print_success "LoadBalancer template rendering successful"
else
    print_error "LoadBalancer template rendering failed"
    exit 1
fi

# Test 4: Lint the chart
print_info "Test 4: Running Helm lint..."
if helm lint "$CHART_DIR" -f "$VALUES_FILE" > /dev/null 2>&1; then
    print_success "Helm lint passed"
else
    print_error "Helm lint failed"
    helm lint "$CHART_DIR" -f "$VALUES_FILE"
    exit 1
fi

# Test 5: Show rendered service template
print_info "Test 5: Displaying rendered service templates..."
echo ""
echo "===== ClusterIP Service (always created) ====="
helm template test-release "$CHART_DIR" \
    -f "$VALUES_FILE" \
    --namespace test-namespace \
    --show-only templates/service.yaml | head -25

echo ""
echo "===== With NodePort Enabled ====="
helm template test-release "$CHART_DIR" \
    -f "$VALUES_FILE" \
    --set kubernetes.nodePort=32084 \
    --namespace test-namespace \
    --show-only templates/service.yaml | grep -A 20 "NodePort Service"

print_header "All Tests Passed!"

echo -e "
${GREEN}✓ Helm templates are valid and render correctly${NC}

You can now safely deploy using:
  helm install <release-name> $CHART_DIR \\
    -f $VALUES_FILE \\
    --namespace <namespace> \\
    --create-namespace
"

exit 0


