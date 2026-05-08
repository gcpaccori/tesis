#!/usr/bin/env bash
set -euo pipefail

TARGET_VERSION="${TARGET_VERSION:-580.126.16}"
INSTALLER="${INSTALLER:-/home/u23u/installers/NVIDIA-Linux-x86_64-${TARGET_VERSION}.run}"
LOG_DIR="${LOG_DIR:-/home/u23u/langflow-qa/runtime/nvidia-driver}"
LOG_FILE="$LOG_DIR/install-${TARGET_VERSION}-$(date -u +%Y%m%d-%H%M%S).log"

mkdir -p "$LOG_DIR"
exec > >(tee -a "$LOG_FILE") 2>&1

echo "== NVIDIA driver safe installer =="
echo "Target: $TARGET_VERSION"
echo "Installer: $INSTALLER"
echo "Log: $LOG_FILE"
echo

if [ "$(id -u)" -ne 0 ]; then
  echo "ERROR: ejecuta este script como root, por ejemplo:"
  echo "  sudo bash $0"
  exit 100
fi

if [ ! -x "$INSTALLER" ]; then
  echo "ERROR: instalador no existe o no es ejecutable: $INSTALLER"
  exit 101
fi

echo "== Preflight =="
cat /etc/os-release | sed -n '1,8p' || true
echo "Kernel: $(uname -r)"
echo "Current driver:"
nvidia-smi --query-gpu=driver_version,name,memory.used,memory.total --format=csv,noheader || true
cat /proc/driver/nvidia/version 2>/dev/null || true

if [ ! -d "/usr/src/kernels/$(uname -r)" ]; then
  echo "ERROR: falta kernel-devel para $(uname -r)"
  exit 102
fi

if [ ! -x /usr/bin/gcc ]; then
  echo "ERROR: falta /usr/bin/gcc"
  exit 103
fi

echo
echo "== GPU users =="
nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv,noheader 2>/dev/null || true

echo
echo "== Stop only local model/GPU monitor services =="
podman stop qa-ollama >/dev/null 2>&1 || true
if [ -f /home/u23u/langflow-qa/runtime/kimi-k26/sglang.pid ]; then
  kill "$(cat /home/u23u/langflow-qa/runtime/kimi-k26/sglang.pid)" >/dev/null 2>&1 || true
fi
pkill -f 'sglang.launch_server' >/dev/null 2>&1 || true
systemctl stop prometheus-dcgm-exporter.service >/dev/null 2>&1 || true
systemctl stop nvidia-dcgm.service >/dev/null 2>&1 || true
systemctl stop nvidia-persistenced.service >/dev/null 2>&1 || true

echo
echo "== Install driver $TARGET_VERSION =="
export CC=/usr/bin/gcc
"$INSTALLER" \
  --silent \
  --accept-license \
  --no-questions \
  --ui=none \
  --no-install-compat32-libs

echo
echo "== Rebuild initramfs and module deps =="
dracut --force "/boot/initramfs-$(uname -r).img" "$(uname -r)" || dracut --force
depmod -a
systemctl daemon-reload

echo
echo "== Restart NVIDIA monitor services =="
systemctl start nvidia-persistenced.service >/dev/null 2>&1 || true
systemctl start nvidia-dcgm.service >/dev/null 2>&1 || true
systemctl start prometheus-dcgm-exporter.service >/dev/null 2>&1 || true

echo
echo "== Postcheck =="
cat /proc/driver/nvidia/version 2>/dev/null || true
nvidia-smi || true

echo
echo "Si nvidia-smi sigue mostrando el driver anterior, reinicia el nodo para cargar el modulo nuevo."
echo "Instalacion finalizada. Log: $LOG_FILE"
