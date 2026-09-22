#!/usr/bin/env bash
# Instala o actualiza el bot en un VPS Ubuntu/Debian.
# Uso: sudo ./deploy/install.sh bot.tudominio.com tu@correo.com
# Se puede volver a correr después de "git pull" para actualizar.
set -euo pipefail

DOMAIN="${1:-}"
EMAIL="${2:-}"
APP_DIR=/opt/abarrotes-bot
SRC_DIR="$(cd "$(dirname "$0")/.." && pwd)"

if [[ $EUID -ne 0 ]]; then echo "Corre con sudo."; exit 1; fi
if [[ -z "$DOMAIN" || -z "$EMAIL" ]]; then
    echo "Uso: sudo $0 bot.tudominio.com tu@correo.com"; exit 1
fi

echo "==> Paquetes del sistema"
apt-get update -q
apt-get install -y -q python3 python3-venv rsync nginx certbot python3-certbot-nginx

echo "==> Copiando código a $APP_DIR"
mkdir -p "$APP_DIR"
if [[ "$SRC_DIR" != "$APP_DIR" ]]; then
    # No toca el .env, la base de datos ni el venv que ya estén en el servidor
    rsync -a --delete --exclude .git --exclude venv --exclude .env --exclude '*.db' \
        --exclude '*.log' "$SRC_DIR"/ "$APP_DIR"/
fi

if [[ ! -f "$APP_DIR/.env" ]]; then
    cp "$APP_DIR/.env.example" "$APP_DIR/.env"
    chmod 600 "$APP_DIR/.env"
    echo
    echo "Se creó $APP_DIR/.env desde el ejemplo. Llénalo y vuelve a correr este script:"
    echo "  sudo nano $APP_DIR/.env"
    exit 1
fi

echo "==> Revisando .env"
missing=()
for var in WA_TOKEN WA_PHONE_NUMBER_ID WA_VERIFY_TOKEN WA_APP_SECRET LLM_API_KEY; do
    val="$(grep -E "^${var}=" "$APP_DIR/.env" | head -1 | cut -d= -f2- || true)"
    case "$val" in
        ""|EAAG...|123456789012345|una-frase-secreta-larga|secreto-de-la-app|sk-or-...)
            missing+=("$var") ;;
    esac
done
if (( ${#missing[@]} )); then
    echo "Faltan valores reales en $APP_DIR/.env: ${missing[*]}"; exit 1
fi

echo "==> Entorno de Python"
[[ -d "$APP_DIR/venv" ]] || python3 -m venv "$APP_DIR/venv"
"$APP_DIR/venv/bin/pip" install -q --upgrade pip
"$APP_DIR/venv/bin/pip" install -q -r "$APP_DIR/requirements.txt"
if grep -qE '^CATALOG_SOURCE=firebird' "$APP_DIR/.env"; then
    "$APP_DIR/venv/bin/pip" install -q 'firebird-driver>=1.10'
fi
chown -R www-data:www-data "$APP_DIR"
chmod 600 "$APP_DIR/.env"

echo "==> Servicio systemd"
cp "$APP_DIR/abarrotes-bot.service" /etc/systemd/system/abarrotes-bot.service
systemctl daemon-reload
systemctl enable abarrotes-bot
systemctl restart abarrotes-bot

echo "==> Nginx"
site=/etc/nginx/sites-available/abarrotes-bot
if [[ ! -f "$site" ]]; then
    # Solo la primera vez: después certbot le agrega HTTPS a este archivo
    sed "s/__DOMAIN__/$DOMAIN/g" "$APP_DIR/deploy/nginx.conf.template" > "$site"
fi
ln -sf "$site" /etc/nginx/sites-enabled/abarrotes-bot
nginx -t
systemctl reload nginx

echo "==> Firewall"
if command -v ufw >/dev/null && ufw status | grep -q "Status: active"; then
    ufw allow 'Nginx Full'
fi

echo "==> HTTPS (Let's Encrypt)"
certbot --nginx -d "$DOMAIN" -m "$EMAIL" --agree-tos --non-interactive --redirect

echo "==> Comprobando"
sleep 2
curl -fsS http://127.0.0.1:5000/health >/dev/null && echo "Bot local: ok"
curl -fsS "https://$DOMAIN/health" >/dev/null && echo "Bot en https://$DOMAIN: ok"

echo
echo "Listo. En Meta > WhatsApp > Configuration > Webhook usa:"
echo "  Callback URL: https://$DOMAIN/webhook"
echo "  Verify token: el valor de WA_VERIFY_TOKEN en $APP_DIR/.env"
echo "Logs: sudo journalctl -u abarrotes-bot -f"
