import { useState, useRef, useEffect } from "react";
import { createPortal } from "react-dom";
import { Sun, Moon, Monitor, Check } from "@phosphor-icons/react";
import type { Icon } from "@phosphor-icons/react";
import { useTheme } from "@/components/ui/themeProvider";
import { cn } from "@/utils/cn";

type ThemeMode = "light" | "dark" | "system";

const options: { value: ThemeMode; label: string; icon: Icon }[] = [
  { value: "light", label: "Light", icon: Sun },
  { value: "dark", label: "Dark", icon: Moon },
  { value: "system", label: "System", icon: Monitor },
];

export function ThemeSwitcher() {
  const { mode, setMode } = useTheme();
  const [isOpen, setIsOpen] = useState(false);
  const buttonRef = useRef<HTMLButtonElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const [position, setPosition] = useState<{
    top: number;
    right: number;
  } | null>(null);

  const ActiveIcon =
    options.find((o) => o.value === mode)?.icon ?? Monitor;

  useEffect(() => {
    if (!isOpen || !buttonRef.current) return;

    const rect = buttonRef.current.getBoundingClientRect();
    setPosition({
      top: rect.bottom + 6,
      right: window.innerWidth - rect.right,
    });

    function handleClickOutside(event: MouseEvent) {
      if (
        buttonRef.current &&
        !buttonRef.current.contains(event.target as Node) &&
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") setIsOpen(false);
    }

    document.addEventListener("mousedown", handleClickOutside);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [isOpen]);

  const dropdown =
    isOpen && position
      ? createPortal(
          <div
            ref={dropdownRef}
            style={{
              position: "fixed",
              top: position.top,
              right: position.right,
            }}
            className={cn(
              "z-[200] w-40 overflow-hidden rounded-lg",
              "border border-border bg-surface shadow-xl"
            )}
          >
            <div className="py-1">
              {options.map((option) => {
                const OptionIcon = option.icon;
                const isSelected = option.value === mode;
                return (
                  <button
                    key={option.value}
                    type="button"
                    onClick={() => {
                      setMode(option.value);
                      setIsOpen(false);
                    }}
                    className={cn(
                      "flex w-full items-center justify-between gap-2 px-3 py-2 text-sm",
                      "transition-colors duration-100",
                      isSelected
                        ? "bg-primary/10 font-medium text-primary"
                        : "text-foreground hover:bg-accent"
                    )}
                  >
                    <span className="flex items-center gap-2">
                      <OptionIcon size={16} weight="duotone" />
                      {option.label}
                    </span>
                    {isSelected && (
                      <Check
                        size={16}
                        weight="bold"
                        className="flex-shrink-0 text-primary"
                      />
                    )}
                  </button>
                );
              })}
            </div>
          </div>,
          document.body
        )
      : null;

  return (
    <>
      <button
        ref={buttonRef}
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className={cn(
          "flex h-8 w-8 items-center justify-center rounded-lg",
          "text-muted transition-colors duration-150",
          "hover:bg-accent hover:text-foreground"
        )}
        aria-label="Toggle theme"
      >
        <ActiveIcon size={18} weight="duotone" />
      </button>
      {dropdown}
    </>
  );
}
