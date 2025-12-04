from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from jose import jwt
from passlib.context import CryptContext
from motor.motor_asyncio import AsyncIOMotorClient
from odmantic import AIOEngine, Model
from starlette.middleware.sessions import SessionMiddleware
from fastapi.middleware.cors import CORSMiddleware

# Конфигурация приложения
APP_CONFIG = {
    "SECRET_KEY": "very_secret_key",
    "ALGORITHM": "HS256",
    "DATABASE_URL": "mongodb://admin:admin@db:27017/users_db",
    "TEMPLATES_DIR": "templates"
}

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(SessionMiddleware, secret_key=APP_CONFIG["SECRET_KEY"])

password_manager = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Подключение к MongoDB
dbClient = AsyncIOMotorClient(APP_CONFIG["DATABASE_URL"])
db = AIOEngine(client=dbClient, database="chat_db")

# Модели данных
class UserProfile(Model):
    username: str
    encrypted_password: str

class Chat(Model):
    title: str

# Утилиты для работы с паролями
def encrypt_password(password: str) -> str:
    return password_manager.hash(password)

def check_password(plain_password: str, encrypted_password: str) -> bool:
    return password_manager.verify(plain_password, encrypted_password)

# Генерация токена
def generate_token(user_data: dict) -> str:
    payload = user_data.copy()
    return jwt.encode(payload, APP_CONFIG["SECRET_KEY"], algorithm=APP_CONFIG["ALGORITHM"])

# Инициализация шаблонов
templates = Jinja2Templates(directory=APP_CONFIG["TEMPLATES_DIR"])

# Маршруты
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    user = request.session.get("username")
    return templates.TemplateResponse("index.html", {"request": request, "user": user})

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@app.post("/register", response_class=HTMLResponse)
async def register_user(request: Request, username: str = Form(...), password: str = Form(...)):
    existing_user = await db.find_one(UserProfile, UserProfile.username == username)
    if existing_user:
        return templates.TemplateResponse("register.html", {"request": request, "error": "Username already exists."})

    user = UserProfile(username=username, encrypted_password=encrypt_password(password))
    await db.save(user)
    request.session["username"] = user.username
    return RedirectResponse("/dashboard", status_code=302)

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login", response_class=HTMLResponse)
async def login_user(request: Request, username: str = Form(...), password: str = Form(...)):
    user = await db.find_one(UserProfile, UserProfile.username == username)
    if not user or not check_password(password, user.encrypted_password):
        return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid credentials."})
    request.session["username"] = user.username
    return RedirectResponse("/dashboard", status_code=302)

@app.get("/logout")
async def logout(request: Request):
    request.session.pop("username", None)
    return RedirectResponse("/", status_code=302)

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    if not request.session.get("username"):
        return RedirectResponse("/login", status_code=302)
    
    user = request.session.get("username")
    return templates.TemplateResponse("dashboard.html", {"request": request, "user": user})

# Маршрут для создания беседы
@app.get("/create_chat", response_class=HTMLResponse)
async def create_chat_page(request: Request):
    if not request.session.get("username"):
        return RedirectResponse("/login", status_code=302)
    return templates.TemplateResponse("create_chat.html", {"request": request})

@app.post("/create_chat", response_class=HTMLResponse)
async def create_chat(request: Request, chat_name: str = Form(...)):
    if not request.session.get("username"):
        return RedirectResponse("/login", status_code=302)

    if len(chat_name) < 6:
        return templates.TemplateResponse("create_chat.html", {"request": request, "error": "Название беседы должно содержать минимум 6 символов."})

    existing_chat = await db.find_one(Chat, Chat.title == chat_name)
    if existing_chat:
        return templates.TemplateResponse("create_chat.html", {"request": request, "error": "Беседа с таким названием уже существует."})

    new_chat = Chat(title=chat_name)
    await db.save(new_chat)

    return RedirectResponse(url=f"/chat/{chat_name}", status_code=303)

@app.get("/search_chats", response_class=HTMLResponse)
async def search_chats_page(request: Request):
    if not request.session.get("username"):
        return RedirectResponse("/login", status_code=302)

    chats = await db.find(Chat)
    print(chats)
    return templates.TemplateResponse("search_chats.html", {"request": request, "chats": chats})

@app.post("/search_chats", response_class=HTMLResponse)
async def search_chats(request: Request, search_query: str = Form(...)):
    if not request.session.get("username"):
        return RedirectResponse("/login", status_code=302)

    if len(search_query) < 6:
        return templates.TemplateResponse("search_chats.html", {"request": request, "error": "Запрос должен содержать минимум 6 символов."})

    chats = await db.find(Chat, Chat.title.match(search_query))
    print(chats)
    return templates.TemplateResponse("search_chats.html", {"request": request, "chats": chats, "query": search_query})

@app.post("/delete_chat/{chat_name}")
async def delete_chat(chat_name: str, request: Request):
    if not request.session.get("username"):
        return RedirectResponse("/login", status_code=302)

    chat_to_delete = await db.find_one(Chat, Chat.title == chat_name)

    if chat_to_delete:
        await db.delete(chat_to_delete)
        return RedirectResponse("/dashboard", status_code=303)
    else:
        return templates.TemplateResponse("chat.html", {"request": request, "error": "Беседа не найдена."})

@app.get("/chat/{chat_name}", response_class=HTMLResponse)
async def chat_page(request: Request, chat_name: str):
    if not request.session.get("username"):
        return RedirectResponse("/login", status_code=302)
    user = request.session.get("username")
    token = generate_token({"sub": user})
    return templates.TemplateResponse("chat.html", {"request": request, "chat_name": chat_name, "user": user, "token": token})

# Запуск приложения
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
