# Realtime Chat App

A real-time chat application with JWT auth and refresh token rotation, room-based persistent messaging, user profiles with Cloudinary avatars, Redis-backed presence, and Socket.IO for real-time events.

**Stack:** Python · FastAPI · PostgreSQL · SQLAlchemy · Socket.IO · Redis · Cloudinary · slowapi

---

## Live Demo

- **App (Vercel):** TODO — add Vercel URL after deploy
- **Backend API (Render):** https://realtime-chat-fastapi.onrender.com/docs
- **Database:** Neon (PostgreSQL)
- **Cache / Presence:** Upstash (Redis)

> Note: Render free tier spins down after inactivity — first request may take ~30s to cold-start.

Want to run it yourself instead? See [Run locally with Docker](#run-locally-with-docker) below — one command, no manual setup.

---

## Architecture

Two parallel transport layers share a single ASGI process and the same JWT auth scheme:

```
┌──────────────────────────────────────────────┐
│                 FastAPI App                  │
│                                              │
│   REST Routers          Socket.IO (ASGI)     │
│   /auth                 /socket.io           │
│   /profile                                   │
│   /users                                     │
│   /chat                                      │
│        │                      │              │
│   Service Layer         Socket Handlers      │
│   AuthService           connect/disconnect   │
│   ProfileService        join/leave room      │
│   ChatService           send_message         │
│        │                typing indicators    │
│        │                      │              │
│   SQLAlchemy · Redis · core/security (JWT)   │
└──────────────────────────────────────────────┘
```

| Layer | Purpose |
|---|---|
| `routers/` | HTTP routing — thin, delegates all logic to services |
| `services/` | Business logic — stateless classes with static methods |
| `core/` | Shared infrastructure: DB, JWT, Redis, config, Socket.IO server |
| `sockets/` | Real-time event handlers |
| `db_models/` | SQLAlchemy ORM models |
| `schemas/` | Pydantic request/response schemas with input validation |

---

## Data Model

```
User ──────┬── Profile        (1:1, cascade delete)
           ├── RefreshToken[] (1:N, cascade delete)
           ├── RoomMember[]   (N:N bridge to Room)
           └── Message[]      (1:N as sender)

Room ──────┬── RoomMember[]   (tracks joined_at, last_read_at per member)
           └── Message[]      (cascade delete)
```

- `Room` supports two types: **DM** and **GROUP**
- `Message` supports TEXT, IMAGE, and FILE types; has soft delete and edit tracking
- All primary keys are UUIDs

---

## Auth

Tokens carry `sub` (user id) and `rt_id` (bound refresh token DB id), linking each access token to one session — logout deletes that row, no blocklist needed. Refresh tokens are single-use: rotation deletes the old row and inserts a new pair atomically. `change_password` wipes all refresh tokens at once (logs out every device). The `token_type` claim is checked on every protected route so refresh tokens can't be used as access tokens. Username format and password strength (uppercase + number required) are enforced at the Pydantic schema level. Auth endpoints are rate-limited per IP via slowapi.

---

## Real-time Messaging

Socket.IO is mounted as an ASGI sub-app sharing the same process and JWT auth. The token is accepted via the `auth` payload (`{ token: "..." }`) or `?token=` query param. Online presence is stored in Redis, making it accurate across multiple workers. Users must explicitly join a Socket.IO room with `join_room` — membership is validated against the DB on every join, and `last_read_at` is updated. Messages are persisted to the database and broadcast to everyone in the room. Typing indicators are emitted to the room excluding the sender.

| Event (client → server) | Payload |
|---|---|
| `join_room` | `{ room_id }` |
| `leave_room` | `{ room_id }` |
| `send_message` | `{ room_id, content }` |
| `get_online_users` | `{ room_id }` |
| `typing_start` | `{ room_id }` |
| `typing_stop` | `{ room_id }` |

| Event (server → client) | Payload |
|---|---|
| `new_message` | `{ id, room_id, user_id, content, created_at }` |
| `user_typing` | `{ room_id, user_id, username, is_typing }` |
| `user_online` | `{ user_id }` |
| `user_offline` | `{ user_id }` |
| `online_users` | `{ room_id, users: [...] }` |
| `room_joined` | `{ room_id, online_users }` |
| `room_left` | `{ room_id }` |

---

## API

Auth: `Authorization: Bearer <access_token>`

**Authentication**

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/auth/register` | Create account |
| `POST` | `/auth/login` | Login, returns token pair |
| `POST` | `/auth/refresh` | Rotate token pair |
| `POST` | `/auth/logout` | Revoke current session |
| `POST` | `/auth/change-password` | Change password + revoke all sessions |

**Profile**

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/profile/me` | Get own profile |
| `PATCH` | `/profile/me/` | Update profile (bio, phone, location, date of birth) |
| `POST` | `/profile/me/avatar` | Upload avatar to Cloudinary |
| `DELETE` | `/profile/me/avatar` | Remove avatar |

**Users**

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/users?q=` | Search users by username/email (min 2 chars), excludes self |

**Chat — Rooms**

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/chat/rooms/create` | Create a DM or group room |
| `GET` | `/chat/rooms` | List rooms you belong to |
| `GET` | `/chat/rooms/{room_id}` | Room detail |
| `PATCH` | `/chat/rooms/{room_id}` | Update room info |
| `DELETE` | `/chat/rooms/{room_id}` | Delete room |
| `POST` | `/chat/rooms/{room_id}/members/add` | Add member |
| `DELETE` | `/chat/rooms/{room_id}/members/{user_id}/delete` | Remove member |
| `PUT` | `/chat/rooms/{room_id}/mark-as-read` | Mark room as read |
| `GET` | `/chat/unread-count` | Global unread count across all rooms |

**Chat — Messages**

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/chat/rooms/{room_id}/messages` | Paginated message history (cursor-based) |
| `PATCH` | `/chat/messages/{message_id}` | Edit a message |
| `DELETE` | `/chat/messages/{message_id}/delete` | Soft-delete a message |

Interactive docs: `http://localhost:8000/docs`

---

## Run locally with Docker

Spins up backend + frontend + Postgres + Redis together, no manual service setup.

```bash
cp .env.docker.example .env.docker
# fill in SECRET_KEY (any random string) — Cloudinary vars are optional,
# avatar upload just won't work locally without real credentials

docker compose up --build
```

- Frontend: `http://localhost:5173`
- Backend: `http://localhost:8000/docs`

`.env.docker` is gitignored — never commit real credentials there.

---

## Manual setup (without Docker)

**Backend:**

```bash
pip install -r requirements.txt

# .env required vars
DATABASE_URL=postgresql://user:password@localhost/dbname
SECRET_KEY=your-secret-key
CLOUDINARY_CLOUD_NAME=...
CLOUDINARY_API_KEY=...
CLOUDINARY_API_SECRET=...
REDIS_URL=redis://localhost:6379

alembic upgrade head
uvicorn main:app --reload
```

Schema is managed by Alembic — no more manual DB resets. New model changes: `alembic revision --autogenerate -m "..."` then `alembic upgrade head`.

**Frontend:**

React + Vite chat UI in `frontend/` — login/register, main chat (rooms, messages, typing, presence), group create/manage, profile page.

```bash
cd frontend
npm install

# .env
VITE_API_URL=http://localhost:8000

npm run dev
```

Runs on `http://localhost:5173`.

---

## Planned

- Email verification on registration
- OAuth2 social login (Google)
- Password reset via email
- File/image message attachments
