import { useState, useRef, useEffect, useCallback } from "react";
import { createPortal } from "react-dom";
import { CaretDown, Check } from "@phosphor-icons/react";
import { cn } from "@/utils/cn";

export interface SelectOption<T extends string | number = string> {
  value: T;
  label: string;
  icon?: React.ReactNode;
}

interface SelectProps<T extends string | number = string> {
  value: T | undefined;
  onChange: (value: T) => void;
  options: SelectOption<T>[];
  placeholder?: string;
  disabled?: boolean;
  className?: string;
  icon?: React.ReactNode;
}

interface DropdownPosition {
  top: number;
  left: number;
  width: number;
  openUpward: boolean;
}

export function Select<T extends string | number = string>({
  value,
  onChange,
  options,
  placeholder = "Select...",
  disabled = false,
  className,
  icon,
}: SelectProps<T>) {
  const [isOpen, setIsOpen] = useState(false);
  const [position, setPosition] = useState<DropdownPosition | null>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const updatePosition = useCallback(() => {
    if (!buttonRef.current) return;

    const rect = buttonRef.current.getBoundingClientRect();
    const dropdownHeight = Math.min(options.length * 40 + 8, 240);
    const viewportHeight = window.innerHeight;
    const spaceBelow = viewportHeight - rect.bottom;
    const spaceAbove = rect.top;
    const openUpward =
      spaceBelow < dropdownHeight && spaceAbove > spaceBelow;

    setPosition({
      top: openUpward ? rect.top - dropdownHeight - 4 : rect.bottom + 4,
      left: rect.left,
      width: rect.width,
      openUpward,
    });
  }, [options.length]);

  useEffect(() => {
    if (isOpen) {
      updatePosition();

      const handleScrollOrResize = () => updatePosition();
      window.addEventListener("scroll", handleScrollOrResize, true);
      window.addEventListener("resize", handleScrollOrResize);

      return () => {
        window.removeEventListener("scroll", handleScrollOrResize, true);
        window.removeEventListener("resize", handleScrollOrResize);
      };
    }
  }, [isOpen, updatePosition]);

  useEffect(() => {
    if (!isOpen) return;

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

  const selectedOption = options.find((opt) => opt.value === value);

  const handleSelect = (optionValue: T) => {
    onChange(optionValue);
    setIsOpen(false);
  };

  const dropdown =
    isOpen && position
      ? createPortal(
          <div
            ref={dropdownRef}
            style={{
              position: "fixed",
              top: position.top,
              left: position.left,
              width: position.width,
              minWidth: 160,
            }}
            className={cn(
              "z-[200] overflow-hidden rounded-lg",
              "border border-border bg-surface shadow-xl",
              "animate-in fade-in-0 duration-100",
              position.openUpward
                ? "slide-in-from-bottom-1"
                : "slide-in-from-top-1"
            )}
          >
            <div className="max-h-60 overflow-y-auto py-1">
              {options.map((option) => {
                const isSelected = option.value === value;
                return (
                  <button
                    key={String(option.value)}
                    type="button"
                    onClick={() => handleSelect(option.value)}
                    className={cn(
                      "flex w-full items-center justify-between gap-2 px-3 py-2 text-left text-sm",
                      "transition-colors duration-100",
                      isSelected
                        ? "bg-primary/10 font-medium text-primary"
                        : "text-foreground hover:bg-accent"
                    )}
                  >
                    <span className="flex items-center gap-2">
                      {option.icon}
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
    <div className={cn("relative", className)}>
      <button
        ref={buttonRef}
        type="button"
        onClick={() => !disabled && setIsOpen(!isOpen)}
        disabled={disabled}
        className={cn(
          "flex h-9 items-center justify-between gap-2 rounded-lg border border-border bg-surface px-3 text-sm font-medium text-foreground",
          "shadow-[0_1px_2px_rgba(0,0,0,0.04),0_0_0_0.5px_rgba(0,0,0,0.04)]",
          "hover:border-border/80 hover:shadow-[0_1px_3px_rgba(0,0,0,0.06),0_0_0_0.5px_rgba(0,0,0,0.06)]",
          "focus:outline-none focus:ring-2 focus:ring-primary/50 focus:ring-offset-1",
          "transition-all duration-150 cursor-pointer",
          "disabled:pointer-events-none disabled:opacity-50",
          "min-w-[140px]"
        )}
      >
        <span className="flex items-center gap-2 truncate">
          {icon}
          {selectedOption?.icon}
          {selectedOption?.label ?? placeholder}
        </span>
        <CaretDown
          size={14}
          weight="bold"
          className={cn(
            "flex-shrink-0 text-muted transition-transform duration-200",
            isOpen && "rotate-180"
          )}
        />
      </button>

      {dropdown}
    </div>
  );
}
