import type { ButtonHTMLAttributes } from "react";

type ButtonVariant = "primary" | "secondary" | "danger" | "ghost-danger";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  isLoading?: boolean;
  variant?: ButtonVariant;
  // Full width by default (form submit buttons). Pass false for buttons that
  // sit in a row, e.g. modal footers.
  fullWidth?: boolean;
}

const variantClasses: Record<ButtonVariant, string> = {
  primary:
    "bg-accent text-white hover:bg-accent-hover active:bg-accent-active disabled:bg-bg-raised disabled:text-text-muted",
  secondary:
    "border border-border bg-transparent text-text-primary hover:bg-bg-elevated disabled:text-text-muted",
  danger:
    "bg-danger text-white hover:bg-danger-hover disabled:bg-bg-raised disabled:text-text-muted",
  "ghost-danger":
    "bg-transparent text-danger hover:bg-danger/10 disabled:text-text-muted",
};

export function Button({
  isLoading,
  disabled,
  children,
  className,
  variant = "primary",
  fullWidth = true,
  ...props
}: ButtonProps) {
  return (
    <button
      disabled={disabled || isLoading}
      className={`inline-flex h-10 ${fullWidth ? "w-full" : ""} items-center justify-center rounded-md px-4 text-sm font-semibold transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-bg-raised disabled:cursor-not-allowed ${variantClasses[variant]} ${className ?? ""}`}
      {...props}
    >
      {isLoading ? (
        <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
      ) : (
        children
      )}
    </button>
  );
}
