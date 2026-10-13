import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router";
import { Button } from "@/design-system/components/Button";
import { Notice } from "@/design-system/components/Notice";
import { Sheet } from "@/design-system/components/Sheet";
import { TextField } from "@/design-system/components/TextField";
import { usePurgePerson } from "@/lib/data";
import styles from "./data.module.css";

/** Deleting a profile for good asks for the name, and then for the password. */
export function PurgeSheet({
  personId,
  name,
  open,
  onClose,
}: {
  personId: string;
  name: string;
  open: boolean;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const purge = usePurgePerson();
  const [typed, setTyped] = useState("");
  return (
    <Sheet open={open} title={t("data.purgeTitle")} onClose={onClose}>
      <div className={styles.block}>
        <p className="text-secondary">{t("data.purgeIntro", { name })}</p>
        <TextField
          label={t("data.typeName", { name })}
          value={typed}
          onChange={(e) => setTyped(e.target.value)}
        />
        {purge.error && <Notice kind="error">{purge.error.message}</Notice>}
        <div className={styles.actions}>
          <Button type="button" variant="quiet" onClick={onClose}>
            {t("common.cancel")}
          </Button>
          <Button
            variant="dangerFilled"
            disabled={typed.trim() !== name || purge.isPending}
            onClick={() => purge.mutate(personId, { onSuccess: () => void navigate("/", { replace: true }) })}
          >
            {t("data.purgeAction")}
          </Button>
        </div>
      </div>
    </Sheet>
  );
}
