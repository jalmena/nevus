import { X } from "lucide-react";
import { useEffect, useId, useRef, type ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { IconButton } from "./IconButton";
import styles from "./Sheet.module.css";

/**
 * A tool that opens over the page: a sheet from the bottom on a phone, a dialog in the middle on a
 * desktop. Native <dialog>, so Escape closes it and the focus stays inside while it is open.
 */
export function Sheet({
  open,
  title,
  onClose,
  children,
}: {
  open: boolean;
  title: string;
  onClose: () => void;
  children: ReactNode;
}) {
  const { t } = useTranslation();
  const dialog = useRef<HTMLDialogElement>(null);
  const id = useId();
  useEffect(() => {
    const element = dialog.current;
    if (!element) return;
    if (open && !element.open) element.showModal();
    if (!open && element.open) element.close();
  }, [open]);
  useEffect(() => {
    // A tap on the backdrop closes the sheet; the panel itself swallows its clicks.
    const element = dialog.current;
    if (!element) return;
    const onBackdrop = (event: MouseEvent) => {
      if (event.target === element) onClose();
    };
    element.addEventListener("click", onBackdrop);
    return () => element.removeEventListener("click", onBackdrop);
  }, [onClose]);
  return (
    <dialog ref={dialog} className={styles.sheet} aria-labelledby={id} onClose={onClose}>
      <div className={styles.panel}>
        <header className={styles.head}>
          <h2 id={id} className={styles.title}>
            {title}
          </h2>
          <IconButton label={t("common.close")} icon={<X />} onClick={onClose} />
        </header>
        <div className={styles.body}>{children}</div>
      </div>
    </dialog>
  );
}
