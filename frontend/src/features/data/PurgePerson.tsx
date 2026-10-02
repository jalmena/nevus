import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router";
import { Button } from "@/design-system/components/Button";
import { Notice } from "@/design-system/components/Notice";
import { TextField } from "@/design-system/components/TextField";
import { usePurgePerson } from "@/lib/data";
import styles from "./data.module.css";

/** Deleting a profile for good asks for the name, and then for the password. */
export function PurgePerson({ personId, name }: { personId: string; name: string }) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const purge = usePurgePerson();
  const [typed, setTyped] = useState("");
  return (
    <div className={styles.danger}>
      <strong>{t("data.purgeTitle")}</strong>
      <p className="text-secondary">{t("data.purgeIntro", { name })}</p>
      <TextField
        label={t("data.typeName", { name })}
        value={typed}
        onChange={(e) => setTyped(e.target.value)}
      />
      <Button
        variant="danger"
        disabled={typed.trim() !== name || purge.isPending}
        onClick={() => purge.mutate(personId, { onSuccess: () => void navigate("/", { replace: true }) })}
      >
        {t("data.purgeAction")}
      </Button>
      {purge.error && <Notice kind="error">{purge.error.message}</Notice>}
    </div>
  );
}
