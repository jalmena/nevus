import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "@/design-system/components/Button";
import { Notice } from "@/design-system/components/Notice";
import { TextField } from "@/design-system/components/TextField";
import styles from "./auth.module.css";

const MIN_PASSWORD = 10;

export function CredentialsForm({
  title,
  intro,
  submitLabel,
  confirm,
  pending,
  error,
  onSubmit,
}: {
  title: string;
  intro?: string;
  submitLabel: string;
  confirm?: boolean;
  pending: boolean;
  error?: string;
  onSubmit: (credentials: { username: string; password: string }) => void;
}) {
  const { t } = useTranslation();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [repeat, setRepeat] = useState("");
  const [localError, setLocalError] = useState<string | undefined>();

  function submit(event: FormEvent) {
    event.preventDefault();
    if (password.length < MIN_PASSWORD) {
      setLocalError(t("auth.passwordTooShort", { count: MIN_PASSWORD }));
      return;
    }
    if (confirm && password !== repeat) {
      setLocalError(t("auth.passwordsDiffer"));
      return;
    }
    setLocalError(undefined);
    onSubmit({ username: username.trim(), password });
  }

  return (
    <form className={styles.form} onSubmit={submit} noValidate>
      <h1>{title}</h1>
      {intro && <p className="text-secondary">{intro}</p>}
      <TextField
        label={t("auth.username")}
        name="username"
        autoComplete="username"
        autoCapitalize="none"
        required
        value={username}
        onChange={(e) => setUsername(e.target.value)}
      />
      <TextField
        label={t("auth.password")}
        name="password"
        type="password"
        autoComplete={confirm ? "new-password" : "current-password"}
        required
        hint={confirm ? t("auth.passwordHint", { count: MIN_PASSWORD }) : undefined}
        value={password}
        onChange={(e) => setPassword(e.target.value)}
      />
      {confirm && (
        <TextField
          label={t("auth.repeatPassword")}
          name="repeat"
          type="password"
          autoComplete="new-password"
          required
          value={repeat}
          onChange={(e) => setRepeat(e.target.value)}
        />
      )}
      {(localError ?? error) && <Notice kind="error">{localError ?? error}</Notice>}
      <Button type="submit" disabled={pending || !username || !password}>
        {pending ? t("common.working") : submitLabel}
      </Button>
    </form>
  );
}
