import os
import requests
import time
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

def get_updates(offset=None):
    params = {"timeout": 30, "offset": offset}
    response = requests.get(f"{BASE_URL}/getUpdates", params=params)
    return response.json()

def send_message(chat_id, text):
    requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": chat_id, "text": text})

def handle_updates(updates):
    for update in updates:
        message = update.get("message", {})
        text = message.get("text", "")
        chat_id = message.get("chat", {}).get("id")

        if text == "/start" and chat_id:
            send_message(chat_id, f"Salut! Chat ID-ul tau este:\n\n{chat_id}\n\nCopiaza acest numar si pune-l in aplicatie la sectiunea Setari Telegram.")

def main():
    print("Bot listener pornit...")
    offset = None

    while True:
        try:
            data = get_updates(offset)
            updates = data.get("result", [])

            if updates:
                handle_updates(updates)
                offset = updates[-1]["update_id"] + 1

        except Exception as e:
            print(f"Eroare: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
