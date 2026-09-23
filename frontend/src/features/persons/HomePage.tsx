import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";
import { Button } from "@/design-system/components/Button";
import { Card } from "@/design-system/components/Card";
import { EmptyState } from "@/design-system/components/EmptyState";
import { Notice } from "@/design-system/components/Notice";
import { TextField } from "@/design-system/components/TextField";
import { useCreatePerson, usePersons } from "@/lib/persons";
import styles from "./persons.module.css";

export function HomePage() {
  const { t } = useTranslation();
  const persons = usePersons();
  const create = useCreatePerson();
  const [name, setName] = useState("");
  const [adding, setAdding] = useState(false);

  function submit(event: FormEvent) {
    event.preventDefault();
    create.mutate({ display_name: name }, { onSuccess: () => (setName(""), setAdding(false)) });
  }

  const form = (
    <form className={styles.addForm} onSubmit={submit}>
      <TextField label={t("persons.name")} value={name} onChange={(e) => setName(e.target.value)} required />
      <div className={styles.actions}>
        <Button type="submit" disabled={create.isPending || !name.trim()}>
          {t("persons.create")}
        </Button>
        <Button type="button" variant="quiet" onClick={() => setAdding(false)}>
          {t("common.cancel")}
        </Button>
      </div>
      {create.error && <Notice kind="error">{create.error.message}</Notice>}
    </form>
  );

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h1>{t("persons.title")}</h1>
        {!adding && persons.data && persons.data.length > 0 && (
          <Button variant="secondary" onClick={() => setAdding(true)}>
            {t("persons.add")}
          </Button>
        )}
      </header>
      {persons.error && <Notice kind="error">{persons.error.message}</Notice>}
      {persons.data && persons.data.length === 0 && !adding && (
        <EmptyState
          title={t("persons.emptyTitle")}
          text={t("persons.emptyText")}
          action={<Button onClick={() => setAdding(true)}>{t("persons.add")}</Button>}
        />
      )}
      {adding && form}
      <ul className={styles.list}>
        {persons.data?.map((person) => (
          <li key={person.id}>
            <Card>
              <Link to={`/persons/${person.id}`} className={styles.personLink}>
                <span className={styles.personName}>{person.display_name}</span>
                <span className="text-secondary">{t(`persons.role.${person.my_role}`)}</span>
              </Link>
            </Card>
          </li>
        ))}
      </ul>
    </div>
  );
}
