import { Send, Trash2 } from "lucide-react";
import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "@/design-system/components/Button";
import { EmptyState } from "@/design-system/components/EmptyState";
import { Help } from "@/design-system/components/Help";
import { IconButton } from "@/design-system/components/IconButton";
import { Notice } from "@/design-system/components/Notice";
import { Row, RowList } from "@/design-system/components/Row";
import { Select } from "@/design-system/components/Select";
import { Sheet } from "@/design-system/components/Sheet";
import { Switch } from "@/design-system/components/Switch";
import { TextField } from "@/design-system/components/TextField";
import { SettingsHeader } from "@/features/settings/SettingsHeader";
import { useConfirm } from "@/lib/confirm/ConfirmProvider";
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
  const confirm = useConfirm();
  const hooks = useWebhooks();
  const create = useCreateWebhook();
  const update = useUpdateWebhook();
  const remove = useDeleteWebhook();
  const test = useTestWebhook();
  const [adding, setAdding] = useState(false);
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
      {
        onSuccess: () => {
          setName("");
          setUrl("");
          setSecret("");
          setAdding(false);
        },
      },
    );
  }

  return (
    <div className={styles.page}>
      <SettingsHeader
        admin
        title={t("webhooks.title")}
        meta={[hooks.data ? t("settings.status.webhooks", { count: hooks.data.length }) : null]}
        primary={{ label: t("webhooks.new"), onClick: () => setAdding(true) }}
      >
        <p className={["text-secondary", styles.intro].join(" ")}>
          {t("webhooks.hint")}
          <Help title={t("webhooks.title")} as="text">
            <p>{t("webhooks.intro")}</p>
          </Help>
        </p>
      </SettingsHeader>
      {hooks.data && hooks.data.length === 0 && <EmptyState>{t("webhooks.hint")}</EmptyState>}
      {(hooks.data ?? []).length > 0 && (
        <RowList>
          {hooks.data?.map((hook) => (
            <Row
              key={hook.id}
              title={`${hook.name} · ${t(`webhooks.presets.${hook.preset}`)}`}
              meta={
                <>
                  <span>{hook.url_hint}</span>
                  <span>
                    {hook.last_status === "failed"
                      ? t("webhooks.lastFailed", { detail: hook.last_error ?? "" })
                      : hook.last_sent_at
                        ? t("webhooks.lastSent", { date: dateFormat.format(new Date(hook.last_sent_at)) })
                        : t("webhooks.notYet")}
                  </span>
                  {test.data?.id === hook.id && (
                    <span role="status">
                      {test.data.ok
                        ? t("webhooks.arrived")
                        : t("webhooks.didNotArrive", { detail: test.data.detail ?? "" })}
                    </span>
                  )}
                </>
              }
              trailing={
                <>
                  <Switch
                    label={t("webhooks.enabled")}
                    checked={hook.enabled}
                    onChange={(enabled) => update.mutate({ id: hook.id, enabled })}
                  />
                  <IconButton
                    label={t("webhooks.testNamed", { name: hook.name })}
                    icon={<Send />}
                    onClick={() => test.mutate(hook.id)}
                    disabled={test.isPending}
                  />
                  <IconButton
                    label={t("webhooks.deleteNamed", { name: hook.name })}
                    icon={<Trash2 />}
                    disabled={remove.isPending}
                    onClick={() => {
                      void confirm({
                        title: t("webhooks.deleteQuestion"),
                        text: t("webhooks.deleteNote"),
                        action: t("webhooks.delete"),
                        danger: true,
                      }).then((yes) => yes && remove.mutate(hook.id));
                    }}
                  />
                </>
              }
            />
          ))}
        </RowList>
      )}
      {(hooks.error ?? update.error ?? remove.error ?? test.error) && (
        <Notice kind="error">{(hooks.error ?? update.error ?? remove.error ?? test.error)?.message}</Notice>
      )}
      <Sheet open={adding} title={t("webhooks.new")} onClose={() => setAdding(false)}>
        <form className={styles.form} onSubmit={submit}>
          <Select
            label={t("webhooks.preset")}
            value={preset}
            onChange={(e) => setPreset(e.target.value as Preset)}
            options={PRESETS.map((value) => ({ value, label: t(`webhooks.presets.${value}`) }))}
          />
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
          {create.error && <Notice kind="error">{create.error.message}</Notice>}
          <div className={styles.actions}>
            <Button type="button" variant="quiet" onClick={() => setAdding(false)}>
              {t("common.cancel")}
            </Button>
            <Button type="submit" disabled={create.isPending || !url.trim()}>
              {t("webhooks.add")}
            </Button>
          </div>
        </form>
      </Sheet>
    </div>
  );
}
