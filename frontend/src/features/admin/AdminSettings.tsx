import { FlaskConical } from "lucide-react";
import { useEffect, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "@/design-system/components/Button";
import { Notice } from "@/design-system/components/Notice";
import { Row, RowList } from "@/design-system/components/Row";
import { Select } from "@/design-system/components/Select";
import { TextField } from "@/design-system/components/TextField";
import { SettingsHeader } from "@/features/settings/SettingsHeader";
import {
  useEmailSettings,
  useInstanceSettings,
  useSaveEmailSettings,
  useSaveInstanceSettings,
  useTestEmail,
} from "@/lib/admin";
import { languageNames, supportedLanguages, type Language } from "@/lib/i18n";
import styles from "@/features/settings/settings.module.css";

/** For administrators: how reminder emails leave the server. */
export function AdminSettings() {
  const { t } = useTranslation();
  const email = useEmailSettings(true);
  const save = useSaveEmailSettings();
  const test = useTestEmail();
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
    <div className={styles.page}>
      <SettingsHeader
        help={{
          title: t("admin.emailTitle"),
          content: (
            <>
              <p>{t("admin.emailHint")}</p>
              <p>{t("admin.emailIntro")}</p>
            </>
          ),
        }}
        admin
        title={t("admin.emailTitle")}
        meta={[
          email.data
            ? email.data.ready
              ? t("settings.status.emailReady")
              : t("settings.status.emailNotReady")
            : null,
        ]}
      ></SettingsHeader>
      <form className={styles.form} onSubmit={submit}>
        <TextField label={t("admin.host")} value={form.host} onChange={set("host")} autoComplete="off" />
        <TextField label={t("admin.port")} value={form.port} onChange={set("port")} inputMode="numeric" />
        <Select
          label={t("admin.security")}
          value={form.security}
          onChange={set("security")}
          options={[
            { value: "starttls", label: "STARTTLS" },
            { value: "ssl", label: "SSL/TLS" },
            { value: "none", label: t("admin.securityNone") },
          ]}
        />
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
        <TextField label={t("admin.sender")} value={form.sender} onChange={set("sender")} inputMode="email" />
        <TextField
          label={t("admin.publicUrl")}
          hint={t("admin.publicUrlHint")}
          value={form.public_url}
          onChange={set("public_url")}
          inputMode="url"
        />
        <div className={styles.actions}>
          <Button type="submit" disabled={save.isPending}>
            {t("common.save")}
          </Button>
        </div>
      </form>
      {save.error && <Notice kind="error">{save.error.message}</Notice>}
      {save.isSuccess && <Notice kind="success">{t("admin.saved")}</Notice>}
      <form
        className={styles.form}
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
        <div className={styles.actions}>
          <Button
            type="submit"
            variant="secondary"
            disabled={!email.data?.ready || !testTo || test.isPending}
          >
            {t("admin.sendTest")}
          </Button>
        </div>
      </form>
      {test.error && <Notice kind="error">{test.error.message}</Notice>}
      {test.isSuccess && <Notice kind="success">{t("admin.testSent")}</Notice>}
    </div>
  );
}

/** For administrators: the language of new accounts, and the way to the evaluation set. */
export function InstanceSection() {
  const { t } = useTranslation();
  const instance = useInstanceSettings(true);
  const saveInstance = useSaveInstanceSettings();
  return (
    <div className={styles.page}>
      <SettingsHeader
        admin
        title={t("admin.instanceTitle")}
        meta={[
          instance.data
            ? t("settings.status.language", { language: languageNames[instance.data.default_language] })
            : null,
        ]}
        help={{ title: t("admin.instanceTitle"), content: <p>{t("admin.instanceHint")}</p> }}
      />
      <RowList>
        <Row
          title={t("admin.defaultLanguage")}
          trailing={
            <Select
              label={t("admin.defaultLanguage")}
              labelHidden
              value={instance.data?.default_language ?? "en"}
              onChange={(e) => saveInstance.mutate({ default_language: e.target.value as Language })}
              options={supportedLanguages.map((code) => ({ value: code, label: languageNames[code] }))}
            />
          }
        />
        <Row
          to="/evaluation"
          leading={<FlaskConical />}
          title={t("evaluation.title")}
          meta={t("admin.instanceHint")}
          chevron
        />
      </RowList>
      {saveInstance.isSuccess && (
        <p className="text-secondary" role="status">
          {t("common.saved")}
        </p>
      )}
      {saveInstance.error && <Notice kind="error">{saveInstance.error.message}</Notice>}
    </div>
  );
}
