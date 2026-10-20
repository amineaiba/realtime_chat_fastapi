// Mirrors schemas/user.py::UserOut
export interface UserSummary {
  id: string;
  username: string;
  email: string;
  avatar_url: string | null;
  created_at: string;
  is_active: boolean;
}

export type RoomType = "dm" | "group";

// Mirrors schemas/user.py::UserSearchOut (GET /users?q=)
export interface UserSearchResult {
  id: string;
  username: string;
  avatar_url: string | null;
}
export type MessageType = "text" | "image" | "file";

// Mirrors schemas/chat.py::MessageOut (REST shape)
export interface Message {
  id: string;
  content: string | null;
  type: MessageType;
  attachment_url: string | null;
  sender: UserSummary;
  room_id: string;
  is_edited: boolean;
  is_deleted: boolean;
  created_at: string;
}

// Mirrors schemas/chat.py::RoomMemberOut
export interface RoomMember {
  user: UserSummary;
  joined_at: string;
  last_read_at: string;
}

// Mirrors schemas/chat.py::RoomBase + RoomListOut
export interface RoomSummary {
  id: string;
  type: RoomType;
  name: string | null;
  is_active: boolean;
  creator_id: string | null;
  created_at: string;
  updated_at: string | null;
  unread_count: number;
  last_message: Message | null;
  members: RoomMember[];
}

// Mirrors schemas/chat.py::RoomDetailOut
export interface RoomDetail
  extends Omit<RoomSummary, "unread_count" | "last_message"> {
  members: RoomMember[];
}

// ---- Socket.IO payloads (raw, as emitted by sockets/handlers.py) ----

export interface RoomJoinedPayload {
  room_id: string;
  message: string;
  online_users: string[];
}

export interface RoomLeftPayload {
  room_id: string;
  message: string;
}

// NOTE: shape intentionally differs from MessageOut — flat user_id, no
// type/attachment_url/is_edited/is_deleted. Must be normalized client-side
// using the room member list to resolve sender username/avatar.
export interface NewMessagePayload {
  id: string;
  room_id: string;
  user_id: string;
  content: string;
  created_at: string;
}

export interface OnlineUsersPayload {
  room_id: string;
  users: string[];
}

export interface UserTypingPayload {
  room_id: string;
  user_id: string;
  username: string;
  is_typing: boolean;
}

// user_online / user_offline
export interface PresenceEventPayload {
  user_id: string;
  message: string;
}

export interface SocketErrorPayload {
  message: string;
}

// Client-side normalized message — what components actually render, whether
// it came from REST history, a reconciled socket new_message event, or an
// optimistic local send.
export interface ChatMessage extends Message {
  status: "sent" | "pending" | "failed";
  clientId?: string;
}
