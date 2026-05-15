import * as React from "react";
import { Check } from "lucide-react";
import { cn } from "@/lib/utils";

interface CheckboxProps
  extends Omit<React.InputHTMLAttributes<HTMLInputElement>, "type"> {
  label?: React.ReactNode;
}

/**
 * Lightweight checkbox without Radix dependency — the visual checkbox
 * is rendered next to a wrapped native ``<input>`` for accessibility.
 */
export const Checkbox = React.forwardRef<HTMLInputElement, CheckboxProps>(
  ({ className, label, id, checked, ...props }, ref) => {
    const generatedId = React.useId();
    const inputId = id ?? generatedId;
    return (
      <label
        htmlFor={inputId}
        className={cn(
          "group flex cursor-pointer select-none items-center gap-2 text-sm",
          className,
        )}
      >
        <span className="relative inline-flex size-4 shrink-0 items-center justify-center rounded border border-border bg-background transition-colors group-has-[:checked]:border-primary group-has-[:checked]:bg-primary group-has-[:focus-visible]:ring-2 group-has-[:focus-visible]:ring-ring group-has-[:disabled]:opacity-50">
          <input
            ref={ref}
            type="checkbox"
            id={inputId}
            checked={checked}
            className="peer absolute inset-0 cursor-pointer appearance-none opacity-0"
            {...props}
          />
          <Check
            className={cn(
              "size-3 text-primary-foreground transition-opacity",
              checked ? "opacity-100" : "opacity-0",
            )}
          />
        </span>
        {label != null && <span className="leading-tight">{label}</span>}
      </label>
    );
  },
);
Checkbox.displayName = "Checkbox";
