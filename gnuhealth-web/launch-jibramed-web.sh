SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🚀 Launch JibraMed GUI"
TRYTON_CONF="$HOME/gnuhealth/tryton/server/config/trytond.conf"
trytond -c $TRYTON_CONF