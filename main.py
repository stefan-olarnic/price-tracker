from fastapi import FastAPI, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy.orm import Session
from database import get_db, engine
from models import Base, User, Product
from auth import hash_password, verify_password
import os
from dotenv import load_dotenv
load_dotenv()

Base.metadata.create_all(bind=engine)

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key=os.getenv("SECRET_KEY"))


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
    return """
    <html>
        <body>
            <h1>Price Tracker</h1>
            <a href="/register">Inregistrare</a> |
            <a href="/login">Login</a>
        </body>
    </html>
    """


@app.get("/register", response_class=HTMLResponse)
def register_page():
    return """
    <html>
        <body>
            <h1>Inregistrare</h1>
            <form method="post" action="/register">
                <input type="email" name="email" placeholder="Email" required><br><br>
                <input type="password" name="password" placeholder="Parola" required><br><br>
                <button type="submit">Inregistreaza-te</button>
            </form>
            <p>Ai deja cont? <a href="/login">Login</a></p>
        </body>
    </html>
    """


@app.post("/register")
def register(email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        return HTMLResponse("<p>Email deja inregistrat. <a href='/register'>Incearca din nou</a></p>", status_code=400)

    user = User(email=email, password=hash_password(password))
    db.add(user)
    db.commit()
    return RedirectResponse(url="/login", status_code=303)


@app.get("/login", response_class=HTMLResponse)
def login_page():
    return """
    <html>
        <body>
            <h1>Login</h1>
            <form method="post" action="/login">
                <input type="email" name="email" placeholder="Email" required><br><br>
                <input type="password" name="password" placeholder="Parola" required><br><br>
                <button type="submit">Intra in cont</button>
            </form>
            <p>Nu ai cont? <a href="/register">Inregistreaza-te</a></p>
        </body>
    </html>
    """


@app.post("/login")
def login(request: Request, email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.password):
        return HTMLResponse("<p>Email sau parola gresite. <a href='/login'>Incearca din nou</a></p>", status_code=400)

    request.session["user_id"] = user.id
    return RedirectResponse(url="/dashboard", status_code=303)


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login")

    products = db.query(Product).filter(Product.user_id == user.id).all()

    products_html = ""
    for p in products:
        products_html += f"""
        <tr>
            <td>{p.name}</td>
            <td>{p.target_price} RON</td>
            <td><a href="{p.url}" target="_blank">Link</a></td>
            <td><a href="/delete/{p.id}">Sterge</a></td>
        </tr>
        """

    return f"""
    <html>
        <body>
            <h1>Bun venit, {user.email}!</h1>
            <h2>Adauga produs</h2>
            <form method="post" action="/add">
                <input type="text" name="name" placeholder="Nume produs" required><br><br>
                <input type="text" name="url" placeholder="URL produs" required><br><br>
                <input type="number" name="target_price" placeholder="Target price (RON)" step="0.01" required><br><br>
                <button type="submit">Adauga</button>
            </form>
            <h2>Produsele tale</h2>
            <table border="1">
                <tr>
                    <th>Nume</th>
                    <th>Target</th>
                    <th>Link</th>
                    <th>Actiuni</th>
                </tr>
                {products_html}
            </table>
            <h2>Setari Telegram</h2>
            <p>Chat ID curent: <b>{user.chat_id or "nesalvat"}</b></p>
            <form method="post" action="/save-chat-id">
                <input type="text" name="chat_id" placeholder="Chat ID Telegram" required><br><br>
                <button type="submit">Salveaza</button>
            </form>
            <br>
            <a href="/logout">Logout</a>
        </body>
    </html>
    """


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
