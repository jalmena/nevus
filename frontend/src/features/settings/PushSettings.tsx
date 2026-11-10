import { Send } from "lucide-react";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Notice } from "@/design-system/components/Notice";
import { StatusChip } from "@/design-system/components/StatusChip";
import {
  currentSubscription,
  pushSupported,
  useSubscribeDevice,
  useTestPush,
  useUnsubscribeDevice,
  usePushStatus,
} from "@/lib/push";
import { SettingsHeader } from "./SettingsHeader";
import styles from "./settings.module.css";

/** Whether this browser holds a subscription; re-checked when the server's count changes. */
export function useThisDevice(count: number | undefined): boolean | null {
  const [thisDevice, setThisDevice] = useState<boolean | null>(null);
  useEffect(() => {
    let alive = true;
    void currentSubscription().then((subscription) => {
      if (alive) setThisDevice(Boolean(subscription));
    });
    return () => {
      alive = false;
    };
  }, [count]);
  return thisDevice;
}

/**
 * Notifications to this device when marks are due. The page always opens: when this browser cannot
 * take them, or the server does not send them, it says so (and an administrator reads how to turn
 * them on) instead of showing nothing.
 */
export function PushSettings({ admin }: { admin: boolean }) {
  const { t } = useTranslation();
  const supported = pushSupported();
  const status = usePushStatus();
  const subscribe = useSubscribeDevice();
  const unsubscribe = useUnsubscribeDevice();
  const test = useTestPush();
  const count = status.data?.subscriptions;
  const thisDevice = useThisDevice(count);
  const [known, setKnown] = useState<boolean | null>(null);
  const on = known ?? thisDevice;
  const enabled = Boolean(status.data?.enabled);
  const ready = supported && enabled;
  const failure = subscribe.error ?? unsubscribe.error ?? test.error;
  const publicKey = status.data?.public_key ?? "";
  return (
    <div className={styles.page}>
      <SettingsHeader
        help={{
          title: t("push.title"),
          content: (
            <>
              <p>{t("push.intro")}</p>
              <p>{t("push.introMore")}</p>
              <p>{t("push.note")}</p>
            </>
          ),
        }}
        admin={admin}
        title={t("push.title")}
        chip={<StatusChip kind="experimental">{t("proposals.experimental")}</StatusChip>}
        meta={
          ready
            ? [
                on ? t("push.onThisDevice") : t("push.offThisDevice"),
                t("push.devices", { count: count ?? 0 }),
              ]
            : undefined
        }
        primary={
          !ready
            ? undefined
            : on
              ? {
                  label: t("push.turnOff"),
                  pending: unsubscribe.isPending,
                  onClick: () => unsubscribe.mutate(undefined, { onSuccess: () => setKnown(false) }),
                }
              : {
                  label: t("push.turnOn"),
                  pending: subscribe.isPending,
                  disabled: !publicKey,
                  onClick: () => subscribe.mutate(publicKey, { onSuccess: () => setKnown(true) }),
                }
        }
        actions={
          ready && count
            ? [
                {
                  key: "test",
                  label: t("push.test"),
                  icon: <Send />,
                  onClick: () => test.mutate(),
                  disabled: test.isPending,
                },
              ]
            : []
        }
      ></SettingsHeader>
      {status.error && <Notice kind="error">{status.error.message}</Notice>}
      {status.data && !enabled && (
        <Notice kind="info">{admin ? t("push.serverOffAdmin") : t("push.serverOff")}</Notice>
      )}
      {enabled && !supported && (
        <Notice kind="info">
          {t("push.unsupported")} {t("push.note")}
        </Notice>
      )}
      {test.data && (
        <Notice kind={test.data.sent > 0 ? "success" : "attention"}>
          {t("push.tested", { sent: test.data.sent, failed: test.data.failed })}
        </Notice>
      )}
      {failure && <Notice kind="error">{failure.message}</Notice>}
    </div>
  );
}
