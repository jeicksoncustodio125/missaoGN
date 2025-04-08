import os
from flask import Flask, request
import requests
from dotenv import load_dotenv

# Carrega variáveis do .env
load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TAPE_TOKEN = os.getenv("TAPE_TOKEN")
COLLECTION_ID_FUNCIONARIOS = os.getenv("COLLECTION_ID")
COLLECTION_ID_VIAGENS = os.getenv("COLLECTION_ID_VIAGENS")  # novo campo no .env
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

app = Flask(__name__)

# Armazena estado temporário dos usuários
usuarios = {}

# Endpoint do Telegram
@app.route(f"/{TELEGRAM_TOKEN}", methods=["POST"])
def telegram_webhook():
    data = request.json

    if "message" in data:
        chat_id = data["message"]["chat"]["id"]
        texto = data["message"]["text"]

        if texto == "/start":
            enviar_mensagem(chat_id, "👋 Bem-vindo à MissãoGN!\nPor favor, envie seu nome para cadastro.")
            usuarios[chat_id] = {"estado": "aguardando_nome"}

        elif texto == "/minhas_viagens":
            viagens = buscar_viagens_do_usuario(chat_id)
            if viagens:
                resposta = "🗓️ Suas próximas viagens:\n\n" + "\n".join(viagens)
            else:
                resposta = "❌ Nenhuma viagem encontrada para você."
            enviar_mensagem(chat_id, resposta)

        elif chat_id in usuarios and usuarios[chat_id]["estado"] == "aguardando_nome":
            nome = texto.strip()
            sucesso = cadastrar_funcionario_tape(nome, chat_id)
            if sucesso:
                enviar_mensagem(chat_id, f"✅ {nome}, você foi registrado com sucesso! Agora receberá alertas de missão.")
            else:
                enviar_mensagem(chat_id, "❌ Erro ao registrar no sistema. Tente novamente.")
            usuarios.pop(chat_id, None)

    return "ok", 200

# Endpoint para receber alertas do Tape
@app.route("/webhook/viagem", methods=["POST"])
def webhook_viagem():
    data = request.json
    nome = data.get("nome", "Agente")
    destino = data.get("destino", "desconhecido")
    horario = data.get("horario", "sem horário")
    chat_id = data.get("chat_id")

    if chat_id:
        mensagem = (
            f"🕒 Missão em 1 hora!\n"
            f"👤 Agente: {nome}\n"
            f"📍 Destino: {destino}\n"
            f"🕓 Horário: {horario}"
        )
        enviar_mensagem(chat_id, mensagem)
        return "ok", 200
    return "Faltando chat_id", 400

# Envia mensagem no Telegram
def enviar_mensagem(chat_id, texto):
    requests.post(f"{TELEGRAM_API_URL}/sendMessage", json={
        "chat_id": chat_id,
        "text": texto
    })

# Cadastra funcionário no Tape
def cadastrar_funcionario_tape(nome, chat_id):
    url = "https://SEU_SUBDOMINIO.tapeapp.com/api/v1/items"  # substitua pelo seu subdomínio
    headers = {
        "Authorization": f"Bearer {TAPE_TOKEN}",
        "Content-Type": "application/json"
    }
    body = {
        "collection_id": COLLECTION_ID_FUNCIONARIOS,
        "fields": {
            "nome": nome,
            "telegram_chat_id": chat_id
        }
    }
    response = requests.post(url, headers=headers, json=body)
    return response.status_code == 200

# Busca viagens do usuário no Tape
def buscar_viagens_do_usuario(chat_id):
    url = "https://SEU_SUBDOMINIO.tapeapp.com/api/v1/items"  # substitua pelo seu subdomínio
    headers = {
        "Authorization": f"Bearer {TAPE_TOKEN}",
        "Content-Type": "application/json"
    }

    response = requests.get(
        url,
        headers=headers,
        params={
            "collection_id": COLLECTION_ID_VIAGENS
        }
    )

    if response.status_code == 200:
        data = response.json()
        viagens = []
        for item in data.get("items", []):
            fields = item.get("fields", {})
            if str(fields.get("telegram_chat_id")) == str(chat_id):
                destino = fields.get("destino", "Desconhecido")
                horario = fields.get("horario", "Sem horário")
                viagens.append(f"📍 {destino} às {horario}")
        return viagens
    return None

if __name__ == "__main__":
    app.run(debug=True)
