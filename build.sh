#!/bin/bash
# CommDebugTool - Multi-platform Build Script
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "========================================"
echo " CommDebugTool - Build Script"
echo "========================================"

# Check pyinstaller
if ! command -v pyinstaller &> /dev/null; then
    echo "Installing PyInstaller..."
    pip3 install pyinstaller
fi

# Install pyserial (optional)
pip3 install pyserial 2>/dev/null || true

# Detect platform
OS_TYPE="$(uname -s)"
ARCH="$(uname -m)"
case "$OS_TYPE" in
    Darwin)  PLATFORM="macos-${ARCH}" ;;
    Linux)   PLATFORM="linux-${ARCH}" ;;
    *)       PLATFORM="$(echo $OS_TYPE | tr '[:upper:]' '[:lower:]')-${ARCH}" ;;
esac

DIST_DIR="dist/${PLATFORM}"
BUILD_DIR="build/${PLATFORM}"

echo ""
echo "Platform: ${PLATFORM}"
echo "Output:   ${DIST_DIR}/"
echo ""

# Clean only this platform's build
rm -rf "$BUILD_DIR" "$DIST_DIR"

echo "Building..."
echo ""

pyinstaller CommDebugTool.spec --noconfirm \
    --distpath "$DIST_DIR" \
    --workpath "$BUILD_DIR"

echo ""
echo "========================================"
echo " Build complete!"
echo "========================================"
echo ""
echo "  Output directory: ${DIST_DIR}/"
if [ "$OS_TYPE" = "Darwin" ]; then
    echo "  Executable:       ${DIST_DIR}/CommDebugTool"
    echo "  macOS App:        ${DIST_DIR}/CommDebugTool.app"
else
    echo "  Executable:       ${DIST_DIR}/CommDebugTool"
fi
echo ""
