import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "@/design-system/components/Button";
import { Notice } from "@/design-system/components/Notice";
import { Sheet } from "@/design-system/components/Sheet";
import { TextField } from "@/design-system/components/TextField";
import { useRequestExport } from "@/lib/data";
import styles from "./data.module.css";

const MIN = 10;

/** One encrypted file with everything: the passphrase is needed to open it and is never stored. */
export function ExportSheet({
  personId,
  open,
  onClose,
  title,
}: {
  personId: string | null;
  open: boolean;
  onClose: () => void;
  title: string;
}) {
  const { t } = useTranslation();
  const request = useRequestExport();
  const [first, setFirst] = useState("");
  const [second, setSecond] = useState("");
  const [problem, setProblem] = useState<string | null>(null);

  function submit(event: FormEvent) {
    event.preventDefault();
    if (first.length < MIN) return setProblem(t("auth.passwordTooShort", { count: MIN }));
    if (first !== second) return setProblem(t("auth.passwordsDiffer"));
    setProblem(null);
    request.mutate(
      { person_id: personId, passphrase: first },
      {
        onSuccess: () => {
          setFirst("");
          setSecond("");
          onClose();
        },
      },
    );
  }

  return (
    <>
      <Sheet open={open} title={title} onClose={onClose}>
        <form className={styles.block} onSubmit={submit}>
          <p className="text-secondary">{t("data.exportIntro")}</p>
          <TextField
            label={t("data.passphrase")}
            type="password"
            autoComplete="new-password"
            value={first}
            onChange={(e) => setFirst(e.target.value)}
          />
          <TextField
            label={t("data.passphraseAgain")}
            type="password"
            autoComplete="new-password"
            value={second}
            onChange={(e) => setSecond(e.target.value)}
          />
          {(problem ?? request.error?.message) && (
            <Notice kind="error">{problem ?? request.error?.message}</Notice>
          )}
          <div className={styles.actions}>
            <Button type="button" variant="quiet" onClick={onClose}>
              {t("common.cancel")}
            </Button>
            <Button type="submit" disabled={request.isPending}>
              {t("data.startExport")}
            </Button>
          </div>
        </form>
      </Sheet>
      {request.isSuccess && !open && <Notice kind="success">{t("data.exportStarted")}</Notice>}
    </>
  );
}
