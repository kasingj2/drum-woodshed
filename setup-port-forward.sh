#!/bin/bash
# Run once with sudo to forward port 80 → 8080 so woodshed.local needs no port number.
# Sets up immediately and persists across reboots via a LaunchDaemon.

set -e

if [ "$EUID" -ne 0 ]; then
  echo "Run with sudo: sudo ./setup-port-forward.sh"
  exit 1
fi

ANCHOR=/etc/pf.anchors/woodshed
PLIST=/Library/LaunchDaemons/local.woodshed.portforward.plist

cat > "$ANCHOR" << 'EOF'
rdr pass proto tcp from any to any port 80 -> 127.0.0.1 port 8080
EOF

cat > "$PLIST" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>local.woodshed.portforward</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/sh</string>
        <string>-c</string>
        <string>/sbin/pfctl -ef $ANCHOR</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
</dict>
</plist>
EOF

# Apply immediately
pfctl -ef "$ANCHOR" 2>/dev/null || true

# Load daemon so it runs at every boot
launchctl load "$PLIST" 2>/dev/null || launchctl bootstrap system "$PLIST"

echo "Done — port 80 → 8080 is active and will persist across reboots."
echo "woodshed.local will work once the server is running."
