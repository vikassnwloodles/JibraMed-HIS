#!/bin/bash

# Install dependencies globally
sudo apt-get install -y npm
sudo npm install -g bower
sudo npm install -g grunt-cli

# Navigate to the gnuhealth-web directory and install npm packages
cd gnuhealth-web
npm install --force
npm audit fix --force
bower install
# grunt

# Set SCRIPT_DIR to the current script directory
cd ..
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo $SCRIPT_DIR
cd $SCRIPT_DIR

# === Update Tryton config ===
TRYTON_CONF="$HOME/gnuhealth/tryton/server/config/trytond.conf"

# Modify line 6
sed -i "6s|.*|listen = *:8010|" "$TRYTON_CONF" 


# Modify line 7
sed -i "7s|.*|root = $SCRIPT_DIR|" "$TRYTON_CONF"

echo "Tryton configuration updated successfully."
