import { useState } from "react";
import { Modal } from "../../components/ui/Modal";
import { Button } from "../../components/ui/Button";

interface DeleteConfirmModalProps {
  groupName: string;
  memberCount: number;
  onCancel: () => void;
  onConfirm: () => Promise<void>;
}

export function DeleteConfirmModal({
  groupName,
  memberCount,
  onCancel,
  onConfirm,
}: DeleteConfirmModalProps) {
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleDelete() {
    setDeleting(true);
    setError(null);
    try {
      await onConfirm();
    } catch {
      setError("Could not delete room. Try again.");
      setDeleting(false);
    }
  }

  return (
    <Modal
      title={`Delete ${groupName}?`}
      onClose={onCancel}
      size="sm"
      footer={
        <>
          <Button type="button" variant="secondary" onClick={onCancel} fullWidth={false} className="px-4">
            Cancel
          </Button>
          <Button
            type="button"
            variant="danger"
            isLoading={deleting}
            onClick={handleDelete}
            fullWidth={false} className="px-4"
          >
            Delete
          </Button>
        </>
      }
    >
      <p className="text-sm leading-relaxed text-text-secondary">
        This permanently deletes the room and its message history for all {memberCount} members.
        This can&apos;t be undone.
      </p>
      {error && <p className="mt-2 text-xs text-danger">{error}</p>}
    </Modal>
  );
}
