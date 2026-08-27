#!/bin/bash
export DISPLAY=:1
mkdir -p /root/.vnc
echo "password" | vncpasswd -f > /root/.vnc/passwd
chmod 600 /root/.vnc/passwd

# Start VNC server (XFCE)
vncserver :1 -geometry 1280x720 -depth 24

# Start noVNC proxy
# On Ubuntu 22.04, novnc_proxy might be in different locations
if [ -f /usr/share/novnc/utils/novnc_proxy ]; then
    /usr/share/novnc/utils/novnc_proxy --vnc localhost:5901 --listen 6080 &
elif [ -f /usr/bin/novnc_proxy ]; then
    /usr/bin/novnc_proxy --vnc localhost:5901 --listen 6080 &
else
    # Fallback to websockify directly if novnc_proxy is missing
    websockify --web /usr/share/novnc/ 6080 localhost:5901 &
fi

# Keep container running
tail -f /dev/null
