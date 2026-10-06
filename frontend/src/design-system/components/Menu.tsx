import { MoreHorizontal } from "lucide-react";
import { useEffect, useId, useRef, useState, type KeyboardEvent, type ReactNode } from "react";
import { IconButton } from "./IconButton";
import styles from "./Menu.module.css";

export interface MenuItem {
  label: string;
  icon?: ReactNode;
  onSelect: () => void;
  danger?: boolean;
  disabled?: boolean;
}

/**
 * The actions a page does not need in view: behind one "more" button, in a menu the keyboard can
 * walk (arrows move, Enter chooses, Escape closes and returns the focus to the button).
 */
export function Menu({
  label,
  items,
  icon = <MoreHorizontal />,
  showLabel = false,
}: {
  label: string;
  items: MenuItem[];
  icon?: ReactNode;
  showLabel?: boolean | "desktop";
}) {
  const [open, setOpen] = useState(false);
  const id = useId();
  const root = useRef<HTMLDivElement>(null);
  const trigger = useRef<HTMLButtonElement>(null);
  const list = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const outside = (event: PointerEvent) => {
      if (!root.current?.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener("pointerdown", outside);
    const first = list.current?.querySelector<HTMLButtonElement>("button:not(:disabled)");
    first?.focus();
    return () => document.removeEventListener("pointerdown", outside);
  }, [open]);

  function onKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    const buttons = Array.from(
      list.current?.querySelectorAll<HTMLButtonElement>("button:not(:disabled)") ?? [],
    );
    const index = buttons.findIndex((button) => button === document.activeElement);
    if (event.key === "Escape") {
      event.preventDefault();
      setOpen(false);
      trigger.current?.focus();
    } else if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      const step = event.key === "ArrowDown" ? 1 : -1;
      buttons[(index + step + buttons.length) % buttons.length]?.focus();
    } else if (event.key === "Home" || event.key === "End") {
      event.preventDefault();
      (event.key === "Home" ? buttons[0] : buttons[buttons.length - 1])?.focus();
    } else if (event.key === "Tab") {
      setOpen(false);
    }
  }

  if (items.length === 0) return null;
  return (
    <div ref={root} className={styles.root}>
      <IconButton
        ref={trigger}
        label={label}
        icon={icon}
        showLabel={showLabel}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-controls={open ? id : undefined}
        onClick={() => setOpen((value) => !value)}
      />
      {open && (
        <div
          ref={list}
          id={id}
          role="menu"
          tabIndex={-1}
          aria-label={label}
          className={styles.menu}
          onKeyDown={onKeyDown}
        >
          {items.map((item) => (
            <button
              key={item.label}
              type="button"
              role="menuitem"
              className={[styles.item, item.danger ? styles.danger : ""].join(" ")}
              disabled={item.disabled}
              onClick={() => {
                setOpen(false);
                item.onSelect();
              }}
            >
              {item.icon && (
                <span className={styles.itemIcon} aria-hidden="true">
                  {item.icon}
                </span>
              )}
              {item.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
