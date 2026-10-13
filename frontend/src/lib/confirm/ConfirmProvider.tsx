import { createContext, useCallback, useContext, useRef, useState, type ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "@/design-system/components/Button";
import { Sheet } from "@/design-system/components/Sheet";
import styles from "./confirm.module.css";

export interface Confirmation {
  /** The verb, with a question mark: "Move the mark to the trash?" */
  title: string;
  /** One sentence of consequence. */
  text: string;
  /** The verb again, on the button. */
  action: string;
  danger?: boolean;
}

type Ask = (confirmation: Confirmation) => Promise<boolean>;
const Context = createContext<Ask>(() => Promise.resolve(false));

/** One dialog for every irreversible action: the verb, its consequence, the verb, Cancel. */
export function ConfirmProvider({ children }: { children: ReactNode }) {
  const { t } = useTranslation();
  const [current, setCurrent] = useState<Confirmation | null>(null);
  const pending = useRef<((value: boolean) => void) | null>(null);
  const ask = useCallback<Ask>((confirmation) => {
    setCurrent(confirmation);
    return new Promise<boolean>((resolve) => {
      pending.current = resolve;
    });
  }, []);
  function settle(value: boolean) {
    pending.current?.(value);
    pending.current = null;
    setCurrent(null);
  }
  return (
    <Context.Provider value={ask}>
      {children}
      <Sheet open={current !== null} title={current?.title ?? ""} onClose={() => settle(false)}>
        <p className="text-secondary">{current?.text}</p>
        <div className={styles.actions}>
          <Button variant="quiet" onClick={() => settle(false)}>
            {t("common.cancel")}
          </Button>
          <Button variant={current?.danger ? "dangerFilled" : "primary"} onClick={() => settle(true)}>
            {current?.action}
          </Button>
        </div>
      </Sheet>
    </Context.Provider>
  );
}

/** Asks the person before an irreversible action; resolves to whether they agreed. */
export function useConfirm(): Ask {
  return useContext(Context);
}
