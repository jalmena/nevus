import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "@/design-system/components/Button";
import { Notice } from "@/design-system/components/Notice";
import { TextField } from "@/design-system/components/TextField";
import { useSecondFactor } from "@/lib/auth/session";
import styles from "./auth.module.css";

/** After the password: the code from the authenticator app, or one of the recovery codes. */
export function SecondFactorForm({ onBack }: { onBack: () => void }) {
  const { t } = useTranslation();
  const finish = useSecondFactor();
  const [recovery, setRecovery] = useState(false);
  const [value, setValue] = useState("");

  function submit(event: FormEvent) {
    event.preventDefault();
    finish.mutate(recovery ? { recovery_code: value.trim() } : { code: value.replace(/\s+/g, "") });
  }

  return (
    <form className={styles.form} onSubmit={submit} noValidate>
      <h1>{t("auth.secondFactorTitle")}</h1>
      <p className="text-secondary">{recovery ? t("auth.recoveryIntro") : t("auth.codeIntro")}</p>
      <TextField
        label={recovery ? t("auth.recoveryCode") : t("auth.code")}
        name="code"
        inputMode={recovery ? "text" : "numeric"}
        autoComplete={recovery ? "off" : "one-time-code"}
        autoCapitalize="none"
        required
        value={value}
        onChange={(e) => setValue(e.target.value)}
      />
      {finish.error && <Notice kind="error">{finish.error.message}</Notice>}
      <Button type="submit" disabled={finish.isPending || !value.trim()}>
        {finish.isPending ? t("common.working") : t("auth.continue")}
      </Button>
      <div className={styles.links}>
        <Button
          type="button"
          variant="quiet"
          onClick={() => {
            setRecovery(!recovery);
            setValue("");
          }}
        >
          {recovery ? t("auth.useCode") : t("auth.useRecovery")}
        </Button>
        <Button type="button" variant="quiet" onClick={onBack}>
          {t("auth.backToPassword")}
        </Button>
      </div>
    </form>
  );
}
