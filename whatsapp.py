"""Envío de mensajes vía WhatsApp Cloud API."""
import hashlib
import hmac

import requests

import config

API = f"https://graph.facebook.com/{config.GRAPH_VERSION}/{config.WA_PHONE_NUMBER_ID}/messages"


def _post(payload):
    try:
        r = requests.post(API, json=payload, timeout=20,
                          headers={"Authorization": f"Bearer {config.WA_TOKEN}"})
    except requests.RequestException as e:  # red caída, timeout, etc.: no tumbar al llamador
        print("[wa] error de red:", e)
        return None
    if r.status_code >= 300:
        print("[wa] error", r.status_code, r.text)
    return r


def _fix_mx(to: str) -> str:
    """Meta entrega números de México como 521XXXXXXXXXX, pero para enviar suele requerir 52XXXXXXXXXX."""
    return "52" + to[3:] if to.startswith("521") and len(to) == 13 else to


def send_text(to: str, body: str):
    to = _fix_mx(to)
    # WhatsApp permite hasta 4096 caracteres por mensaje
    for i in range(0, len(body), 4000):
        _post({"messaging_product": "whatsapp", "to": to, "type": "text",
               "text": {"preview_url": False, "body": body[i:i + 4000]}})


def mark_read(wamid: str):
    _post({"messaging_product": "whatsapp", "status": "read", "message_id": wamid})


def valid_signature(raw_body: bytes, header: str) -> bool:
    if not config.WA_APP_SECRET:
        return True  # sin secreto configurado no se valida (solo para pruebas)
    expected = "sha256=" + hmac.new(config.WA_APP_SECRET.encode(), raw_body,
                                    hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, header or "")
