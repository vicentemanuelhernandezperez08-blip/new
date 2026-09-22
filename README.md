# Bot de WhatsApp — Abarrotes Hernández

Bot con IA que atiende clientes por WhatsApp: consulta precios y existencias reales
(CSV o Eleventa/Firebird), arma pedidos, pide confirmación, los guarda y te avisa por WhatsApp.

## Archivos
| Archivo | Qué hace |
|---|---|
| `app.py` | Servidor Flask con el webhook de WhatsApp Cloud API |
| `agent.py` | LLM + herramientas `buscar_productos` y `registrar_pedido` |
| `catalog.py` | Lee productos de CSV o de Eleventa (solo lectura, caché 5 min) |
| `whatsapp.py` | Envía mensajes y valida la firma de Meta |
| `store.py` | SQLite: historial, pedidos, mensajes ya procesados |
| `chat_local.py` | Prueba el bot en la terminal sin WhatsApp |

## 1. Probar local (5 min)
```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env      # pon al menos LLM_API_KEY
python chat_local.py
```
Prueba: "¿tienes coca de 2 litros?", "quiero 2 cocas de 600 y un kilo de frijol", etc.

## 2. Configurar WhatsApp Cloud API
1. developers.facebook.com → Crear app → tipo **Business** → agregar producto **WhatsApp**.
2. En *API Setup* copia **Phone number ID** → `WA_PHONE_NUMBER_ID`.
3. Crea un **System User** en Business Settings, dale acceso a la app y genera un token
   permanente con permisos `whatsapp_business_messaging` y `whatsapp_business_management` → `WA_TOKEN`.
4. App Settings → Basic → **App Secret** → `WA_APP_SECRET`.
5. Agrega y verifica el número real de la tienda (no puede estar activo en la app de WhatsApp normal).

## 3. Desplegar en el VPS (Hostinger)
Requisitos: VPS con Ubuntu/Debian, un subdominio (ej. `bot.tudominio.com`) con registro **A**
apuntando a la IP del VPS, y los puertos 80/443 abiertos.

```bash
ssh root@IP-DEL-VPS
git clone https://github.com/vicentemanuelhernandezperez08-blip/new.git abarrotes-bot
cd abarrotes-bot
sudo ./deploy/install.sh bot.tudominio.com tu@correo.com   # 1ª vez: crea /opt/abarrotes-bot/.env y se detiene
sudo nano /opt/abarrotes-bot/.env                          # llena tokens de WhatsApp y LLM
sudo ./deploy/install.sh bot.tudominio.com tu@correo.com   # instala todo
```
El script instala Python, Nginx y certbot; copia el código a `/opt/abarrotes-bot`; crea el venv;
instala el servicio `abarrotes-bot`; configura Nginx con HTTPS (Let's Encrypt) y comprueba `/health`.
No arranca si faltan valores reales en `.env` (incluido `WA_APP_SECRET`).

En Meta → WhatsApp → Configuration → Webhook:
- Callback URL: `https://bot.tudominio.com/webhook`
- Verify token: el mismo de `WA_VERIFY_TOKEN`
- Suscríbete al campo **messages**.

**Actualizar:** `cd abarrotes-bot && git pull && sudo ./deploy/install.sh bot.tudominio.com tu@correo.com`
(no toca `.env` ni la base de pedidos).

**Logs:** `sudo journalctl -u abarrotes-bot -f`

## 4. Conectar Eleventa (inventario real)
El VPS debe alcanzar la PC de la tienda por **Tailscale** (puerto Firebird 3050).
```
CATALOG_SOURCE=firebird
FB_DSN=100.x.x.x:C:/Eleventa/pdvdata.fdb   # IP Tailscale de la PC + ruta real del .fdb
```
Descomenta `firebird-driver` en requirements.txt e instálalo. Usa un usuario Firebird de
solo lectura si puedes. Si tu versión de Eleventa usa otros nombres de columna, ajusta
`FB_COL_*` en `.env`. Si la PC está apagada, el bot sigue con el último catálogo en caché.

## Ver pedidos
`GET /pedidos?token=<WA_VERIFY_TOKEN>`. Nginx solo la permite desde Tailscale o desde el propio VPS
(`curl "http://127.0.0.1:5000/pedidos?token=..."`). Cada pedido nuevo
también llega a `OWNER_PHONE` por WhatsApp.

## Costos a tener en cuenta
- WhatsApp: las conversaciones que **inicia el cliente** (servicio) no tienen costo en la
  ventana de 24 h; mensajes de plantilla/marketing sí se cobran. Revisa la tabla de precios de Meta para México.
- LLM: modelos como DeepSeek cuestan centavos por conversación. Cambia `LLM_MODEL` para comparar.

## Comandos del cliente
`/reset` o `reiniciar` — borra el historial de esa conversación.
