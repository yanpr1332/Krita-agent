#!/usr/bin/env bash
# Disposable Krita + Bridge pilot. This runs in GitHub's Xvfb virtual display,
# never on the user's local computer. The probe itself never fakes KRA/PNG.
set -euo pipefail

: "${RUNNER_TEMP:?}"
: "${GITHUB_WORKSPACE:?}"
ROOT="${RUNNER_TEMP}/krita-native-pilot"
ART="${ROOT}/artifacts"
HOME_DATA="${ROOT}/data"
HOME_CONFIG="${ROOT}/config"
mkdir -p "$ART" "$HOME_DATA/krita/pykrita" "$HOME_CONFIG"
chmod 700 "$ROOT" "$ART"

# Isolate plugin and Krita config from any host/user session.
export XDG_DATA_HOME="$HOME_DATA"
export XDG_CONFIG_HOME="$HOME_CONFIG"
cp "$GITHUB_WORKSPACE/plugin/krita_agent_bridge.desktop" "$HOME_DATA/krita/pykrita/"
cp -R "$GITHUB_WORKSPACE/plugin/krita_agent_bridge" "$HOME_DATA/krita/pykrita/"
cat > "$HOME_CONFIG/kritarc" <<'EOF'
[python]
enable_krita_agent_bridge=true
EOF

export KRITA_AGENT_TOKEN="$(python -c 'import secrets;print(secrets.token_urlsafe(36))')"
export KRITA_AGENT_PORT=47653
export KRITA_AGENT_OUTPUT_DIR="$ART"
export KRITA_AGENT_INPUT_DIR="$ART"
export KRITA_AGENT_DOCK=0
export QT_OPENGL=software
export LIBGL_ALWAYS_SOFTWARE=1
export QT_X11_NO_MITSHM=1
export XDG_RUNTIME_DIR="${RUNNER_TEMP}/krita-xdg-runtime"
mkdir -p "$XDG_RUNTIME_DIR"
chmod 700 "$XDG_RUNTIME_DIR"

{
  echo "Runner OS: $(uname -a)"
  echo "Krita executable: $(command -v krita)"
  krita --version
  echo "Python executable: $(python --version)"
  echo "DISPLAY: ${DISPLAY:-unset}"
} > "$ART/environment.txt" 2>&1

# Lightweight WM ensures a Krita active window under Xvfb, even without desktop login.
openbox > "$ART/openbox.log" 2>&1 &
wm_pid=$!
krita --nosplash > "$ART/krita-startup.log" 2>&1 &
krita_pid=$!
cleanup() {
  kill "$krita_pid" "$wm_pid" 2>/dev/null || true
  wait "$krita_pid" 2>/dev/null || true
  wait "$wm_pid" 2>/dev/null || true
}
trap cleanup EXIT

# A timeout here is a failed experiment, never an accepted native test.
timeout --signal=TERM 230s python "$GITHUB_WORKSPACE/scripts/cloud_native_probe.py" \
  --output-dir "$ART" --port "$KRITA_AGENT_PORT" --ready-timeout 95
