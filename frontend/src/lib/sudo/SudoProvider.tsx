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
import { TextField } from "@/design-system/components/TextField";
import { api, errorMessage } from "@/lib/api/client";
import styles from "./sudo.module.css";

type Ask = () => Promise<void>;
const Context = createContext<Ask>(() => Promise.reject(new Error("no sudo provider")));

/** Asks for the password again when the server says an action needs it, then lets the action retry. */
export function SudoProvider({ children }: { children: ReactNode }) {
  const { t } = useTranslation();
  const dialog = useRef<HTMLDialogElement>(null);
  const pending = useRef<{ resolve: () => void; reject: (error: Error) => void } | null>(null);
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const ask = useCallback<Ask>(
    () =>
      new Promise<void>((resolve, reject) => {
        pending.current = { resolve, reject };
        setPassword("");
        setError(null);
        const element = dialog.current;
        if (element?.showModal) element.showModal();
        else element?.setAttribute("open", "");
      }),
    [],
  );

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    const { error: failure, response } = await api.POST("/api/auth/sudo", { body: { password } });
    setBusy(false);
    if (!response.ok) {
      setError(errorMessage(failure, t("sudo.wrong")));
      return;
    }
    close();
    pending.current?.resolve();
    pending.current = null;
  }

  function close() {
    const element = dialog.current;
    if (element?.close) element.close();
    else element?.removeAttribute("open");
  }

  function cancel() {
    close();
    pending.current?.reject(new Error(t("sudo.cancelled")));
    pending.current = null;
  }

  return (
    <Context.Provider value={ask}>
      {children}
      <dialog ref={dialog} className={styles.dialog} aria-labelledby="sudo-title" onCancel={cancel}>
        <form onSubmit={submit} className={styles.form}>
          <h2 id="sudo-title">{t("sudo.title")}</h2>
          <p className="text-secondary">{t("sudo.intro")}</p>
          <TextField
            label={t("auth.password")}
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          {error && <Notice kind="error">{error}</Notice>}
          <div className={styles.actions}>
            <Button type="submit" disabled={busy || !password}>
              {t("sudo.confirm")}
            </Button>
            <Button type="button" variant="quiet" onClick={cancel}>
              {t("common.cancel")}
            </Button>
          </div>
        </form>
      </dialog>
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
