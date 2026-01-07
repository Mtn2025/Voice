#!/bin/bash
# =============================================================================
# Lint Script - Asistente Andrea
# =============================================================================
# Executes Ruff linter to check code quality and formatting
# Usage:
#   ./scripts/lint.sh              # Check only
#   ./scripts/lint.sh --fix        # Check and auto-fix issues
#   ./scripts/lint.sh --format     # Check, fix, and format code
# =============================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔍 Running Ruff Linter for Asistente Andrea${NC}"
echo -e "${BLUE}===============================================${NC}"

# Parse arguments
FIX_MODE=false
FORMAT_MODE=false

for arg in "$@"; do
    case $arg in
        --fix)
            FIX_MODE=true
            ;;
        --format)
            FIX_MODE=true
            FORMAT_MODE=true
            ;;
    esac
done

# =============================================================================
# 1. LINTING (Check code quality)
# =============================================================================
echo -e "\n${YELLOW}Step 1: Linting Python code...${NC}"

if [ "$FIX_MODE" = true ]; then
    echo -e "${GREEN}→ Running with auto-fix enabled${NC}"
    ruff check app/ tests/ --fix
else
    echo -e "${YELLOW}→ Running in check-only mode (use --fix to auto-fix)${NC}"
    ruff check app/ tests/
fi

# =============================================================================
# 2. FORMATTING (Check code formatting)
# =============================================================================
if [ "$FORMAT_MODE" = true ]; then
    echo -e "\n${YELLOW}Step 2: Formatting Python code...${NC}"
    echo -e "${GREEN}→ Applying Ruff formatter${NC}"
    ruff format app/ tests/
else
    echo -e "\n${YELLOW}Step 2: Checking code formatting...${NC}"
    echo -e "${YELLOW}→ Running in check-only mode (use --format to auto-format)${NC}"
    ruff format --check app/ tests/
fi

# =============================================================================
# 3. SUMMARY
# =============================================================================
echo -e "\n${GREEN}✅ Linting completed successfully!${NC}"
echo -e "${BLUE}===============================================${NC}"

if [ "$FIX_MODE" = false ]; then
    echo -e "${YELLOW}💡 Tip: Run with --fix to automatically fix issues${NC}"
fi

if [ "$FORMAT_MODE" = false ]; then
    echo -e "${YELLOW}💡 Tip: Run with --format to auto-fix and format code${NC}"
fi

echo ""
