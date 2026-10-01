import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "@/design-system/components/Button";
import { Card } from "@/design-system/components/Card";
import { Notice } from "@/design-system/components/Notice";
import { TextField } from "@/design-system/components/TextField";
import {
  PRESETS,
  useCreateWebhook,
  useDeleteWebhook,
  useTestWebhook,
  useUpdateWebhook,
  useWebhooks,
  type Preset,
} from "@/lib/notifications";
import styles from "@/features/settings/settings.module.css";

/** For administrators: the daily list of due marks, sent to Home Assistant, ntfy, Gotify, n8n or any address. */
export function WebhookSettings() {
  const { t, i18n } = useTranslation();
  const hooks = useWebhooks();
  const create = useCreateWebhook();
  const update = useUpdateWebhook();
  const remove = useDeleteWebhook();
  const test = useTestWebhook();
  const [name, setName] = useState("");
  const [preset, setPreset] = useState<Preset>("home_assistant");
  const [url, setUrl] = useState("");
  const [secret, setSecret] = useState("");
  const dateFormat = new Intl.DateTimeFormat(i18n.resolvedLanguage, {
    dateStyle: "medium",
    timeStyle: "short",
  });

  function submit(event: FormEvent) {
    event.preventDefault();
    create.mutate(
      {
        name: name.trim() || t(`webhooks.presets.${preset}`),
        preset,
        url: url.trim(),
        secret: secret || null,
        enabled: true,
      },
      { onSuccess: () => (setName(""), setUrl(""), setSecret("")) },
    );
  }

  return (
    <Card className={styles.group}>
      <h2 className={styles.subheading}>{t("webhooks.title")}</h2>
      <p className="text-secondary">{t("webhooks.intro")}</p>
      {(hooks.data ?? []).length > 0 && (
        <ul className={styles.hooks}>
          {hooks.data?.map((hook) => (
            <li key={hook.id} className={styles.hook}>
              <span className={styles.hookWhat}>
                <span className={styles.hookName}>
                  {hook.name} · {t(`webhooks.presets.${hook.preset}`)}
                </span>
                <span className="text-secondary">{hook.url_hint}</span>
                <span className="text-secondary">
                  {hook.last_status === "failed"
                    ? t("webhooks.lastFailed", { detail: hook.last_error ?? "" })
                    : hook.last_sent_at
                      ? t("webhooks.lastSent", { date: dateFormat.format(new Date(hook.last_sent_at)) })
                      : t("webhooks.notYet")}
                </span>
              </span>
              <span className={styles.hookActions}>
                <label className={styles.row}>
                  <input
                    type="checkbox"
                    checked={hook.enabled}
                    onChange={(e) => update.mutate({ id: hook.id, enabled: e.target.checked })}
                  />
                  {t("webhooks.enabled")}
                </label>
                <Button
                  variant="secondary"
                  onClick={() => test.mutate(hook.id)}
                  disabled={test.isPending}
                  aria-label={t("webhooks.testNamed", { name: hook.name })}
                >
                  {t("webhooks.test")}
                </Button>
                <Button
                  variant="quiet"
                  onClick={() => remove.mutate(hook.id)}
                  disabled={remove.isPending}
                  aria-label={t("webhooks.deleteNamed", { name: hook.name })}
                >
                  {t("webhooks.delete")}
                </Button>
              </span>
              {test.data?.id === hook.id &&
                (test.data.ok ? (
                  <Notice kind="success">{t("webhooks.arrived")}</Notice>
                ) : (
                  <Notice kind="error">
                    {t("webhooks.didNotArrive", { detail: test.data.detail ?? "" })}
                  </Notice>
                ))}
            </li>
          ))}
        </ul>
      )}
      <form className={styles.form} onSubmit={submit}>
        <label className={styles.row}>
          <span>{t("webhooks.preset")}</span>
          <select value={preset} onChange={(e) => setPreset(e.target.value as Preset)}>
            {PRESETS.map((value) => (
              <option key={value} value={value}>
                {t(`webhooks.presets.${value}`)}
              </option>
            ))}
          </select>
        </label>
        <TextField
          label={t("webhooks.name")}
          value={name}
          onChange={(e) => setName(e.target.value)}
          maxLength={80}
        />
        <TextField
          label={t("webhooks.url")}
          hint={t(`webhooks.urlHints.${preset}`)}
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          inputMode="url"
          autoComplete="off"
          required
        />
        <TextField
          label={t("webhooks.secret")}
          hint={t(`webhooks.secretHints.${preset}`)}
          type="password"
          value={secret}
          onChange={(e) => setSecret(e.target.value)}
          autoComplete="new-password"
        />
        <Button type="submit" disabled={create.isPending || !url.trim()}>
          {t("webhooks.add")}
        </Button>
      </form>
      {create.error && <Notice kind="error">{create.error.message}</Notice>}
    </Card>
  );
}
