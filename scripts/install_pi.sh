#!/usr/bin/env bash
set -euo pipefail

PROJECT_SOURCE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INSTALL_DIR="/opt/led-matrix-dashboard"
SERVICE_NAME="led-matrix-dashboard"
ENV_FILE="/etc/default/${SERVICE_NAME}"
RGBMATRIX_REPO_DIR="/tmp/rpi-rgb-led-matrix"

if [[ "${EUID}" -ne 0 ]]; then
  echo "Ce script doit etre lance en root (sudo)."
  exit 1
fi

PI_USER="${SUDO_USER:-pi}"

echo "[1/9] Installation des dependances systeme"
apt update
apt install -y python3 python3-venv python3-pip python3-dev git build-essential cmake rsync

echo "[2/9] Copie du projet vers ${INSTALL_DIR}"
mkdir -p "${INSTALL_DIR}"
rsync -a --delete --exclude ".git" --exclude ".venv" "${PROJECT_SOURCE}/" "${INSTALL_DIR}/"

chown -R "${PI_USER}:${PI_USER}" "${INSTALL_DIR}"

echo "[3/9] Creation de l'environnement Python"
runuser -u "${PI_USER}" -- python3 -m venv "${INSTALL_DIR}/.venv"

echo "[4/9] Installation des dependances Python"
runuser -u "${PI_USER}" -- "${INSTALL_DIR}/.venv/bin/pip" install --upgrade pip
runuser -u "${PI_USER}" -- "${INSTALL_DIR}/.venv/bin/pip" install -r "${INSTALL_DIR}/requirements.txt"

echo "[5/9] Installation du driver LED matrix (rgbmatrix)"
if runuser -u "${PI_USER}" -- "${INSTALL_DIR}/.venv/bin/python" -c "import rgbmatrix" >/dev/null 2>&1; then
  echo "rgbmatrix deja disponible dans la venv"
else
  if runuser -u "${PI_USER}" -- "${INSTALL_DIR}/.venv/bin/pip" install rpi-rgb-led-matrix >/dev/null 2>&1; then
    echo "rgbmatrix installe via pip"
  else
    echo "Installation pip impossible, compilation depuis la source officielle"
    rm -rf "${RGBMATRIX_REPO_DIR}"
    runuser -u "${PI_USER}" -- git clone --depth 1 https://github.com/hzeller/rpi-rgb-led-matrix.git "${RGBMATRIX_REPO_DIR}"
    runuser -u "${PI_USER}" -- bash -lc "cd '${RGBMATRIX_REPO_DIR}/bindings/python' && '${INSTALL_DIR}/.venv/bin/pip' install ."
  fi

  if ! runuser -u "${PI_USER}" -- "${INSTALL_DIR}/.venv/bin/python" -c "import rgbmatrix" >/dev/null 2>&1; then
    echo "ATTENTION: rgbmatrix n'a pas pu etre installe. L'application restera en mode console."
  fi
fi

if [[ ! -f "${INSTALL_DIR}/config.yaml" ]]; then
  echo "[6/9] Initialisation de config.yaml"
  cp "${INSTALL_DIR}/config.example.yaml" "${INSTALL_DIR}/config.yaml"
fi

echo "[7/9] Initialisation du fichier d'environnement ${ENV_FILE}"
if [[ ! -f "${ENV_FILE}" ]]; then
  cat > "${ENV_FILE}" <<'EOF'
FINNHUB_API_TOKEN=
NEWSAPI_KEY=
HA_TOKEN=
EOF
fi

chmod 600 "${ENV_FILE}"

echo "[8/9] Installation du service systemd"
cp "${INSTALL_DIR}/deploy/led-matrix-dashboard.service" "/etc/systemd/system/${SERVICE_NAME}.service"
systemctl daemon-reload
systemctl enable "${SERVICE_NAME}.service"

echo "[9/9] Demarrage du service"
systemctl restart "${SERVICE_NAME}.service"

cat <<EOF
Installation terminee.

A verifier:
- ${INSTALL_DIR}/config.yaml
- ${ENV_FILE}

Commandes utiles:
- systemctl status ${SERVICE_NAME}
- journalctl -u ${SERVICE_NAME} -f
EOF
