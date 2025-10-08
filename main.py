from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from jose import JWTError, jwt
from typing import Dict, List
import logging

# Настройка логирования
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = FastAPI()

APP_CONFIG = {
    "SECRET_KEY": "very_secret_key",
    "ALGORITHM": "HS256",
}

# Карта для хранения подключений
connected_clients: Dict[str, List[WebSocket]] = {}

# Верификация JWT токена
def check_token(token: str):
    try:
        payload = jwt.decode(token, APP_CONFIG.SECRET_KEY, algorithms=[APP_CONFIG.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            logger.error("Токен не содержит username.")
            raise JWTError()
        return username
    except JWTError as e:
        logger.error(f"Ошибка верификации токена: {e}")
        return None

@app.websocket("/ws/{chat_name}")
async def websocket_endpoint(websocket: WebSocket, chat_name: str, token: str = Query(...)):
    user = check_token(token)
    if user is None:
        logger.error(f"Неверный токен: {token}")
        await websocket.close(code=1008)
        return

    await websocket.accept()
    logger.info(f"Пользователь {user} подключился к беседе {chat_name}.")

    if chat_name not in connected_clients:
        connected_clients[chat_name] = []

    connected_clients[chat_name].append(websocket)

    try:
        for client in connected_clients[chat_name]:
            if client != websocket:
                await client.send_text(f"{user} присоединился.")

        while True:
            data = await websocket.receive_text()
            logger.info(f"Получено сообщение от {user}: {data}")
            for client in connected_clients[chat_name]:
                await client.send_text(f"{user}: {data}")

    except WebSocketDisconnect:
        logger.info(f"Пользователь {user} отключился от беседы {chat_name}.")
        connected_clients[chat_name].remove(websocket)
        for client in connected_clients[chat_name]:
            await client.send_text(f"{user} покинул беседу.")
        if not connected_clients[chat_name]:
            del connected_clients[chat_name]
