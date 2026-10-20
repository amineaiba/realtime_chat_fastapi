import socketio

from core.config import get_settings

settings = get_settings()

# Use Redis URL from environment for production (Upstash)
mgr = socketio.AsyncRedisManager(settings.REDIS_URL)

# create the async socketio server
# cors_allowed_origins=[] disables Engine.IO's own CORS header injection —
# FastAPI's CORSMiddleware (main.py) already wraps this mounted sub-app, and
# having both add Access-Control-Allow-Origin produces duplicate header
# values, which browsers (unlike curl/non-browser socket.io clients) reject
# outright, breaking every real-browser socket connection.
sio = socketio.AsyncServer(
    async_mode="asgi",
    client_manager=mgr,
    cors_allowed_origins=[],
    # Socket.IO / Engine.IO traffic logs are very noisy; only show them in DEBUG.
    logger=settings.DEBUG,
    engineio_logger=settings.DEBUG,
)


sio_app = socketio.ASGIApp(sio, socketio_path="")
