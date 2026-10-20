# WebSocket API Documentation

## Connection

**Endpoint:** `/socket.io`  
**Protocol:** Socket.IO over WebSocket  
**Auth:** a valid **access** token in the `auth` payload. The connection is refused if the token is missing, expired, a refresh token, or was revoked by logout. Tokens in the query string are not accepted (they leak into logs).

```js
// socket.io-client
const socket = io(API_URL, { auth: { token: accessToken } });
```

---

## Events: Client → Server

### `join_room`

Join a chat room to receive messages.

```json
{
  "room_id": "uuid"
}
```

**Response:** `room_joined` event with online users list. Joining also marks the room as read.

---

### `leave_room`

Stop receiving events for a room (you stay a member).

```json
{
  "room_id": "uuid"
}
```

**Response:** `room_left` event.

---

### `send_message`

Send a message to a room.

```json
{
  "room_id": "uuid",
  "content": "message text"
}
```

**Saved to database.** Broadcasts `new_message` to all room members.

---

### `typing_start`

Notify room members you're typing.

```json
{
  "room_id": "uuid"
}
```

**Broadcasts:** `user_typing` with `is_typing: true`

---

### `typing_stop`

Notify room members you stopped typing.

```json
{
  "room_id": "uuid"
}
```

**Broadcasts:** `user_typing` with `is_typing: false`

---

### `get_online_users`

Request list of online users in a room.

```json
{
  "room_id": "uuid"
}
```

**Response:** `online_users` event.

---

## Events: Server → Client

### `new_message`

Received when someone sends a message in your room.

```json
{
  "id": "message-uuid",
  "room_id": "room-uuid",
  "user_id": "sender-uuid",
  "content": "message text",
  "created_at": "2026-02-13T10:30:00+00:00"
}
```

---

### `user_typing`

Received when someone starts/stops typing.

```json
{
  "room_id": "room-uuid",
  "user_id": "typing-user-uuid",
  "username": "john_doe",
  "is_typing": true
}
```

---

### `user_online`

Sent to every room the user belongs to when they connect.

```json
{
  "user_id": "uuid",
  "message": "User came online"
}
```

---

### `user_offline`

Sent to every room the user belongs to when they disconnect.

```json
{
  "user_id": "uuid",
  "message": "User went offline"
}
```

---

### `room_joined`

Confirmation after joining a room.

```json
{
  "room_id": "room-uuid",
  "message": "Successfully joined room",
  "online_users": ["user1-uuid", "user2-uuid"]
}
```

---

### `room_left`

Confirmation after leaving a room.

```json
{
  "room_id": "room-uuid",
  "message": "Successfully left room"
}
```

---

### `online_users`

Response to `get_online_users` request.

```json
{
  "room_id": "room-uuid",
  "users": ["user1-uuid", "user2-uuid"]
}
```

---

### `error`

Error notifications.

```json
{
  "message": "error description"
}
```

---

## Notes

- All `room_id` and `user_id` values are UUIDs
- Must join room before sending messages
- Online status persists across all user's rooms
- Typing events don't persist (broadcast only)
- Messages are stored in database with edit/delete support via REST API
