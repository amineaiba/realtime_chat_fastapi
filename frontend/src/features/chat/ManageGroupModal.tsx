import { useEffect, useState } from "react";
import { Pencil, Plus, Search, X } from "lucide-react";
import { Modal } from "../../components/ui/Modal";
import { Button } from "../../components/ui/Button";
import { TextInput } from "../../components/ui/TextInput";
import { Avatar } from "../../components/ui/Avatar";
import { useAuth } from "../../context/AuthContext";
import { useChat } from "../../context/ChatContext";
import * as chatApi from "../../lib/chatApi";
import type { UserSearchResult } from "../../types/chat";
import { DeleteConfirmModal } from "./DeleteConfirmModal";

interface ManageGroupModalProps {
  onClose: () => void;
}

export function ManageGroupModal({ onClose }: ManageGroupModalProps) {
  const { user } = useAuth();
  const { activeRoomDetail, onlineUserIds, refreshRooms, refreshActiveRoomDetail } = useChat();
  const [isEditingName, setIsEditingName] = useState(false);
  const [nameDraft, setNameDraft] = useState(activeRoomDetail?.name ?? "");
  const [addingMember, setAddingMember] = useState(false);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<UserSearchResult[]>([]);
  const [searched, setSearched] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    setNameDraft(activeRoomDetail?.name ?? "");
  }, [activeRoomDetail?.name]);

  useEffect(() => {
    const q = query.trim();
    if (!addingMember || q.length < 2) {
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
  }, [query, addingMember]);

  if (!activeRoomDetail || !user) return null;

  const isCreator = activeRoomDetail.creator_id === user.id;
  const memberIds = new Set(activeRoomDetail.members.map((m) => m.user.id));
  const groupName = activeRoomDetail.name ?? "Group";

  async function saveName() {
    const trimmed = nameDraft.trim();
    setIsEditingName(false);
    if (!trimmed || trimmed === activeRoomDetail?.name) return;
    try {
      await chatApi.updateRoom(activeRoomDetail!.id, trimmed);
      await Promise.all([refreshActiveRoomDetail(), refreshRooms()]);
    } catch {
      setError("Only the creator can rename this group.");
      await refreshActiveRoomDetail();
    }
  }

  async function handleAddMember(person: UserSearchResult) {
    setBusy(true);
    setError(null);
    try {
      await chatApi.addRoomMember(activeRoomDetail!.id, person.id);
      await refreshActiveRoomDetail();
      setQuery("");
      setResults([]);
      setSearched(false);
    } catch {
      setError("Could not add member — you may no longer be the creator.");
      await refreshActiveRoomDetail();
    } finally {
      setBusy(false);
    }
  }

  async function handleRemoveMember(userId: string) {
    setBusy(true);
    setError(null);
    try {
      await chatApi.removeRoomMember(activeRoomDetail!.id, userId);
      await refreshActiveRoomDetail();
    } catch {
      setError("Could not remove member — you may no longer be the creator.");
      await refreshActiveRoomDetail();
    } finally {
      setBusy(false);
    }
  }

  async function handleLeave() {
    setBusy(true);
    setError(null);
    try {
      await chatApi.leaveRoom(activeRoomDetail!.id);
      await refreshRooms();
      onClose();
    } catch {
      setError("Could not leave the group. Try again.");
      setBusy(false);
    }
  }

  async function handleDelete() {
    await chatApi.deleteRoom(activeRoomDetail!.id);
    await refreshRooms();
    onClose();
  }

  return (
    <>
      <Modal
        title={groupName}
        titleContent={
          isEditingName ? (
            <input
              autoFocus
              value={nameDraft}
              onChange={(e) => setNameDraft(e.target.value)}
              onBlur={saveName}
              onKeyDown={(e) => {
                if (e.key === "Enter") e.currentTarget.blur();
              }}
              className="h-9 w-full rounded-md border-[1.5px] border-accent bg-bg-elevated px-2 text-lg font-semibold text-text-primary outline-none"
            />
          ) : (
            <div className="flex items-center gap-2">
              <span className="text-lg font-semibold text-text-primary">{groupName}</span>
              {isCreator && (
                <button
                  type="button"
                  onClick={() => setIsEditingName(true)}
                  aria-label="Rename group"
                  className="text-text-muted hover:text-text-primary"
                >
                  <Pencil size={14} />
                </button>
              )}
            </div>
          )
        }
        onClose={onClose}
        footer={
          isCreator ? (
            <>
              <Button
                type="button"
                variant="ghost-danger"
                onClick={() => setShowDeleteConfirm(true)}
                fullWidth={false} className="px-4"
              >
                Delete room
              </Button>
              <div className="flex-1" />
              <Button type="button" variant="secondary" onClick={onClose} fullWidth={false} className="px-4">
                Close
              </Button>
            </>
          ) : (
            <Button
              type="button"
              variant="secondary"
              isLoading={busy}
              onClick={handleLeave}
              fullWidth={false} className="px-4"
            >
              Leave group
            </Button>
          )
        }
      >
        <div className="-mt-2 mb-4">
          <span className="text-xs text-text-muted">
            {activeRoomDetail.members.length} members
          </span>
        </div>

        <div className="border-t border-border pt-4">
          {isCreator && (
            <button
              type="button"
              onClick={() => setAddingMember((v) => !v)}
              className="mb-2 flex w-full items-center gap-2 rounded-md px-2 py-2 text-sm text-accent hover:bg-bg-elevated"
            >
              <Plus size={16} />
              Add members
            </button>
          )}

          {isCreator && addingMember && (
            <div className="mb-3 flex flex-col gap-2">
              <TextInput
                label="Search"
                placeholder="Search people…"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                rightElement={<Search size={16} className="text-text-muted" />}
              />
              <div className="max-h-[160px] overflow-y-auto">
                {searched && results.filter((p) => !memberIds.has(p.id)).length === 0 ? (
                  <p className="px-1 py-4 text-center text-[13px] text-text-muted">No users found</p>
                ) : (
                  results
                    .filter((p) => !memberIds.has(p.id))
                    .map((person) => (
                      <div
                        key={person.id}
                        onClick={() => handleAddMember(person)}
                        className="flex cursor-pointer items-center gap-3 rounded-md px-2 py-2 hover:bg-bg-elevated"
                      >
                        <Avatar src={person.avatar_url} alt={person.username} size={32} />
                        <span className="text-sm text-text-primary">{person.username}</span>
                      </div>
                    ))
                )}
              </div>
            </div>
          )}

          <div className="flex max-h-[220px] flex-col gap-0.5 overflow-y-auto">
            {activeRoomDetail.members.map((member) => {
              const isRoomCreator = member.user.id === activeRoomDetail.creator_id;
              return (
                <div
                  key={member.user.id}
                  className="flex items-center gap-3 rounded-md px-2 py-2 hover:bg-bg-elevated"
                >
                  <Avatar
                    src={member.user.avatar_url}
                    alt={member.user.username}
                    size={32}
                    presence={onlineUserIds.has(member.user.id) ? "online" : "offline"}
                  />
                  <span className="flex-1 text-sm text-text-primary">{member.user.username}</span>
                  {isRoomCreator ? (
                    <span className="text-xs text-text-secondary">Creator</span>
                  ) : (
                    isCreator && (
                      <button
                        type="button"
                        onClick={() => handleRemoveMember(member.user.id)}
                        aria-label={`Remove ${member.user.username}`}
                        className="flex h-6 w-6 items-center justify-center rounded-md text-text-muted hover:bg-danger/10 hover:text-danger"
                      >
                        <X size={14} />
                      </button>
                    )
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {error && <p className="mt-3 text-xs text-danger">{error}</p>}
      </Modal>

      {showDeleteConfirm && (
        <DeleteConfirmModal
          groupName={groupName}
          memberCount={activeRoomDetail.members.length}
          onCancel={() => setShowDeleteConfirm(false)}
          onConfirm={handleDelete}
        />
      )}
    </>
  );
}
