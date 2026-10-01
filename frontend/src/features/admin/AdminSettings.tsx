import { useEffect, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";
import { Button } from "@/design-system/components/Button";
import { Card } from "@/design-system/components/Card";
import { Notice } from "@/design-system/components/Notice";
import { TextField } from "@/design-system/components/TextField";
import {
  useEmailSettings,
  useInstanceSettings,
  useSaveEmailSettings,
  useSaveInstanceSettings,
  useTestEmail,
} from "@/lib/admin";
import { supportedLanguages } from "@/lib/i18n";
import { WebhookSettings } from "./WebhookSettings";
import styles from "@/features/settings/settings.module.css";

/** For administrators: how reminder emails leave the server, and the language of new accounts. */
export function AdminSettings() {
  const { t } = useTranslation();
  const email = useEmailSettings(true);
  const save = useSaveEmailSettings();
  const test = useTestEmail();
  const instance = useInstanceSettings(true);
  const saveInstance = useSaveInstanceSettings();
  const [form, setForm] = useState({
    host: "",
    port: "587",
    security: "starttls",
    username: "",
    password: "",
    sender: "",
    public_url: "",
  });
  const [testTo, setTestTo] = useState("");

  useEffect(() => {
    if (email.data) {
      setForm({
        host: email.data.host ?? "",
        port: String(email.data.port),
        security: email.data.security,
        username: email.data.username ?? "",
        password: "",
        sender: email.data.sender ?? "",
        public_url: email.data.public_url ?? "",
      });
    }
  }, [email.data]);

  function submit(event: FormEvent) {
    event.preventDefault();
    save.mutate({
      host: form.host || null,
      port: Number(form.port) || 587,
      security: form.security as "starttls" | "ssl" | "none",
      username: form.username || null,
      password: form.password === "" ? undefined : form.password,
      sender: form.sender || null,
      public_url: form.public_url || null,
    });
  }

  const set = (key: keyof typeof form) => (e: { target: { value: string } }) =>
    setForm({ ...form, [key]: e.target.value });

  return (
    <>
      <Card className={styles.group}>
        <h2 className={styles.subheading}>{t("admin.emailTitle")}</h2>
        <p className="text-secondary">{t("admin.emailIntro")}</p>
        <form className={styles.form} onSubmit={submit}>
          <TextField label={t("admin.host")} value={form.host} onChange={set("host")} autoComplete="off" />
          <TextField label={t("admin.port")} value={form.port} onChange={set("port")} inputMode="numeric" />
          <label className={styles.row}>
            <span>{t("admin.security")}</span>
            <select value={form.security} onChange={set("security")}>
              <option value="starttls">STARTTLS</option>
              <option value="ssl">SSL/TLS</option>
              <option value="none">{t("admin.securityNone")}</option>
            </select>
          </label>
          <TextField
            label={t("admin.username")}
            value={form.username}
            onChange={set("username")}
            autoComplete="off"
          />
          <TextField
            label={t("admin.password")}
            type="password"
            value={form.password}
            onChange={set("password")}
            autoComplete="new-password"
            hint={email.data?.has_password ? t("admin.passwordKept") : undefined}
          />
          <TextField
            label={t("admin.sender")}
            value={form.sender}
            onChange={set("sender")}
            inputMode="email"
          />
          <TextField
            label={t("admin.publicUrl")}
            hint={t("admin.publicUrlHint")}
            value={form.public_url}
            onChange={set("public_url")}
            inputMode="url"
          />
          <Button type="submit" disabled={save.isPending}>
            {t("common.save")}
          </Button>
        </form>
        {save.error && <Notice kind="error">{save.error.message}</Notice>}
        {save.isSuccess && <Notice kind="success">{t("admin.saved")}</Notice>}
        <form
          className={styles.inline}
          onSubmit={(event) => {
            event.preventDefault();
            test.mutate(testTo);
          }}
        >
          <TextField
            label={t("admin.testTo")}
            value={testTo}
            onChange={(e) => setTestTo(e.target.value)}
            inputMode="email"
          />
          <Button
            type="submit"
            variant="secondary"
            disabled={!email.data?.ready || !testTo || test.isPending}
          >
            {t("admin.sendTest")}
          </Button>
        </form>
        {test.error && <Notice kind="error">{test.error.message}</Notice>}
        {test.isSuccess && <Notice kind="success">{t("admin.testSent")}</Notice>}
      </Card>
      <WebhookSettings />
      <Card className={styles.group}>
        <Link to="/evaluation">{t("admin.evaluationLink")}</Link>
      </Card>
      <Card className={styles.group}>
        <h2 className={styles.subheading}>{t("admin.instanceTitle")}</h2>
        <label className={styles.row}>
          <span>{t("admin.defaultLanguage")}</span>
          <select
            value={instance.data?.default_language ?? "en"}
            onChange={(e) => saveInstance.mutate({ default_language: e.target.value as "en" | "es" })}
          >
            {supportedLanguages.map((code) => (
              <option key={code} value={code}>
                {t(`languages.${code}`)}
              </option>
            ))}
          </select>
        </label>
      </Card>
    </>
  );
}
