"""Agente con LLM + herramientas (buscar productos, registrar pedido)."""
import json

from openai import OpenAI

import catalog
import config
import store
import whatsapp

client = OpenAI(base_url=config.LLM_BASE_URL, api_key=config.LLM_API_KEY)

SYSTEM = f"""Eres el asistente de WhatsApp de {config.STORE_NAME}, una tienda de abarrotes de barrio.
Hablas español de México, cálido y breve (mensajes cortos, estilo WhatsApp, sin markdown pesado).

Información de la tienda: {config.STORE_INFO}

Reglas:
- NUNCA inventes precios ni existencias. Usa siempre la herramienta buscar_productos.
- Si un producto no aparece o no está disponible, dilo y sugiere alternativas del resultado.
- Para levantar un pedido: confirma productos, cantidades, total, nombre y dirección de entrega.
  Muestra el resumen y pide un "sí" explícito ANTES de llamar a registrar_pedido.
- Precios en pesos mexicanos con formato $00.00.
- Si piden algo fuera de la tienda (quejas serias, facturas, proveedores), di que el encargado les contactará.
"""

TOOLS = [
    {"type": "function", "function": {
        "name": "buscar_productos",
        "description": "Busca productos del inventario por nombre, marca o código. Devuelve precio y disponibilidad.",
        "parameters": {"type": "object", "properties": {
            "consulta": {"type": "string", "description": "Ej: 'coca 600', 'huevo', 'aceite 1 litro'"}},
            "required": ["consulta"]}}},
    {"type": "function", "function": {
        "name": "registrar_pedido",
        "description": "Registra el pedido SOLO después de que el cliente confirmó el resumen.",
        "parameters": {"type": "object", "properties": {
            "nombre": {"type": "string"},
            "direccion": {"type": "string"},
            "productos": {"type": "array", "items": {"type": "object", "properties": {
                "codigo": {"type": "string"}, "cantidad": {"type": "number"}},
                "required": ["codigo", "cantidad"]}},
            "notas": {"type": "string"}},
            "required": ["nombre", "direccion", "productos"]}}},
]


def _registrar_pedido(phone, args):
    items, total, faltantes = [], 0.0, []
    for p in args.get("productos", []):
        prod = catalog.get(p["codigo"])
        if not prod:
            faltantes.append(p["codigo"])
            continue
        sub = round(prod["precio"] * float(p["cantidad"]), 2)
        items.append({"codigo": prod["codigo"], "nombre": prod["nombre"],
                      "cantidad": p["cantidad"], "precio": prod["precio"], "subtotal": sub})
        total += sub
    if not items:
        return {"ok": False, "error": "Ningún código válido", "faltantes": faltantes}
    total = round(total, 2)
    oid = store.create_order(phone, args.get("nombre", ""), args.get("direccion", ""),
                             items, total, args.get("notas", ""))
    if config.OWNER_PHONE:
        lines = "\n".join(f"- {i['cantidad']} x {i['nombre']} = ${i['subtotal']:.2f}" for i in items)
        whatsapp.send_text(config.OWNER_PHONE,
                           f"🛒 Pedido #{oid}\nCliente: {args.get('nombre')} (+{phone})\n"
                           f"Dirección: {args.get('direccion')}\n{lines}\nTotal: ${total:.2f}\n"
                           f"Notas: {args.get('notas', '')}")
    return {"ok": True, "pedido": oid, "total": total, "items": items, "faltantes": faltantes}


def _run_tool(phone, name, args):
    if name == "buscar_productos":
        return catalog.search(args.get("consulta", ""))
    if name == "registrar_pedido":
        return _registrar_pedido(phone, args)
    return {"error": f"herramienta desconocida {name}"}


def reply(phone: str, text: str) -> str:
    if text.strip().lower() in {"/reset", "reiniciar"}:
        store.reset(phone)
        return "Listo, empezamos de nuevo. ¿En qué te ayudo?"

    store.add_message(phone, "user", text)
    messages = [{"role": "system", "content": SYSTEM}] + store.history(phone, config.HISTORY_TURNS)

    for _ in range(6):  # máximo de rondas de herramientas
        resp = client.chat.completions.create(model=config.LLM_MODEL, messages=messages,
                                              tools=TOOLS, temperature=0.3)
        msg = resp.choices[0].message
        if not msg.tool_calls:
            answer = (msg.content or "").strip() or "Perdón, no entendí. ¿Me lo repites?"
            store.add_message(phone, "assistant", answer)
            return answer
        messages.append({"role": "assistant", "content": msg.content or "",
                         "tool_calls": [tc.model_dump() for tc in msg.tool_calls]})
        for tc in msg.tool_calls:
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            result = _run_tool(phone, tc.function.name, args)
            messages.append({"role": "tool", "tool_call_id": tc.id,
                             "content": json.dumps(result, ensure_ascii=False)})
    return "Estoy teniendo problemas, en un momento te atiende una persona."
