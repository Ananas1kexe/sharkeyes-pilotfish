#!/usr/bin/env bash

RED="\033[31m"
GREEN="\033[32m"
YELLOW="\033[33m"
BLUE="\033[34m"
RESET="\033[0m"
BOLD="\033[1m"

print_header() {
    echo -e "\n${BOLD}${BLUE}════════════════════════════════════${RESET}"
    echo -e "${BOLD}${BLUE}▶ $1${RESET}"
    echo -e "${BOLD}${BLUE}════════════════════════════════════${RESET}\n"
}

print_success() {
    echo -e "${GREEN}✓ $1${RESET}\n"
}

print_error() {
    echo -e "${RED}✗ $1${RESET}\n"
}

cd test/ci || exit 1

print_header "Running security checks"

print_header "pip-audit"
if bash ./audit.sh; then
    print_success "audit completed successfully"
else
    print_error "audit completed with an error"
fi
print_header "gitleaks"

if bash ./leaks.sh; then
    print_success "gitleaks completed successfully"
else
    print_error "gitleaks completed with an error"
fi

print_header "bandit"
if bash ./bandit.sh; then
    print_success "bandit completed successfully"
else
    print_error "bandit completed with an error"
fi

print_header "ruff"
if bash ./ruff_check.sh; then
    print_success "ruff completed successfully"
else
    print_error "ruff completed with an error"
fi

echo -e "${BOLD}${GREEN}════════════════════════════════════${RESET}"
echo -e "${BOLD}${GREEN}✓ All checks are complete!${RESET}"
echo -e "${BOLD}${GREEN}════════════════════════════════════${RESET}\n"
