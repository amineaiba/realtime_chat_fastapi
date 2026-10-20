from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import core.cloudinary_config  # noqa: F401 — configures the cloudinary SDK on import
from core.config import get_settings
from core.logging_config import setup_logging
from core.socket_manager import sio_app
from routers import auth, chat, profile, users
from sockets import events  # noqa: F401 — registers the Socket.IO handlers

settings = get_settings()
setup_logging()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="""
## Realtime Chat API

REST API endpoints documented below.

**WebSocket API:** [View WebSocket Documentation](https://github.com/amineaiba/realtime_chat_fastapi/blob/main/WEBSOCKET_API.md)

---
    """,
)

# CORS Configuration for production
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

# Mount at /socket.io
app.mount("/socket.io", sio_app)

app.include_router(auth.router)
app.include_router(profile.router)
app.include_router(chat.router)
app.include_router(users.router)


@app.get("/")
async def root():
    return {
        "message": "Realtime Chat API",
        "status": "running",
        "version": settings.APP_VERSION,
    }


@app.get("/health")
async def health_check():
    """Health check endpoint for deployment platforms"""
    return {"status": "healthy", "service": "realtime_chat_api"}
