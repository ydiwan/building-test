#!/usr/bin/env bash
# quick setup script for floor level pi's
# installs deps, enables I2C/SPI + gpiozero.
# Usage:  ./deploy/setup_floor_pi.sh
# after setup, reboot to apply group and gpio changes
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REQ="$REPO_ROOT/src/occ_building/requirements.txt"
USER_NAME="${SUDO_USER:-$USER}"

echo "[1/5] installing dependencies..."
sudo apt-get update
sudo apt-get install -y python3-pip python3-smbus i2c-tools python3-gpiozero ros-jazzy-rmw-zenoh-cpp
sudo apt-get install -y python3-lgpio || sudo python3 -m pip install --break-system-packages lgpio

echo "[2/5] enable I2C + SPI..."
CONFIG=/boot/firmware/config.txt
[ -f "$CONFIG" ] || CONFIG=/boot/config.txt
if [ -f "$CONFIG" ]; then
  grep -q '^dtparam=i2c_arm=on' "$CONFIG" || echo 'dtparam=i2c_arm=on' | sudo tee -a "$CONFIG" >/dev/null
  grep -q '^dtparam=spi=on'     "$CONFIG" || echo 'dtparam=spi=on'     | sudo tee -a "$CONFIG" >/dev/null
  echo "   patched $CONFIG"
else
  echo "ERROR: no boot config found - enable I2C/SPI manually with raspi-config"
fi
grep -qx 'i2c-dev' /etc/modules 2>/dev/null || echo 'i2c-dev' | sudo tee -a /etc/modules >/dev/null
sudo modprobe i2c-dev || true

echo "[3/5] configuring hardware groups..."
sudo tee /etc/udev/rules.d/99-occ-hardware.rules >/dev/null <<'EOF'
KERNEL=="gpiochip[0-9]*", GROUP="dialout", MODE="0660"
SUBSYSTEM=="i2c-dev", GROUP="dialout", MODE="0660"
SUBSYSTEM=="spidev", GROUP="dialout", MODE="0660"
EOF
sudo udevadm control --reload-rules && sudo udevadm trigger || true
sudo usermod -aG dialout "$USER_NAME" || true

echo "[4/5] python hardware dependencies"
sudo python3 -m pip install --break-system-packages -r "$REQ"

echo "[5/5] final checks"
ls -l /dev/i2c-* 2>/dev/null || echo "   (no /dev/i2c-* yet - appears after reboot)"
python3 -c "import gpiozero; print('   gpiozero OK')" 2>/dev/null || echo "   ERROR: gpiozero import failed"

echo
echo "ALL DONE, PLEASE REBOOT (sudo reboot)"
echo "After reboot, build the workspace and launch:"
