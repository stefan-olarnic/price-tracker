import os
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy.orm import Session
from database import get_db, engine
from models import Base, User, Product
from auth import hash_password, verify_password

Base.metadata.create_all(bind=engine)

secret_key = os.getenv("SECRET_KEY")

if not secret_key:
    raise ValueError("SECRET_KEY environment variable is not set")

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key=secret_key)

TAILWIND = '<script src="https://cdn.tailwindcss.com"></script>'

def base_html(title, content):
    return f"""
    <!DOCTYPE html>
    <html lang="ro">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{title} - Price Tracker</title>
        {TAILWIND}
    </head>
    <body class="bg-gray-950 text-gray-100 min-h-screen">
        <nav class="bg-gray-900 border-b border-gray-800 px-6 py-4">
            <div class="max-w-5xl mx-auto flex justify-between items-center">
                <a href="/" class="text-xl font-bold text-indigo-400">Price Tracker</a>
            </div>
        </nav>
        <main class="max-w-5xl mx-auto px-6 py-10">
            {content}
        </main>
    </body>
    </html>
    """

def auth_page(title, form_action, submit_label, link_href, link_label, error=""):
    error_html = f'<p class="text-red-400 text-sm mb-4">{error}</p>' if error else ""
    return base_html(title, f"""
        <div class="max-w-md mx-auto bg-gray-900 rounded-2xl p-8 shadow-xl border border-gray-800">
            <h1 class="text-2xl font-bold mb-6 text-white">{title}</h1>
            {error_html}
            <form method="post" action="{form_action}" class="space-y-4">
                <input type="email" name="email" placeholder="Email"
                    class="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-indigo-500" required>
                <input type="password" name="password" placeholder="Parola"
                    class="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-indigo-500" required>
                <button type="submit"
                    class="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-semibold py-3 rounded-lg transition">
                    {submit_label}
                </button>
            </form>
            <p class="mt-4 text-gray-400 text-sm text-center">{link_label} <a href="{link_href}" class="text-indigo-400 hover:underline">click aici</a></p>
        </div>
    """)


