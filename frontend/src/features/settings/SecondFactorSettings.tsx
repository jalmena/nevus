import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "@/design-system/components/Button";
import { Card } from "@/design-system/components/Card";
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
export function SecondFactorSettings() {
  const { t } = useTranslation();
  const local = useInstance().data?.auth_mode !== "proxy";
  const status = useTotpStatus(local);
  const setup = useTotpSetup();
  const enable = useTotpEnable();
  const disable = useTotpDisable();
  const renew = useNewRecoveryCodes();
  const [code, setCode] = useState("");
  const [codes, setCodes] = useState<string[] | null>(null);
  if (!local || !status.data) return null;
  const failure = setup.error ?? disable.error ?? renew.error;

  function turnOn(event: FormEvent) {
    event.preventDefault();
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

  return (
    <Card className={styles.group}>
      <h2 className={styles.subheading}>{t("secondFactor.title")}</h2>
      <p className="text-secondary">{t("secondFactor.intro")}</p>
      {status.data.enabled ? (
        <>
          <p>{t("secondFactor.on", { count: status.data.recovery_codes_left })}</p>
          <div className={styles.userActions}>
            <Button
              variant="secondary"
              disabled={renew.isPending}
              onClick={() => renew.mutate(undefined, { onSuccess: (fresh) => setCodes(fresh) })}
            >
              {t("secondFactor.newCodes")}
            </Button>
            <Button variant="quiet" disabled={disable.isPending} onClick={() => disable.mutate()}>
              {t("secondFactor.turnOff")}
            </Button>
          </div>
        </>
      ) : setup.data ? (
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
          <p className="text-secondary">
            {t("secondFactor.orType")}{" "}
            <code className={["numeric", styles.secret].join(" ")}>{grouped(setup.data.secret)}</code>
          </p>
          <TextField
            label={t("secondFactor.firstCode")}
            inputMode="numeric"
            autoComplete="one-time-code"
            value={code}
            onChange={(e) => setCode(e.target.value)}
          />
          {enable.error && <Notice kind="error">{enable.error.message}</Notice>}
          <div className={styles.userActions}>
            <Button type="submit" disabled={enable.isPending || code.replace(/\s/g, "").length < 6}>
              {t("secondFactor.turnOn")}
            </Button>
            <Button type="button" variant="quiet" onClick={() => setup.reset()}>
              {t("common.cancel")}
            </Button>
          </div>
        </form>
      ) : (
        !codes && (
          <div>
            <Button variant="secondary" disabled={setup.isPending} onClick={() => setup.mutate()}>
              {t("secondFactor.setUp")}
            </Button>
          </div>
        )
      )}
      {codes && (
        <section className={styles.codes} aria-labelledby="recovery-codes-heading">
          <h3 id="recovery-codes-heading">{t("secondFactor.codesTitle")}</h3>
          <p className="text-secondary">{t("secondFactor.codesIntro")}</p>
          <ul className={styles.codeList}>
            {codes.map((item) => (
              <li key={item}>
                <code className="numeric">{item}</code>
              </li>
            ))}
          </ul>
          <div className={styles.userActions}>
            <Button variant="secondary" onClick={() => download(codes)}>
              {t("secondFactor.download")}
            </Button>
            <Button variant="quiet" onClick={() => setCodes(null)}>
              {t("secondFactor.codesDone")}
            </Button>
          </div>
        </section>
      )}
      {failure && <Notice kind="error">{failure.message}</Notice>}
    </Card>
  );
}
