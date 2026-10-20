# Realtime Chat: frontend

A small React app to use and demo the backend API and Socket.IO events. The backend is the focus of this project, so the UI is kept simple.

**Stack:** React 19 · TypeScript · Vite · Tailwind CSS v4 · React Router · axios · socket.io-client · lucide-react · oxlint

## Run

```bash
cp .env.example .env    # VITE_API_URL=http://localhost:8000
npm install
npm run dev             # http://localhost:5173
```

Other scripts: `npm run build`, `npm run lint`.

To run everything with Docker instead, see the main [README](../README.md).

## Structure

| Folder | Purpose |
|---|---|
| `src/pages/` | Login, Register, Main chat, Profile |
| `src/features/chat/` | Room list, messages, composer, group modals |
| `src/features/profile/` | Profile form, avatar upload, change password |
| `src/context/` | `AuthContext`, `SocketContext`, `ChatContext` (app state, no Redux) |
| `src/components/ui/` | Shared UI: Button, TextInput, Avatar, Badge, Modal, Skeleton |
| `src/lib/` | API clients (axios), time formatting, helpers |
| `scripts/screenshots.mjs` | Playwright script that takes the README screenshots |

## How auth works here

- The access token lives **in memory only**, never in `localStorage`.
- The refresh token is an `httpOnly` cookie set by the backend. On page load, the app calls `POST /auth/refresh` to restore the session.
- If a request gets a `401`, the axios interceptor refreshes once and retries the request.
- The Socket.IO client sends the access token in its `auth` payload, and reconnects with a fresh token.

## Screenshots

```bash
# with the app running and the demo data seeded (see main README)
npx playwright install chromium
node scripts/screenshots.mjs    # writes to ../docs/screenshots/
```
