import { isAxiosError } from "axios";
import { Eye, EyeOff, Shield } from "lucide-react";
import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "../../components/ui/Button";
import { Modal } from "../../components/ui/Modal";
import { TextInput } from "../../components/ui/TextInput";
import { setAccessToken } from "../../lib/api";
import * as profileApi from "../../lib/profileApi";

interface ChangePasswordModalProps {
  onClose: () => void;
}

export function ChangePasswordModal({ onClose }: ChangePasswordModalProps) {
  const navigate = useNavigate();

  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [currentPasswordError, setCurrentPasswordError] = useState<string | null>(null);
  const [confirmError, setConfirmError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (submitting) return;

    setCurrentPasswordError(null);
    setConfirmError(null);

    if (!currentPassword) return;
    if (newPassword.length < 8 || !/[A-Z]/.test(newPassword) || !/[0-9]/.test(newPassword)) {
      setConfirmError("New password needs 8+ characters, an uppercase letter, and a number.");
      return;
    }
    if (newPassword !== confirmPassword) {
      setConfirmError("Passwords don't match.");
      return;
    }

    setSubmitting(true);
    try {
      await profileApi.changePassword(currentPassword, newPassword);
      setAccessToken(null);
      navigate("/login", { state: { flash: "Password changed. Please log in again." } });
    } catch (err) {
      if (isAxiosError(err) && err.response?.status === 400) {
        setCurrentPasswordError("Current password is incorrect");
      } else {
        setCurrentPasswordError("Something went wrong. Please try again.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Modal title="Change password" onClose={onClose} size="md">
      <div className="mb-5 flex items-start gap-2 rounded-md border border-warning/30 bg-warning/10 px-3 py-3">
        <Shield size={16} className="mt-0.5 shrink-0 text-warning" />
        <span className="text-[13px] leading-relaxed text-text-primary">
          This will sign you out of all devices, including this one.
        </span>
      </div>

      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <div>
          <TextInput
            id="current-password"
            label="Current password"
            type="password"
            autoComplete="current-password"
            value={currentPassword}
            disabled={submitting}
            error={!!currentPasswordError}
            onChange={(e) => setCurrentPassword(e.target.value)}
          />
          {currentPasswordError && (
            <p className="mt-1 text-xs text-danger">{currentPasswordError}</p>
          )}
        </div>

        <TextInput
          id="new-password"
          label="New password"
          type={showNewPassword ? "text" : "password"}
          autoComplete="new-password"
          value={newPassword}
          disabled={submitting}
          onChange={(e) => setNewPassword(e.target.value)}
          rightElement={
            <button
              type="button"
              tabIndex={-1}
              onClick={() => setShowNewPassword((v) => !v)}
              className="text-text-muted transition-colors hover:text-text-primary"
              aria-label={showNewPassword ? "Hide password" : "Show password"}
            >
              {showNewPassword ? <EyeOff size={18} /> : <Eye size={18} />}
            </button>
          }
        />

        <div>
          <TextInput
            id="confirm-password"
            label="Confirm new password"
            type="password"
            autoComplete="new-password"
            value={confirmPassword}
            disabled={submitting}
            onChange={(e) => setConfirmPassword(e.target.value)}
          />
          {confirmError && <p className="mt-1 text-xs text-danger">{confirmError}</p>}
        </div>

        <div className="mt-1 flex justify-end gap-3">
          <Button
            type="button"
            variant="secondary"
            disabled={submitting}
            onClick={onClose}
            fullWidth={false} className="px-4"
          >
            Cancel
          </Button>
          <Button type="submit" isLoading={submitting} fullWidth={false} className="px-4">
            Change password
          </Button>
        </div>
      </form>
    </Modal>
  );
}
