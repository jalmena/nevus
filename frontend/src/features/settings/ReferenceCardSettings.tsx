import { Box, Download } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Notice } from "@/design-system/components/Notice";
import { RowList } from "@/design-system/components/Row";
import { TextField } from "@/design-system/components/TextField";
import { useSession, useUpdateMe } from "@/lib/auth/session";
import { SettingsHeader } from "./SettingsHeader";
import styles from "./settings.module.css";

/** Download the printable card, and record the measured length of its 50 mm verification line. */
export function ReferenceCardSettings({ admin }: { admin: boolean }) {
  const { t, i18n } = useTranslation();
  const user = useSession().data?.user;
  const update = useUpdateMe();
  const [value, setValue] = useState(user?.card_line_mm ? String(user.card_line_mm) : "");
  const lang = i18n.resolvedLanguage ?? "en"; // the sheet and the print note come in the interface's language
  if (!user) return null;

  function save() {
    const parsed = value.trim() === "" ? null : Number(value.replace(",", "."));
    if (parsed !== (user?.card_line_mm ?? null) && (parsed === null || Number.isFinite(parsed)))
      update.mutate({ card_line_mm: parsed });
  }

  return (
    <div className={styles.page}>
      <SettingsHeader
        help={{
          title: t("card.title"),
          content: (
            <>
              <p>{t("card.hint")}</p>
              <p>{t("card.intro")}</p>
            </>
          ),
        }}
        admin={admin}
        title={t("card.title")}
        meta={[user.card_line_mm ? t("card.verified", { mm: user.card_line_mm }) : t("card.unverified")]}
      ></SettingsHeader>
      <RowList>
        <li className={styles.linkRow}>
          <a href={`/api/reference-card?page=a4&lang=${lang}`} download>
            <Download aria-hidden="true" />
            {t("card.downloadA4")}
          </a>
        </li>
        <li className={styles.linkRow}>
          <a href={`/api/reference-card?page=letter&lang=${lang}`} download>
            <Download aria-hidden="true" />
            {t("card.downloadLetter")}
          </a>
        </li>
        <li className={styles.linkRow}>
          <a href={`/api/reference-card/3d?lang=${lang}`} download>
            <Box aria-hidden="true" />
            {t("card.download3d")}
          </a>
        </li>
      </RowList>
      <form
        className={styles.form}
        onSubmit={(event) => {
          event.preventDefault();
          save();
        }}
      >
        <TextField
          label={t("card.lineLabel")}
          hint={t("card.lineHint")}
          inputMode="decimal"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onBlur={save}
        />
      </form>
      {update.isSuccess && (
        <p className="text-secondary" role="status">
          {t("common.saved")}
        </p>
      )}
      {update.error && <Notice kind="error">{update.error.message}</Notice>}
    </div>
  );
}
