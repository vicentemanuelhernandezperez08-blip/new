"""Servidor Flask: webhook de WhatsApp Cloud API."""
import threading

from flask import Flask, abort, jsonify, request

import agent
import config
import store
import whatsapp

app = Flask(__name__)
store.init()


@app.get("/webhook")
def verify():
    """Verificación inicial que hace Meta al registrar el webhook."""
    if (request.args.get("hub.mode") == "subscribe"
            and request.args.get("hub.verify_token") == config.WA_VERIFY_TOKEN):
        return request.args.get("hub.challenge", ""), 200
    abort(403)


def _handle(phone, wamid, text):
    try:
        whatsapp.mark_read(wamid)
        answer = agent.reply(phone, text)
        whatsapp.send_text(phone, answer)
    except Exception as e:
        print("[bot] error:", e)
        whatsapp.send_text(phone, "Perdón, tuve un problema. Intenta de nuevo en un momento 🙏")


@app.post("/webhook")
def incoming():
    if not whatsapp.valid_signature(request.get_data(), request.headers.get("X-Hub-Signature-256")):
        abort(401)
    data = request.get_json(silent=True) or {}
    for entry in data.get("entry", []):
        for change in entry.get("changes", []):
            for m in change.get("value", {}).get("messages", []):
                if store.already_processed(m["id"]):
                    continue
                phone = m["from"]
                if m.get("type") == "text":
                    text = m["text"]["body"]
                elif m.get("type") == "interactive":
                    it = m["interactive"]
                    text = (it.get("button_reply") or it.get("list_reply") or {}).get("title", "")
                else:
                    whatsapp.send_text(phone, "Por ahora solo leo mensajes de texto ✍️")
                    continue
                # Responder a Meta de inmediato y procesar en segundo plano
                threading.Thread(target=_handle, args=(phone, m["id"], text), daemon=True).start()
    return "ok", 200


@app.get("/pedidos")
def pedidos():
    """Lista rápida de pedidos. Protégela (Tailscale o token) antes de exponerla."""
    if request.args.get("token") != config.WA_VERIFY_TOKEN:
        abort(403)
    return jsonify(store.list_orders(request.args.get("status")))


@app.get("/health")
def health():
    return "ok"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
