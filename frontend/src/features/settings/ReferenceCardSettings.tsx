import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "@/design-system/components/Button";
import { Card } from "@/design-system/components/Card";
import { Notice } from "@/design-system/components/Notice";
import { TextField } from "@/design-system/components/TextField";
import { useSession, useUpdateMe } from "@/lib/auth/session";
import styles from "./settings.module.css";

/** Download the printable card, and record the measured length of its 50 mm verification line. */
export function ReferenceCardSettings() {
  const { t, i18n } = useTranslation();
  const session = useSession();
  const update = useUpdateMe();
  const user = session.data?.user;
  const [value, setValue] = useState(user?.card_line_mm ? String(user.card_line_mm) : "");
  const lang = i18n.resolvedLanguage === "es" ? "es" : "en";
  if (!user) return null;

  function save(event: FormEvent) {
    event.preventDefault();
    const parsed = Number(value.replace(",", "."));
    update.mutate({ card_line_mm: value.trim() === "" ? null : parsed });
  }

  return (
    <Card className={styles.group}>
      <h2 className={styles.subheading}>{t("card.title")}</h2>
      <p className="text-secondary">{t("card.intro")}</p>
      <div className={styles.links}>
        <a href={`/api/reference-card?page=a4&lang=${lang}`} download>
          {t("card.downloadA4")}
        </a>
        <a href={`/api/reference-card?page=letter&lang=${lang}`} download>
          {t("card.downloadLetter")}
        </a>
      </div>
      <form className={styles.inline} onSubmit={save}>
        <TextField
          label={t("card.lineLabel")}
          hint={t("card.lineHint")}
          inputMode="decimal"
          value={value}
          onChange={(e) => setValue(e.target.value)}
        />
        <Button type="submit" variant="secondary" disabled={update.isPending}>
          {t("common.save")}
        </Button>
      </form>
      {user.card_line_mm ? (
        <Notice kind="success">{t("card.verified", { mm: user.card_line_mm })}</Notice>
      ) : (
        <p className="text-secondary">{t("card.unverified")}</p>
      )}
      {update.error && <Notice kind="error">{update.error.message}</Notice>}
    </Card>
  );
}
