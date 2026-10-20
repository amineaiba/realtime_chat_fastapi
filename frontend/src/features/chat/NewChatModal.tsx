import { useEffect, useMemo, useState } from "react";
import { Search } from "lucide-react";
import { Modal } from "../../components/ui/Modal";
import { TextInput } from "../../components/ui/TextInput";
import { Button } from "../../components/ui/Button";
import { Checkbox } from "../../components/ui/Checkbox";
import { Chip } from "../../components/ui/Chip";
import { Avatar } from "../../components/ui/Avatar";
import { useChat } from "../../context/ChatContext";
import * as chatApi from "../../lib/chatApi";
import type { UserSearchResult } from "../../types/chat";

type Mode = "dm" | "group";

interface NewChatModalProps {
  onClose: () => void;
}

export function NewChatModal({ onClose }: NewChatModalProps) {
  const { selectRoom, refreshRooms } = useChat();
  const [mode, setMode] = useState<Mode>("dm");
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<UserSearchResult[]>([]);
  const [searched, setSearched] = useState(false);
  const [groupName, setGroupName] = useState("");
  const [selected, setSelected] = useState<Map<string, UserSearchResult>>(new Map());
  const [creating, setCreating] = useState(false);
  const [attempted, setAttempted] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const q = query.trim();
    if (q.length < 2) {
      setResults([]);
      setSearched(false);
      return;
    }
    let cancelled = false;
    const timer = setTimeout(async () => {
      try {
        const data = await chatApi.searchUsers(q);
        if (!cancelled) {
          setResults(data);
          setSearched(true);
        }
      } catch {
        if (!cancelled) {
          setResults([]);
          setSearched(true);
        }
      }
    }, 300);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [query]);

  const selectedList = useMemo(() => Array.from(selected.values()), [selected]);

  function toggleSelect(person: UserSearchResult) {
    setSelected((prev) => {
      const next = new Map(prev);
      if (next.has(person.id)) next.delete(person.id);
      else next.set(person.id, person);
      return next;
    });
  }

  async function handleStartDm(person: UserSearchResult) {
    try {
      const room = await chatApi.createRoom({ type: "dm", member_ids: [person.id] });
      await refreshRooms();
      selectRoom(room.id);
      onClose();
    } catch {
      setError("Could not start conversation. Try again.");
    }
  }

  const createDisabled = creating || !groupName.trim() || selectedList.length === 0;

  async function handleCreateGroup() {
    setAttempted(true);
    if (createDisabled) return;
    setCreating(true);
    setError(null);
    try {
      const room = await chatApi.createRoom({
        type: "group",
        name: groupName.trim(),
        member_ids: selectedList.map((p) => p.id),
      });
      await refreshRooms();
      selectRoom(room.id);
      onClose();
    } catch {
      setError("Could not create group. Try again.");
      setCreating(false);
    }
  }

  const isGroupMode = mode === "group";

  return (
    <Modal title="New chat" onClose={onClose}>
      <div className="flex flex-col gap-4">
        <div className="flex overflow-hidden rounded-md border border-border">
          <button
            type="button"
            onClick={() => setMode("dm")}
            className={`h-9 flex-1 text-sm ${
              mode === "dm" ? "bg-bg-elevated text-text-primary" : "bg-transparent text-text-secondary"
            }`}
          >
            Direct Message
          </button>
          <button
            type="button"
            onClick={() => setMode("group")}
            className={`h-9 flex-1 text-sm ${
              mode === "group" ? "bg-bg-elevated text-text-primary" : "bg-transparent text-text-secondary"
            }`}
          >
            New Group
          </button>
        </div>

        {isGroupMode && (
          <>
            <TextInput
              label="Group name"
              placeholder="e.g. design-team"
              value={groupName}
              onChange={(e) => setGroupName(e.target.value)}
            />
            <div className="flex flex-col gap-2">
              <span className="text-xs font-medium text-text-secondary">
                Members ({selectedList.length} selected)
              </span>
              {selectedList.length > 0 && (
                <div className="flex flex-wrap gap-2">
                  {selectedList.map((p) => (
                    <Chip key={p.id} label={p.username} onRemove={() => toggleSelect(p)} />
                  ))}
                </div>
              )}
            </div>
          </>
        )}

        <TextInput
          label="Search"
          placeholder="Search people…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          rightElement={<Search size={16} className="text-text-muted" />}
        />

        <div className="max-h-[220px] overflow-y-auto">
          {searched && results.length === 0 ? (
            <p className="px-1 py-6 text-center text-[13px] text-text-muted">No users found</p>
          ) : (
            results.map((person) => (
              <div
                key={person.id}
                onClick={() => (isGroupMode ? toggleSelect(person) : handleStartDm(person))}
                className="flex cursor-pointer items-center gap-3 rounded-md px-2 py-2 hover:bg-bg-elevated"
              >
                {isGroupMode && (
                  <Checkbox checked={selected.has(person.id)} onChange={() => toggleSelect(person)} />
                )}
                <Avatar src={person.avatar_url} alt={person.username} size={32} />
                <span className="text-sm text-text-primary">{person.username}</span>
              </div>
            ))
          )}
        </div>

        {isGroupMode && (
          <div className="flex flex-col items-end gap-2">
            {attempted && createDisabled && !creating && (
              <span className="text-xs text-danger">Add a name and at least one member</span>
            )}
            {error && <span className="text-xs text-danger">{error}</span>}
            <Button
              type="button"
              isLoading={creating}
              disabled={creating || (attempted && createDisabled)}
              onClick={handleCreateGroup}
              fullWidth={false} className="px-6"
            >
              Create group
            </Button>
          </div>
        )}
      </div>
    </Modal>
  );
}
