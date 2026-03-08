import requests
import sys
import os
sys.path.append(os.path.dirname(__file__))
from dotenv import load_dotenv
load_dotenv()

from playwright.sync_api import sync_playwright
from database import SessionLocal
from models import Product, User


def get_price(url):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_selector(".product-new-price", timeout=60000)
        price = page.locator(".product-new-price").first.inner_text()
        browser.close()

        price = price.replace("Lei", "").strip()
        price = price.replace(".", "").replace(",", ".")
        return float(price)


def send_message(chat_id, text):
    bot_token = os.getenv("BOT_TOKEN")
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    requests.post(url, json={"chat_id": chat_id, "text": text})


def check_prices():
    db = SessionLocal()
    products = db.query(Product).all()

    for product in products:
        try:
            price = get_price(product.url)
            print(f"{product.name}: {price} RON (target: {product.target_price} RON)")

            if price <= product.target_price:
                user = db.query(User).filter(User.id == product.user_id).first()
                if user and user.chat_id:
                    send_message(user.chat_id, f"Price drop!\n{product.name}\nPret: {price} RON\nTarget: {product.target_price} RON\n{product.url}")
        except Exception as e:
            print(f"Eroare la {product.name}: {e}")

    db.close()


if __name__ == "__main__":
    check_prices()
