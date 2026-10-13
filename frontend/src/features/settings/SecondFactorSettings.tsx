import { Check, Copy, RefreshCw, ShieldOff } from "lucide-react";
import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { IconButton } from "@/design-system/components/IconButton";
import { Notice } from "@/design-system/components/Notice";
import { TextField } from "@/design-system/components/TextField";
import { useInstance } from "@/lib/auth/session";
import {
  useNewRecoveryCodes,
  useTotpDisable,
  useTotpEnable,
  useTotpSetup,
  useTotpStatus,
} from "@/lib/auth/totp";
import { SettingsHeader } from "./SettingsHeader";
import styles from "./settings.module.css";

const grouped = (secret: string) => secret.replace(/(.{4})/g, "$1 ").trim();

/** Save the recovery codes as a small text file, for a password manager or a drawer. */
function download(codes: string[]) {
  const blob = new Blob([`neVus recovery codes\n\n${codes.join("\n")}\n`], { type: "text/plain" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = "nevus-recovery-codes.txt";
  anchor.click();
  URL.revokeObjectURL(url);
}

/** A second factor for the account: an authenticator app, with recovery codes for when it is lost. */
export function SecondFactorSettings({ admin }: { admin: boolean }) {
  const { t } = useTranslation();
  const local = useInstance().data?.auth_mode !== "proxy";
  const status = useTotpStatus(local);
  const setup = useTotpSetup();
  const enable = useTotpEnable();
  const disable = useTotpDisable();
  const renew = useNewRecoveryCodes();
  const [code, setCode] = useState("");
  const [codes, setCodes] = useState<string[] | null>(null);
  const [copied, setCopied] = useState(false);
  if (!local || !status.data) return null;
  const failure = setup.error ?? disable.error ?? renew.error;
  const on = status.data.enabled;
  const settingUp = Boolean(setup.data) && !on;

  function turnOn(event?: FormEvent) {
    event?.preventDefault();
    enable.mutate(
      { code },
      {
        onSuccess: (fresh) => {
          setCodes(fresh);
          setCode("");
          setup.reset();
        },
      },
    );
  }

  async function copySecret() {
    try {
      await navigator.clipboard.writeText(setup.data?.secret ?? "");
      setCopied(true);
    } catch {
      setCopied(false);
    }
  }

  return (
    <div className={styles.page}>
      <SettingsHeader
        help={{
          title: t("secondFactor.title"),
          content: (
            <>
              <p>{t("secondFactor.hint")}</p>
              <p>{t("secondFactor.intro")}</p>
            </>
          ),
        }}
        admin={admin}
        title={t("secondFactor.title")}
        meta={[on ? t("secondFactor.on", { count: status.data.recovery_codes_left }) : t("secondFactor.off")]}
        primary={
          codes
            ? { label: t("secondFactor.codesDone"), onClick: () => setCodes(null) }
            : settingUp
              ? { label: t("secondFactor.turnOn"), pending: enable.isPending, onClick: () => turnOn() }
              : !on
                ? { label: t("secondFactor.setUp"), onClick: () => setup.mutate() }
                : undefined
        }
        secondary={
          codes
            ? { label: t("secondFactor.download"), onClick: () => download(codes) }
            : settingUp
              ? { label: t("common.cancel"), onClick: () => setup.reset() }
              : undefined
        }
        menu={
          on
            ? [
                {
                  label: t("secondFactor.newCodes"),
                  icon: <RefreshCw />,
                  onSelect: () => renew.mutate(undefined, { onSuccess: (fresh) => setCodes(fresh) }),
                },
                {
                  label: t("secondFactor.turnOff"),
                  icon: <ShieldOff />,
                  danger: true,
                  onSelect: () => disable.mutate(),
                },
              ]
            : []
        }
      ></SettingsHeader>
      {settingUp && setup.data && (
        <form className={styles.form} onSubmit={turnOn}>
          <ol className={styles.steps}>
            <li>{t("secondFactor.step1")}</li>
            <li>{t("secondFactor.step2")}</li>
            <li>{t("secondFactor.step3")}</li>
          </ol>
          <img
            className={styles.qr}
            alt={t("secondFactor.qrAlt")}
            src={`data:image/svg+xml;utf8,${encodeURIComponent(setup.data.qr_svg)}`}
          />
          <div className={styles.secretRow}>
            <span className="text-secondary">{t("secondFactor.orType")}</span>
            <code className={["numeric", styles.secret].join(" ")}>{grouped(setup.data.secret)}</code>
            <IconButton
              label={copied ? t("secondFactor.copied") : t("secondFactor.copySecret")}
              icon={copied ? <Check /> : <Copy />}
              onClick={() => void copySecret()}
            />
          </div>
          <TextField
            label={t("secondFactor.firstCode")}
            inputMode="numeric"
            autoComplete="one-time-code"
            value={code}
            onChange={(e) => setCode(e.target.value)}
          />
          {enable.error && <Notice kind="error">{enable.error.message}</Notice>}
        </form>
      )}
      {codes && (
        <section className={styles.codes} aria-labelledby="recovery-codes-heading">
          <h2 id="recovery-codes-heading" className={styles.subheading}>
            {t("secondFactor.codesTitle")}
          </h2>
          <p className="text-secondary">{t("secondFactor.codesIntro")}</p>
          <ul className={styles.codeList}>
            {codes.map((item) => (
              <li key={item}>
                <code className="numeric">{item}</code>
              </li>
            ))}
          </ul>
        </section>
      )}
      {failure && <Notice kind="error">{failure.message}</Notice>}
    </div>
  );
}
