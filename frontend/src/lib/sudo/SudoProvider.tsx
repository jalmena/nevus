import {
  createContext,
  useCallback,
  useContext,
  useRef,
  useState,
  type FormEvent,
  type ReactNode,
} from "react";
import { useTranslation } from "react-i18next";
import { Button } from "@/design-system/components/Button";
import { Notice } from "@/design-system/components/Notice";
import { Sheet } from "@/design-system/components/Sheet";
import { TextField } from "@/design-system/components/TextField";
import { api, errorMessage } from "@/lib/api/client";
import { useInstance } from "@/lib/auth/session";
import styles from "./sudo.module.css";

type Ask = () => Promise<void>;
const Context = createContext<Ask>(() => Promise.reject(new Error("no sudo provider")));

/**
 * Asks for the password again when the server says an action needs it, then lets the action retry.
 * Behind a single sign-on proxy there is no local password: the dialog asks for a plain confirmation.
 */
export function SudoProvider({ children }: { children: ReactNode }) {
  const { t } = useTranslation();
  const proxy = useInstance().data?.auth_mode === "proxy";
  const pending = useRef<{ resolve: () => void; reject: (error: Error) => void } | null>(null);
  const [open, setOpen] = useState(false);
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const ask = useCallback<Ask>(
    () =>
      new Promise<void>((resolve, reject) => {
        pending.current = { resolve, reject };
        setPassword("");
        setError(null);
        setOpen(true);
      }),
    [],
  );

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    const { error: failure, response } = await api.POST("/api/auth/sudo", {
      body: proxy ? {} : { password },
    });
    setBusy(false);
    if (!response.ok) {
      setError(errorMessage(failure, t("sudo.wrong")));
      return;
    }
    setOpen(false);
    pending.current?.resolve();
    pending.current = null;
  }

  const cancel = useCallback(() => {
    setOpen(false);
    if (pending.current) pending.current.reject(new Error(t("sudo.cancelled")));
    pending.current = null;
  }, [t]);

  return (
    <Context.Provider value={ask}>
      {children}
      <Sheet open={open} title={t("sudo.title")} onClose={cancel}>
        <form onSubmit={submit} className={styles.form}>
          <p className="text-secondary">{proxy ? t("sudo.introProxy") : t("sudo.intro")}</p>
          {!proxy && (
            <TextField
              label={t("auth.password")}
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          )}
          {error && <Notice kind="error">{error}</Notice>}
          <div className={styles.actions}>
            <Button type="button" variant="quiet" onClick={cancel}>
              {t("common.cancel")}
            </Button>
            <Button type="submit" disabled={busy}>
              {proxy ? t("sudo.confirmProxy") : t("sudo.confirm")}
            </Button>
          </div>
        </form>
      </Sheet>
    </Context.Provider>
  );
}

export const useSudo = () => useContext(Context);

/** Run a request; if the server wants the password again, ask for it once and run it again. */
export async function withSudo<T extends { response: Response }>(
  ask: Ask,
  run: () => Promise<T>,
): Promise<T> {
  const first = await run();
  if (first.response.status === 403 && first.response.headers.get("x-sudo-required") === "1") {
    await ask();
    return run();
  }
  return first;
}
