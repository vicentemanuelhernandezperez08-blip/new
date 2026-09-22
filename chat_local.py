"""Prueba el bot en la terminal sin WhatsApp: python chat_local.py"""
import agent
import config
import store

config.OWNER_PHONE = ""  # no enviar avisos reales durante la prueba
store.init()
phone = "5210000000000"
print(f"Chat de prueba con {config.STORE_NAME}. Escribe 'salir' para terminar, '/reset' para reiniciar.\n")
while True:
    t = input("Tú: ").strip()
    if t.lower() == "salir":
        break
    if t:
        print("Bot:", agent.reply(phone, t), "\n")
