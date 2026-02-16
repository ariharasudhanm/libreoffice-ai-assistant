#!/bin/bash
# Build script for LibreOffice AI Assistant Extension

set -e
cd "$(dirname "$0")"

echo "Building LibreOffice AI Assistant Extension v1.0.0..."

# Clean old build #
rm -f lo-ai-assistant.oxt

# Package the extension
cd extension
zip -r ../lo-ai-assistant.oxt \
    ai_assistant.py \
    pythonpath/ \
    registry/Addons.xcu \
    assets/ \
    description/ \
    META-INF/ \
    description.xml \
    -x "*.pyc" -x "__pycache__/*"

cd ..

if [ -f "lo-ai-assistant.oxt" ]; then
    echo ""
    echo "✓ Extension built successfully: lo-ai-assistant.oxt"
    echo ""
    echo "Contents:"
    unzip -l lo-ai-assistant.oxt
    echo ""
    echo "To install:"
    echo "  1. Close ALL LibreOffice windows"
    echo "  2. Open LibreOffice Writer"
    echo "  3. Tools > Extension Manager > Add"
    echo "  4. Select lo-ai-assistant.oxt"
    echo "  5. Restart LibreOffice"
else
    echo "✗ Build failed"
    exit 1
fi
