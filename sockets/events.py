from core.socket_manager import sio
from sockets.handlers import (
    handle_connect,
    handle_disconnect,
    handle_get_online_users,
    handle_join_room,
    handle_leave_room,
    handle_send_message,
    handle_typing_start,
    handle_typing_stop,
)


# Map the event to the handler function
@sio.on("connect")
async def on_connect(sid, environ, auth=None):
    return await handle_connect(sid, environ, auth)


@sio.on("disconnect")
async def on_disconnect(sid):
    await handle_disconnect(sid)


@sio.on("join_room")
async def join_room(sid, data):
    await handle_join_room(sid, data)


@sio.on("leave_room")
async def on_leave_room(sid, data):
    await handle_leave_room(sid, data)


@sio.on("send_message")
async def on_send_message(sid, data):
    await handle_send_message(sid, data)


@sio.on("get_online_users")
async def on_get_online_users(sid, data):
    await handle_get_online_users(sid, data)


@sio.on("typing_start")
async def on_typing_start(sid, data):
    await handle_typing_start(sid, data)


@sio.on("typing_stop")
async def on_typing_stop(sid, data):
    await handle_typing_stop(sid, data)
