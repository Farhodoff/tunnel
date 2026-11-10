#!/usr/bin/env bash
# Tunelio (tunnel) 1-Line Quick Installer
# Usage: curl -fsSL https://raw.githubusercontent.com/Farhodoff/tunnel/main/install.sh | bash

set -e

echo "⚡ Installing Tunelio (tunnel CLI)..."

# Check Python 3
if ! command -v python3 >/dev/null 2>&1; then
    echo "❌ Error: python3 is required but not installed." >&2
    exit 1
fi

INSTALL_DIR="${HOME}/.local/bin"
mkdir -p "${INSTALL_DIR}"

# Install virtualenv or direct pip package
TARGET_DIR="${HOME}/.tunelio"
if [ ! -d "${TARGET_DIR}" ]; then
    echo "📦 Creating virtual environment at ${TARGET_DIR}..."
    python3 -m venv "${TARGET_DIR}"
fi

echo "📥 Installing tunnel dependencies..."
"${TARGET_DIR}/bin/pip" install --quiet --upgrade pip
"${TARGET_DIR}/bin/pip" install --quiet git+https://github.com/Farhodoff/tunnel.git

# Create symlink/wrapper in ~/.local/bin
cat << 'EOF' > "${INSTALL_DIR}/tunnel"
#!/usr/bin/env bash
exec "${HOME}/.tunelio/bin/python" -m tunnel.cli "$@"
EOF

chmod +x "${INSTALL_DIR}/tunnel"

echo "✅ Tunelio installed successfully!"
echo ""
echo "🚀 Try running:"
echo "   tunnel --help"
echo "   tunnel client --port 8000 --subdomain myapp"
echo ""
if [[ ":$PATH:" != *":${INSTALL_DIR}:"* ]]; then
    echo "⚠️  Note: Make sure ${INSTALL_DIR} is in your PATH. Add this to your shell config (~/.zshrc or ~/.bashrc):"
    echo "   export PATH=\"\$HOME/.local/bin:\$PATH\""
fi
