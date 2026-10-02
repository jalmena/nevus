import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "@/design-system/components/Button";
import { Card } from "@/design-system/components/Card";
import { Notice } from "@/design-system/components/Notice";
import { TextField } from "@/design-system/components/TextField";
import {
  useCreateUser,
  useResetUserPassword,
  useResetUserSecondFactor,
  useSetUserEnabled,
  useUsers,
  type UserOut,
} from "@/lib/admin";
import { useInstance, useSession } from "@/lib/auth/session";
import styles from "@/features/settings/settings.module.css";

const MIN_PASSWORD = 10;

/** The household's accounts: who can sign in, with what role, and the ways back in when something is lost. */
export function UsersAdmin() {
  const { t, i18n } = useTranslation();
  const local = useInstance().data?.auth_mode !== "proxy";
  const me = useSession().data?.user;
  const users = useUsers();
  const create = useCreateUser();
  const toggle = useSetUserEnabled();
  const resetPassword = useResetUserPassword();
  const resetFactor = useResetUserSecondFactor();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<"member" | "admin">("member");
  const [passwordFor, setPasswordFor] = useState<string | null>(null);
  const [newPassword, setNewPassword] = useState("");
  const dateFormat = new Intl.DateTimeFormat(i18n.resolvedLanguage, { dateStyle: "medium" });
  const failure = users.error ?? create.error ?? toggle.error ?? resetPassword.error ?? resetFactor.error;

  function describe(user: UserOut) {
    const parts = [t(`settings.roles.${user.role}`)];
    if (user.disabled_at) parts.push(t("accounts.disabled"));
    if (user.totp_enabled) parts.push(t("accounts.secondFactorOn"));
    if (user.last_login_at)
      parts.push(t("accounts.lastSignIn", { date: dateFormat.format(new Date(user.last_login_at)) }));
    return parts.join(" · ");
  }

  function add(event: FormEvent) {
    event.preventDefault();
    create.mutate(
      { username: username.trim(), password, role },
      {
        onSuccess: () => {
          setUsername("");
          setPassword("");
        },
      },
    );
  }

  function setPasswordOf(user: UserOut, event: FormEvent) {
    event.preventDefault();
    resetPassword.mutate({ id: user.id, password: newPassword }, { onSuccess: () => setPasswordFor(null) });
  }

  return (
    <Card className={styles.group}>
      <h2 className={styles.subheading}>{t("accounts.title")}</h2>
      <p className="text-secondary">{local ? t("accounts.intro") : t("accounts.introProxy")}</p>
      <ul className={styles.users}>
        {(users.data ?? []).map((user) => (
          <li key={user.id} className={styles.user}>
            <div className={styles.userWhat}>
              <strong>{user.username}</strong>
              <span className="text-secondary">{describe(user)}</span>
            </div>
            {user.id !== me?.id && (
              <div className={styles.userActions}>
                <Button
                  variant="quiet"
                  disabled={toggle.isPending}
                  aria-label={t(user.disabled_at ? "accounts.enableNamed" : "accounts.disableNamed", {
                    name: user.username,
                  })}
                  onClick={() => toggle.mutate({ id: user.id, enabled: Boolean(user.disabled_at) })}
                >
                  {user.disabled_at ? t("accounts.enable") : t("accounts.disable")}
                </Button>
                {local && (
                  <Button
                    variant="quiet"
                    aria-label={t("accounts.newPasswordNamed", { name: user.username })}
                    onClick={() => {
                      setPasswordFor(passwordFor === user.id ? null : user.id);
                      setNewPassword("");
                    }}
                  >
                    {t("accounts.newPassword")}
                  </Button>
                )}
                {local && user.totp_enabled && (
                  <Button
                    variant="quiet"
                    disabled={resetFactor.isPending}
                    aria-label={t("accounts.resetSecondFactorNamed", { name: user.username })}
                    onClick={() => resetFactor.mutate(user.id)}
                  >
                    {t("accounts.resetSecondFactor")}
                  </Button>
                )}
              </div>
            )}
            {passwordFor === user.id && (
              <form className={styles.inline} onSubmit={(event) => setPasswordOf(user, event)}>
                <TextField
                  label={t("accounts.temporaryPassword", { name: user.username })}
                  type="text"
                  autoComplete="off"
                  hint={t("auth.passwordHint", { count: MIN_PASSWORD })}
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                />
                <Button
                  type="submit"
                  variant="secondary"
                  disabled={newPassword.length < MIN_PASSWORD || resetPassword.isPending}
                >
                  {t("common.save")}
                </Button>
                <Button type="button" variant="quiet" onClick={() => setPasswordFor(null)}>
                  {t("common.cancel")}
                </Button>
              </form>
            )}
          </li>
        ))}
      </ul>
      {local && (
        <form className={styles.form} onSubmit={add}>
          <h3>{t("accounts.addTitle")}</h3>
          <TextField
            label={t("auth.username")}
            autoCapitalize="none"
            autoComplete="off"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
          />
          <TextField
            label={t("accounts.temporaryPasswordNew")}
            type="text"
            autoComplete="off"
            hint={t("accounts.temporaryHint", { count: MIN_PASSWORD })}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          <label className={styles.row}>
            <span>{t("accounts.role")}</span>
            <select value={role} onChange={(e) => setRole(e.target.value as "member" | "admin")}>
              <option value="member">{t("settings.roles.member")}</option>
              <option value="admin">{t("settings.roles.admin")}</option>
            </select>
          </label>
          <div>
            <Button
              type="submit"
              variant="secondary"
              disabled={create.isPending || username.trim().length < 2 || password.length < MIN_PASSWORD}
            >
              {t("accounts.add")}
            </Button>
          </div>
        </form>
      )}
      {resetFactor.isSuccess && <Notice kind="success">{t("accounts.secondFactorReset")}</Notice>}
      {resetPassword.isSuccess && passwordFor === null && (
        <Notice kind="success">{t("accounts.passwordSet")}</Notice>
      )}
      {failure && <Notice kind="error">{failure.message}</Notice>}
    </Card>
  );
}
