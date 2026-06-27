#!/usr/bin/env bash
# One-shot setup for an OCC building floor Pi (Ubuntu 24.04 + ROS 2 Jazzy).
# Installs hardware deps, enables I2C/SPI + pigpiod, installs the Python drivers.
#
#   Usage:  ./deploy/setup_floor_pi.sh        (run as your normal user; it sudo's as needed)
#
# A REBOOT is required afterwards for the I2C/SPI and group changes to take effect.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REQ="$REPO_ROOT/src/occ_building/requirements.txt"
USER_NAME="${SUDO_USER:-$USER}"

echo "== [1/5] apt packages =="
sudo apt-get update
sudo apt-get install -y python3-pip python3-smbus i2c-tools python3-gpiozero ros-jazzy-rmw-zenoh-cpp
# GPIO backend for gpiozero (PIR), works on Pi 4 + Pi 5. Prefer apt, fall back to pip.
sudo apt-get install -y python3-lgpio || sudo python3 -m pip install --break-system-packages lgpio

echo "== [2/5] enable I2C + SPI =="
# Ubuntu-on-Pi keeps the firmware config here; fall back to Raspberry Pi OS path.
CONFIG=/boot/firmware/config.txt
[ -f "$CONFIG" ] || CONFIG=/boot/config.txt
if [ -f "$CONFIG" ]; then
  grep -q '^dtparam=i2c_arm=on' "$CONFIG" || echo 'dtparam=i2c_arm=on' | sudo tee -a "$CONFIG" >/dev/null
  grep -q '^dtparam=spi=on'     "$CONFIG" || echo 'dtparam=spi=on'     | sudo tee -a "$CONFIG" >/dev/null
  echo "   patched $CONFIG"
else
  echo "   WARN: no boot config found - enable I2C/SPI manually (raspi-config or config.txt)."
fi
grep -qx 'i2c-dev' /etc/modules 2>/dev/null || echo 'i2c-dev' | sudo tee -a /etc/modules >/dev/null
sudo modprobe i2c-dev || true

echo "== [3/5] hardware device access (udev -> dialout; Ubuntu has no gpio/spi groups) =="
sudo tee /etc/udev/rules.d/99-occ-hardware.rules >/dev/null <<'EOF'
# Grant non-root users in 'dialout' access to GPIO, I2C and SPI character devices.
KERNEL=="gpiochip[0-9]*", GROUP="dialout", MODE="0660"
SUBSYSTEM=="i2c-dev", GROUP="dialout", MODE="0660"
SUBSYSTEM=="spidev", GROUP="dialout", MODE="0660"
EOF
sudo udevadm control --reload-rules && sudo udevadm trigger || true
sudo usermod -aG dialout "$USER_NAME" || true

echo "== [4/5] python hardware drivers (system; PEP668 override) =="
sudo python3 -m pip install --break-system-packages -r "$REQ"

echo "== [5/5] sanity =="
ls -l /dev/i2c-* 2>/dev/null || echo "   (no /dev/i2c-* yet - appears after reboot)"
python3 -c "import gpiozero; print('   gpiozero OK')" 2>/dev/null || echo "   WARN: gpiozero import failed"

echo
echo "DONE.  >>> REBOOT NOW <<<  (sudo reboot) for I2C/SPI + group membership to apply."
echo "After reboot, build the workspace and launch:"
echo "  cd $REPO_ROOT && export PATH=/usr/bin:\$PATH && source /opt/ros/jazzy/setup.bash"
echo "  colcon build && source install/setup.bash"
echo "  ros2 launch occ_building floor.launch.py floor:=1"