def get_current_user(request: Request, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    return db.query(User).filter(User.id == user_id).first()


@app.get("/", response_class=HTMLResponse)
def home(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if user:
        return RedirectResponse(url="/dashboard")
    return base_html("Acasa", """
        <div class="text-center py-20">
            <h1 class="text-5xl font-bold text-white mb-4">Price Tracker</h1>
            <p class="text-gray-400 text-lg mb-10">Monitorizeaza preturile si primeste alerte pe Telegram.</p>
            <div class="flex justify-center gap-4">
                <a href="/register" class="bg-indigo-600 hover:bg-indigo-700 text-white font-semibold px-8 py-3 rounded-lg transition">Inregistrare</a>
                <a href="/login" class="bg-gray-800 hover:bg-gray-700 text-white font-semibold px-8 py-3 rounded-lg transition">Login</a>
            </div>
        </div>
    """)


@app.get("/register", response_class=HTMLResponse)
def register_page():
    return auth_page("Inregistrare", "/register", "Creeaza cont", "/login", "Ai deja cont?")


@app.post("/register")
def register(email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        return HTMLResponse(auth_page("Inregistrare", "/register", "Creeaza cont", "/login", "Ai deja cont?", "Email deja inregistrat."), status_code=400)

    user = User(email=email, password=hash_password(password))
    db.add(user)
    db.commit()
    return RedirectResponse(url="/login", status_code=303)


@app.get("/login", response_class=HTMLResponse)
def login_page():
    return auth_page("Login", "/login", "Intra in cont", "/register", "Nu ai cont?")


@app.post("/login")
def login(request: Request, email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.password):
        return HTMLResponse(auth_page("Login", "/login", "Intra in cont", "/register", "Nu ai cont?", "Email sau parola gresite."), status_code=400)

    request.session["user_id"] = user.id
    return RedirectResponse(url="/dashboard", status_code=303)


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login")

    products = db.query(Product).filter(Product.user_id == user.id).all()

    products_rows = ""
    for p in products:
        products_rows += f"""
        <tr class="border-t border-gray-800 hover:bg-gray-800 transition">
            <td class="py-3 px-4 text-gray-200">{p.name}</td>
            <td class="py-3 px-4 text-indigo-400 font-semibold">{p.target_price} RON</td>
            <td class="py-3 px-4">
                <a href="{p.url}" target="_blank" class="text-indigo-400 hover:underline">Vezi produs</a>
            </td>
            <td class="py-3 px-4">
                <a href="/delete/{p.id}" class="text-red-400 hover:text-red-300 text-sm font-medium">Sterge</a>
            </td>
        </tr>
        """

    empty_state = "" if products else '<p class="text-gray-500 text-sm py-4">Nu ai produse adaugate inca.</p>'

    chat_status = f'<span class="text-green-400 font-medium">{user.chat_id}</span>' if user.chat_id else '<span class="text-red-400">nesalvat</span>'

    content = f"""
        <div class="flex justify-between items-center mb-8">
            <div>
                <h1 class="text-2xl font-bold text-white">Dashboard</h1>
                <p class="text-gray-400 text-sm mt-1">{user.email}</p>
            </div>
            <a href="/logout" class="text-gray-400 hover:text-white text-sm transition">Logout</a>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
            <div class="bg-gray-900 rounded-2xl p-6 border border-gray-800">
                <h2 class="text-lg font-semibold text-white mb-4">Adauga produs</h2>
                <form method="post" action="/add" class="space-y-3">
                    <input type="text" name="name" placeholder="Nume produs"
                        class="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2.5 text-white placeholder-gray-500 focus:outline-none focus:border-indigo-500 text-sm" required>
                    <input type="text" name="url" placeholder="URL produs"
                        class="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2.5 text-white placeholder-gray-500 focus:outline-none focus:border-indigo-500 text-sm" required>
                    <input type="number" name="target_price" placeholder="Target price (RON)" step="0.01"
                        class="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2.5 text-white placeholder-gray-500 focus:outline-none focus:border-indigo-500 text-sm" required>
                    <button type="submit"
                        class="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-semibold py-2.5 rounded-lg transition text-sm">
                        Adauga produs
                    </button>
                </form>
            </div>

            <div class="bg-gray-900 rounded-2xl p-6 border border-gray-800">
                <h2 class="text-lg font-semibold text-white mb-1">Setari Telegram</h2>
                <p class="text-gray-400 text-sm mb-4">Chat ID curent: {chat_status}</p>
                <form method="post" action="/save-chat-id" class="space-y-3">
                    <input type="text" name="chat_id" placeholder="Chat ID Telegram"
                        class="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2.5 text-white placeholder-gray-500 focus:outline-none focus:border-indigo-500 text-sm" required>
                    <button type="submit"
                        class="w-full bg-gray-700 hover:bg-gray-600 text-white font-semibold py-2.5 rounded-lg transition text-sm">
                        Salveaza Chat ID
                    </button>
                </form>
            </div>
        </div>

        <div class="bg-gray-900 rounded-2xl border border-gray-800 overflow-hidden">
            <div class="px-6 py-4 border-b border-gray-800">
                <h2 class="text-lg font-semibold text-white">Produsele tale</h2>
            </div>
            {empty_state}
            <table class="w-full text-sm {'hidden' if not products else ''}">
                <thead>
                    <tr class="text-gray-400 text-left">
                        <th class="py-3 px-4 font-medium">Produs</th>
                        <th class="py-3 px-4 font-medium">Target</th>
                        <th class="py-3 px-4 font-medium">Link</th>
                        <th class="py-3 px-4 font-medium">Actiuni</th>
                    </tr>
                </thead>
                <tbody>
                    {products_rows}
                </tbody>
            </table>
        </div>
    """

    return base_html("Dashboard", content)


@app.post("/add")
def add_product(request: Request, name: str = Form(...), url: str = Form(...), target_price: float = Form(...), db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login")

    product = Product(name=name, url=url, target_price=target_price, user_id=user.id)
    db.add(product)
    db.commit()
    return RedirectResponse(url="/dashboard", status_code=303)


@app.get("/delete/{product_id}")
def delete_product(product_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login")

    product = db.query(Product).filter(Product.id == product_id, Product.user_id == user.id).first()
    if product:
        db.delete(product)
        db.commit()
    return RedirectResponse(url="/dashboard", status_code=303)


@app.post("/save-chat-id")
def save_chat_id(request: Request, chat_id: str = Form(...), db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login")

    user.chat_id = chat_id
    db.commit()
    return RedirectResponse(url="/dashboard", status_code=303)


@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login")
