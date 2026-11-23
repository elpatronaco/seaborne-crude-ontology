#!/usr/bin/env bash
# MIT License — Copyright (c) 2026 Pau Colomé

# ROBOT ("ROBOT is an OBO Tool") es una CLI diseñada para automatizar
# flujos de trabajo con ontologías OWL, complementaria al editor Protégé.
# La utilizamos para invocar el razonador HermiT, materializar los axiomas
# inferidos, fusionar módulos, extraer métricas y ejecutar verificaciones.

set -euo pipefail

ROBOT_VERSION="1.9.11"
ROBOT_URL="https://github.com/ontodev/robot/releases/download/v${ROBOT_VERSION}/robot.jar"

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TOOLS_DIR="${REPO_ROOT}/tools"
JAR_PATH="${TOOLS_DIR}/robot.jar"
WRAPPER_PATH="${TOOLS_DIR}/robot"

mkdir -p "${TOOLS_DIR}"

echo "Downloading ROBOT v${ROBOT_VERSION} to ${JAR_PATH}..."
curl -fsSL -L "${ROBOT_URL}" -o "${JAR_PATH}"

cat > "${WRAPPER_PATH}" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
exec java -jar "${SCRIPT_DIR}/robot.jar" "$@"
EOF

chmod +x "${WRAPPER_PATH}"
echo "Installed ROBOT wrapper at ${WRAPPER_PATH}"
"${WRAPPER_PATH}" --version
