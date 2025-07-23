#!/bin/bash

set -e
set -o pipefail
trap 'echo -e "\n❌ An error occurred on line $LINENO. Please fix and rerun the script."; exit 1' ERR

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd $SCRIPT_DIR


# === Load .env config ===
ENV_FILE=".env"
if [ -f "$ENV_FILE" ]; then
  echo "📥 Loading configuration from $ENV_FILE..."
  set -o allexport
  source "$ENV_FILE"
  set +o allexport
  echo "✅ Configuration loaded successfully!"
else
  echo "❌ .env file not found."
  echo "Please create a .env file with the following variables:"
  echo "DB_USER=gnuhealth"
  echo "DB_PASS=your_secret_password"
  echo "DB_NAME=health"
  echo "PYTHON_VERSION=3.12.3"
  exit 1
fi


# === Validate required env vars ===
REQUIRED_VARS=("DB_USER" "DB_PASS" "DB_NAME" "PYTHON_VERSION")
for var in "${REQUIRED_VARS[@]}"; do
  if [ -z "${!var}" ]; then
    echo "❌ Missing required variable: $var"
    echo "💡 Please add '$var=...' to your .env file."
    exit 1
  fi
done


# === Install required packages ===
echo -e "\n\n🔧 Installing required packages..."
sudo apt update
sudo apt install -y make build-essential libssl-dev zlib1g-dev libbz2-dev \
  libreadline-dev libsqlite3-dev wget curl llvm libncursesw5-dev xz-utils \
  tk-dev libxml2-dev libxmlsec1-dev libffi-dev liblzma-dev git vim \
  postgresql postgresql-contrib


# === Start PostgreSQL service ===
echo -e "\n\n🚀 Starting PostgreSQL..."
sudo service postgresql start


# === Install pyenv if not already present ===
if [ ! -d "$HOME/.pyenv" ]; then
  echo -e "\n\n📦 Installing pyenv..."
  curl https://pyenv.run | bash
fi


# === Set up pyenv for current shell ===
export PYENV_ROOT="$HOME/.pyenv"
export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init --path)"
eval "$(pyenv init -)"


# === Persist pyenv config ===
if ! grep -q 'PYENV_ROOT' "$HOME/.bashrc"; then
  echo -e "\n# Pyenv setup" >> "$HOME/.bashrc"
  {
    echo 'export PYENV_ROOT="$HOME/.pyenv"'
    echo 'export PATH="$PYENV_ROOT/bin:$PATH"'
    echo 'eval "$(pyenv init --path)"'
    echo 'eval "$(pyenv init -)"'
  } >> "$HOME/.bashrc"
fi


# === Install Python version if not installed ===
if ! pyenv versions --bare | grep -qx "$PYTHON_VERSION"; then
  echo -e "\n\n🐍 Installing Python $PYTHON_VERSION..."
  pyenv install "$PYTHON_VERSION"
fi

# pyenv local "$PYTHON_VERSION"
python -m venv env
. env/bin/activate
pip install --upgrade pip setuptools
pip install -r requirements.txt


# === Setup PostgreSQL roles and DB ===
echo -e "\n\n🛠️ Configuring PostgreSQL for GNU Health..."

echo -e "\n🧑‍💻 Creating role for GNU Health..."
if ! sudo -u postgres psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='$DB_USER'" | grep -q 1; then
  sudo -u postgres createuser --createdb --no-createrole --no-superuser "$DB_USER"
  sudo -u postgres psql -c "ALTER USER $DB_USER WITH PASSWORD '$DB_PASS'";
  echo "✅ PostgreSQL role '$DB_USER' created."
else
  echo "ℹ️ PostgreSQL role '$DB_USER' already exists. Skipping."

  echo -e "\n🔐 Testing PostgreSQL connection for user: '$DB_USER'..."

  # Test PostgreSQL authentication with a 2-second timeout
  if ! PGPASSWORD="$DB_PASS" psql -h "localhost" -U "$DB_USER" -d postgres -c '\q' -t 2 >/dev/null 2>&1; then
      echo "❌ Authentication failed!"
      echo "🔧 Possible fixes:"
      echo "   1. Provide correct value for DB_PASS in: $SCRIPT_DIR/.env"
      echo "🔄 Make sure to rerun the script after fixing the issue."
      exit 1
  fi

  echo "✅ Success! PostgreSQL credentials are valid."
fi


# === Update pg_hba.conf ===
echo -e "\n🔐 Updating pg_hba.conf..."
PG_HBA="/etc/postgresql/$(ls -v /etc/postgresql | tail -n 1)/main/pg_hba.conf"

if ! sudo grep -E "^local\s+all\s+$DB_USER\s+md5" "$PG_HBA" > /dev/null; then
    echo "local   all             $DB_USER                               md5" | sudo tee -a "$PG_HBA" > /dev/null
    echo "✅ Added md5 authentication for user '$DB_USER' to pg_hba.conf."
else
    echo "ℹ️ md5 authentication for user '$DB_USER' already exists in pg_hba.conf. Skipping."
fi

sudo service postgresql reload


# === Create database if not exists ===
echo -e "\n🛢️ Creating database for GNU Health..."
if ! sudo -u postgres psql -lqt | cut -d \| -f 1 | grep -qw "$DB_NAME"; then
  sudo -u postgres createdb -O $DB_USER $DB_NAME
  echo "✅ Database '$DB_NAME' created."
else
  echo "ℹ️ Database '$DB_NAME' already exists. Skipping."
fi


# === Update Tryton config ===
TRYTON_CONF="gnuhealth/tryton/server/config/trytond.conf"
sed -i "2s|.*|uri = postgresql://$DB_USER:$DB_PASS@localhost:5432/|" "$TRYTON_CONF"


# === Initialize GNU Health database ===
source .gnuhealthrc
TRYTOND_BIN_DIR="gnuhealth/tryton/server/$(ls -1d gnuhealth/tryton/server/trytond-* | grep -o 'trytond-[0-9.]\+' | sort -V | tail -1)/bin"
cd "$TRYTOND_BIN_DIR"
echo -e "\n\n🛠️ Initializing GNU Health Database..."
python3 ./trytond-admin --all --database="$DB_NAME" --password
echo "✅ Database initialization complete."


# === Start GNU Health ===
echo -e "\n\n🚀 Starting GNU Health..."


# === Generate GNU Health systemd service if not already present ===
SERVICE_FILE="/etc/systemd/system/gnuhealth.service"
USERNAME=$(whoami)
USER_HOME=$(eval echo "~$USERNAME")

if [ ! -f "$SERVICE_FILE" ]; then
    echo -e "\n\n🛠️ Creating systemd service file for GNU Health..."

    sudo tee "$SERVICE_FILE" > /dev/null <<EOF
[Unit]
Description=GNU Health Server
After=network.target postgresql.service

[Service]
Type=simple
User=$USERNAME
WorkingDirectory=$SCRIPT_DIR
ExecStart=$SCRIPT_DIR/start_gnuhealth.sh
Environment="PYENV_ROOT=$USER_HOME/.pyenv"
Environment="PATH=$USER_HOME/.pyenv/bin:$USER_HOME/.pyenv/shims:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF

    echo "✅ Service file created at $SERVICE_FILE"
else
    echo "ℹ️ Service file already exists at $SERVICE_FILE. Skipping creation."
fi


# === Activate the service ===
sudo systemctl daemon-reload
sudo systemctl enable gnuhealth.service
sudo systemctl start gnuhealth.service
sudo systemctl status gnuhealth.service --no-pager


echo -e "\n\n✅ GNU Health Server up and running successfully!"
