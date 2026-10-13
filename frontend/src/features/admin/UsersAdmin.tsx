import { KeyRound, ShieldOff, UserCheck, UserX } from "lucide-react";
import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "@/design-system/components/Button";
import { Help } from "@/design-system/components/Help";
import { Menu } from "@/design-system/components/Menu";
import { Notice } from "@/design-system/components/Notice";
import { Row, RowList } from "@/design-system/components/Row";
import { Select } from "@/design-system/components/Select";
import { Sheet } from "@/design-system/components/Sheet";
import { TextField } from "@/design-system/components/TextField";
import { SettingsHeader } from "@/features/settings/SettingsHeader";
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
  const [adding, setAdding] = useState(false);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<"member" | "admin">("member");
  const [passwordFor, setPasswordFor] = useState<UserOut | null>(null);
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
          setAdding(false);
        },
      },
    );
  }

  function setPasswordOf(event: FormEvent) {
    event.preventDefault();
    if (!passwordFor) return;
    resetPassword.mutate(
      { id: passwordFor.id, password: newPassword },
      { onSuccess: () => setPasswordFor(null) },
    );
  }

  return (
    <div className={styles.page}>
      <SettingsHeader
        admin
        title={t("accounts.title")}
        meta={[users.data ? t("settings.status.accounts", { count: users.data.length }) : null]}
        primary={local ? { label: t("accounts.addTitle"), onClick: () => setAdding(true) } : undefined}
      >
        <p className={["text-secondary", styles.intro].join(" ")}>
          {t("accounts.hint")}
          <Help title={t("accounts.title")} as="text">
            <p>{local ? t("accounts.intro") : t("accounts.introProxy")}</p>
          </Help>
        </p>
      </SettingsHeader>
      <RowList>
        {(users.data ?? []).map((user) => (
          <Row
            key={user.id}
            title={user.username}
            meta={describe(user)}
            trailing={
              user.id !== me?.id ? (
                <Menu
                  label={t("accounts.actionsFor", { name: user.username })}
                  items={[
                    {
                      label: user.disabled_at ? t("accounts.enable") : t("accounts.disable"),
                      icon: user.disabled_at ? <UserCheck /> : <UserX />,
                      disabled: toggle.isPending,
                      onSelect: () => toggle.mutate({ id: user.id, enabled: Boolean(user.disabled_at) }),
                    },
                    ...(local
                      ? [
                          {
                            label: t("accounts.newPassword"),
                            icon: <KeyRound />,
                            onSelect: () => {
                              setPasswordFor(user);
                              setNewPassword("");
                            },
                          },
                        ]
                      : []),
                    ...(local && user.totp_enabled
                      ? [
                          {
                            label: t("accounts.resetSecondFactor"),
                            icon: <ShieldOff />,
                            danger: true,
                            disabled: resetFactor.isPending,
                            onSelect: () => resetFactor.mutate(user.id),
                          },
                        ]
                      : []),
                  ]}
                />
              ) : undefined
            }
          />
        ))}
      </RowList>
      {resetFactor.isSuccess && <Notice kind="success">{t("accounts.secondFactorReset")}</Notice>}
      {resetPassword.isSuccess && passwordFor === null && (
        <Notice kind="success">{t("accounts.passwordSet")}</Notice>
      )}
      {failure && <Notice kind="error">{failure.message}</Notice>}

      <Sheet open={adding} title={t("accounts.addTitle")} onClose={() => setAdding(false)}>
        <form className={styles.form} onSubmit={add}>
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
          <Select
            label={t("accounts.role")}
            value={role}
            onChange={(e) => setRole(e.target.value as "member" | "admin")}
            options={[
              { value: "member", label: t("settings.roles.member") },
              { value: "admin", label: t("settings.roles.admin") },
            ]}
          />
          {create.error && <Notice kind="error">{create.error.message}</Notice>}
          <div className={styles.actions}>
            <Button type="button" variant="quiet" onClick={() => setAdding(false)}>
              {t("common.cancel")}
            </Button>
            <Button
              type="submit"
              disabled={create.isPending || username.trim().length < 2 || password.length < MIN_PASSWORD}
            >
              {t("accounts.add")}
            </Button>
          </div>
        </form>
      </Sheet>
      <Sheet
        open={passwordFor !== null}
        title={passwordFor ? t("accounts.newPasswordNamed", { name: passwordFor.username }) : ""}
        onClose={() => setPasswordFor(null)}
      >
        <form className={styles.form} onSubmit={setPasswordOf}>
          <TextField
            label={passwordFor ? t("accounts.temporaryPassword", { name: passwordFor.username }) : ""}
            type="text"
            autoComplete="off"
            hint={t("auth.passwordHint", { count: MIN_PASSWORD })}
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
          />
          {resetPassword.error && <Notice kind="error">{resetPassword.error.message}</Notice>}
          <div className={styles.actions}>
            <Button type="button" variant="quiet" onClick={() => setPasswordFor(null)}>
              {t("common.cancel")}
            </Button>
            <Button type="submit" disabled={newPassword.length < MIN_PASSWORD || resetPassword.isPending}>
              {t("common.save")}
            </Button>
          </div>
        </form>
      </Sheet>
    </div>
  );
}
