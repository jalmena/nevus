import { Settings, UserPlus } from "lucide-react";
import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { useMediaQuery, type ChromeAction } from "@/app/chrome";
import { Button } from "@/design-system/components/Button";
import { EmptyState } from "@/design-system/components/EmptyState";
import { Notice } from "@/design-system/components/Notice";
import { PageHeader } from "@/design-system/components/PageHeader";
import { Initial, Row, RowList } from "@/design-system/components/Row";
import { Section } from "@/design-system/components/Section";
import { Sheet } from "@/design-system/components/Sheet";
import { TextField } from "@/design-system/components/TextField";
import { UpcomingAppointments } from "@/features/appointments/PrepareAppointment";
import { DueRows } from "@/features/reminders/DueList";
import { useUpcomingAppointments } from "@/lib/appointments";
import { useCreatePerson, usePersons } from "@/lib/persons";
import { useDue } from "@/lib/reminders";
import styles from "./persons.module.css";

/** The home: what is due across persons, the appointments ahead, and the persons. */
export function HomePage() {
  const { t } = useTranslation();
  const desktop = useMediaQuery("(min-width: 900px)");
  const persons = usePersons();
  const upcoming = useUpcomingAppointments();
  const due = useDue();
  const create = useCreatePerson();
  const [name, setName] = useState("");
  const [adding, setAdding] = useState(false);
  const empty = persons.data !== undefined && persons.data.length === 0;
  const dueCount = due.data?.length ?? 0;
  const appointmentCount = upcoming.data?.length ?? 0;

  function submit(event: FormEvent) {
    event.preventDefault();
    create.mutate(
      { display_name: name },
      {
        onSuccess: () => {
          setName("");
          setAdding(false);
        },
      },
    );
  }

  const actions: ChromeAction[] = [];
  if (!empty)
    actions.push({ key: "add", label: t("persons.add"), icon: <UserPlus />, onClick: () => setAdding(true) });
  if (!desktop)
    actions.push({
      key: "settings",
      label: t("settings.title"),
      icon: <Settings />,
      to: "/settings",
      showLabel: false,
    });
  const sectioned = dueCount > 0 || appointmentCount > 0;

  return (
    <div className={styles.page}>
      <PageHeader
        title={t("persons.title")}
        meta={[
          due.data
            ? dueCount > 0
              ? t("reminders.dueCount", { count: dueCount })
              : t("reminders.nothingDue")
            : null,
          appointmentCount > 0 ? t("appointments.count", { count: appointmentCount }) : null,
        ]}
        actions={actions}
        primary={empty ? { label: t("persons.add"), onClick: () => setAdding(true) } : undefined}
      />
      {dueCount > 0 && (
        <Section title={t("reminders.title")}>
          <DueRows />
        </Section>
      )}
      <UpcomingAppointments appointments={upcoming.data} />
      {persons.error && <Notice kind="error">{persons.error.message}</Notice>}
      {empty && <EmptyState>{t("persons.emptyText")}</EmptyState>}
      {persons.data && persons.data.length > 0 && (
        <PersonRows sectioned={sectioned}>
          {persons.data.map((person) => (
            <Row
              key={person.id}
              to={`/persons/${person.id}`}
              leading={<Initial name={person.display_name} />}
              title={person.display_name}
              trailing={t(`persons.role.${person.my_role}`)}
              chevron
            />
          ))}
        </PersonRows>
      )}
      <Sheet open={adding} title={t("persons.add")} onClose={() => setAdding(false)}>
        <form className={styles.addForm} onSubmit={submit}>
          <TextField
            label={t("persons.name")}
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
          />
          {create.error && <Notice kind="error">{create.error.message}</Notice>}
          <div className={styles.actions}>
            <Button type="button" variant="quiet" onClick={() => setAdding(false)}>
              {t("common.cancel")}
            </Button>
            <Button type="submit" disabled={create.isPending}>
              {t("persons.create")}
            </Button>
          </div>
        </form>
      </Sheet>
    </div>
  );
}

function PersonRows({ sectioned, children }: { sectioned: boolean; children: React.ReactNode }) {
  const { t } = useTranslation();
  if (!sectioned) return <RowList label={t("persons.title")}>{children}</RowList>;
  return (
    <Section title={t("persons.title")}>
      <RowList>{children}</RowList>
    </Section>
  );
}
