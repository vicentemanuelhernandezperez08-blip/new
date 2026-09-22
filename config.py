"""Configuración leída desde variables de entorno (.env)."""
import os
from dotenv import load_dotenv

load_dotenv()

# --- WhatsApp Cloud API ---
WA_TOKEN = os.getenv("WA_TOKEN", "")                 # Token permanente (System User)
WA_PHONE_NUMBER_ID = os.getenv("WA_PHONE_NUMBER_ID", "")
WA_VERIFY_TOKEN = os.getenv("WA_VERIFY_TOKEN", "cambia-esto")
WA_APP_SECRET = os.getenv("WA_APP_SECRET", "")       # Para validar firma del webhook
GRAPH_VERSION = os.getenv("GRAPH_VERSION", "v21.0")

# --- LLM (OpenRouter, Z.ai o cualquier API compatible con OpenAI) ---
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://openrouter.ai/api/v1")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "deepseek/deepseek-chat")

# --- Negocio ---
STORE_NAME = os.getenv("STORE_NAME", "Abarrotes Hernández")
STORE_INFO = os.getenv(
    "STORE_INFO",
    "Horario: lunes a domingo 7:00-22:00. Ubicación: Comitán de Domínguez, Chiapas. "
    "Entrega a domicilio en colonias cercanas, pedido mínimo $150. "
    "Pago en efectivo o transferencia.",
)
OWNER_PHONE = os.getenv("OWNER_PHONE", "")  # 52XXXXXXXXXX, recibe aviso de pedidos nuevos

# --- Catálogo ---
CATALOG_SOURCE = os.getenv("CATALOG_SOURCE", "csv")  # "csv" o "firebird"
CATALOG_CSV = os.getenv("CATALOG_CSV", "productos_ejemplo.csv")
FB_DSN = os.getenv("FB_DSN", "localhost:C:/Eleventa/pdvdata.fdb")
FB_USER = os.getenv("FB_USER", "SYSDBA")
FB_PASSWORD = os.getenv("FB_PASSWORD", "masterkey")
# Columnas de Eleventa (ajústalas si tu versión usa otros nombres)
FB_TABLE = os.getenv("FB_TABLE", "PRODUCTOS")
FB_COL_CODE = os.getenv("FB_COL_CODE", "CODIGO")
FB_COL_NAME = os.getenv("FB_COL_NAME", "DESCRIPCION")
FB_COL_PRICE = os.getenv("FB_COL_PRICE", "PVENTA")
FB_COL_STOCK = os.getenv("FB_COL_STOCK", "DINVENTARIO")

DB_PATH = os.getenv("DB_PATH", "bot.db")
HISTORY_TURNS = int(os.getenv("HISTORY_TURNS", "12"))
