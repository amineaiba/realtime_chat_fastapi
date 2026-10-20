import { isAxiosError } from "axios";
import { CircleCheck, CircleX, ChevronRight, LogOut } from "lucide-react";
import { useEffect, useState } from "react";
import { Button } from "../../components/ui/Button";
import { useAuth } from "../../context/AuthContext";
import * as profileApi from "../../lib/profileApi";
import type { ProfileResponse } from "../../types/profile";
import { AvatarUploader } from "./AvatarUploader";
import { ChangePasswordModal } from "./ChangePasswordModal";

type Toast = { tone: "success" | "danger"; message: string };

function FieldRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex gap-4">
      <div className="w-[90px] shrink-0 pt-0.5 text-xs font-medium text-text-secondary">
        {label}
      </div>
      <div className="text-sm text-text-primary">{value || "—"}</div>
    </div>
  );
}

export function ProfileForm() {
  const { user, logout, refreshUser } = useAuth();

  const [profile, setProfile] = useState<ProfileResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(false);
  const [statusDraft, setStatusDraft] = useState("");
  const [bioDraft, setBioDraft] = useState("");
  const [saving, setSaving] = useState(false);
  const [toast, setToast] = useState<Toast | null>(null);
  const [showPasswordModal, setShowPasswordModal] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const data = await profileApi.getMyProfile();
        if (cancelled) return;
        setProfile(data);
        setStatusDraft(data.status ?? "");
        setBioDraft(data.bio ?? "");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!toast) return;
    const timer = setTimeout(() => setToast(null), 3000);
    return () => clearTimeout(timer);
  }, [toast]);

  if (loading || !profile || !user) {
    return (
      <div className="rounded-xl border border-border bg-bg-raised p-8 text-center text-sm text-text-secondary">
        Loading…
      </div>
    );
  }

  function startEditing() {
    setStatusDraft(profile?.status ?? "");
    setBioDraft(profile?.bio ?? "");
    setEditing(true);
  }

  function cancelEditing() {
    setStatusDraft(profile?.status ?? "");
    setBioDraft(profile?.bio ?? "");
    setEditing(false);
  }

  async function saveChanges() {
    setSaving(true);
    try {
      const updated = await profileApi.updateMyProfile({
        status: statusDraft || null,
        bio: bioDraft || null,
      });
      setProfile(updated);
      setEditing(false);
      setToast({ tone: "success", message: "Profile updated" });
    } catch (err) {
      const detail =
        isAxiosError(err) && err.response?.status === 422
          ? "Couldn't save changes. Check your input."
          : "Couldn't save changes. Try again.";
      setToast({ tone: "danger", message: detail });
    } finally {
      setSaving(false);
    }
  }

  function handleAvatarUploaded(url: string) {
    setProfile((p) => (p ? { ...p, avatar_url: url } : p));
    void refreshUser();
  }

  return (
    <div className="rounded-xl border border-border bg-bg-raised p-8 shadow-[0_8px_24px_rgba(0,0,0,0.35)]">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-text-primary">Your profile</h1>
        {editing ? (
          <div className="flex gap-2">
            <Button
              type="button"
              variant="secondary"
              disabled={saving}
              onClick={cancelEditing}
              fullWidth={false} className="px-4"
            >
              Cancel
            </Button>
            <Button
              type="button"
              isLoading={saving}
              onClick={saveChanges}
              fullWidth={false} className="px-4"
            >
              Save changes
            </Button>
          </div>
        ) : (
          <Button
            type="button"
            variant="secondary"
            onClick={startEditing}
            fullWidth={false} className="px-4"
          >
            Edit profile
          </Button>
        )}
      </div>

      <div className="mb-6 flex flex-col items-center">
        <AvatarUploader
          avatarUrl={profile.avatar_url}
          username={user.username}
          onUploaded={handleAvatarUploaded}
        />
        <div className="mt-3 text-base font-semibold text-text-primary">{user.username}</div>
      </div>

      {editing ? (
        <div className="mb-6 flex flex-col gap-4">
          <FieldRow label="Username" value={user.username} />
          <FieldRow label="Email" value={user.email} />
          <div>
            <label className="mb-2 block text-xs font-medium text-text-secondary">Status</label>
            <input
              type="text"
              value={statusDraft}
              maxLength={40}
              disabled={saving}
              placeholder="What's your status?"
              onChange={(e) => setStatusDraft(e.target.value)}
              className="h-10 w-full rounded-md border border-border bg-bg-elevated px-3 text-sm text-text-primary outline-none transition-colors placeholder:text-text-muted hover:border-text-muted focus:border-[1.5px] focus:border-accent focus:ring-2 focus:ring-accent/20 disabled:border-border/40 disabled:bg-bg-app disabled:text-text-muted"
            />
          </div>
          <div>
            <div className="mb-2 flex items-baseline justify-between">
              <label className="text-xs font-medium text-text-secondary">Bio</label>
              <span className="text-[11px] text-text-muted">{bioDraft.length}/160</span>
            </div>
            <textarea
              value={bioDraft}
              maxLength={160}
              disabled={saving}
              rows={3}
              placeholder="Tell people about yourself"
              onChange={(e) => setBioDraft(e.target.value)}
              className="max-h-32 w-full resize-none overflow-y-auto rounded-md border border-border bg-bg-elevated px-3 py-2 text-sm leading-relaxed text-text-primary outline-none transition-colors placeholder:text-text-muted hover:border-text-muted focus:border-[1.5px] focus:border-accent focus:ring-2 focus:ring-accent/20 disabled:border-border/40 disabled:bg-bg-app disabled:text-text-muted"
            />
          </div>
        </div>
      ) : (
        <div className="mb-6 flex flex-col gap-4">
          <FieldRow label="Username" value={user.username} />
          <FieldRow label="Email" value={user.email} />
          <FieldRow label="Status" value={profile.status ?? ""} />
          <FieldRow label="Bio" value={profile.bio ?? ""} />
        </div>
      )}

      <div className="mb-6 h-px bg-border" />

      <div className="mb-4 text-base font-semibold text-text-primary">Account</div>

      <button
        type="button"
        onClick={() => setShowPasswordModal(true)}
        className="mb-4 flex w-full items-center justify-between border-b border-border py-3 text-left hover:bg-bg-elevated"
      >
        <span className="text-sm text-text-primary">Change password</span>
        <ChevronRight size={16} className="text-text-muted" />
      </button>

      <Button
        type="button"
        variant="secondary"
        onClick={() => void logout()}
        fullWidth={false} className="gap-2 px-4"
      >
        <LogOut size={16} />
        Log out
      </Button>

      {showPasswordModal && (
        <ChangePasswordModal onClose={() => setShowPasswordModal(false)} />
      )}

      {toast && (
        <div className="fixed bottom-6 right-6 z-50 flex max-w-[360px] items-start gap-2 rounded-xl border border-border bg-bg-raised px-4 py-3 shadow-[0_8px_24px_rgba(0,0,0,0.4)]">
          {toast.tone === "success" ? (
            <CircleCheck size={18} className="mt-0.5 shrink-0 text-success" />
          ) : (
            <CircleX size={18} className="mt-0.5 shrink-0 text-danger" />
          )}
          <span className="text-sm font-semibold text-text-primary">{toast.message}</span>
        </div>
      )}
    </div>
  );
}
