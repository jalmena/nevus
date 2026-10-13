import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router";
import { Button } from "@/design-system/components/Button";
import { EmptyState } from "@/design-system/components/EmptyState";
import { Help } from "@/design-system/components/Help";
import { Notice } from "@/design-system/components/Notice";
import { PageHeader } from "@/design-system/components/PageHeader";
import { Row, RowList } from "@/design-system/components/Row";
import { Section } from "@/design-system/components/Section";
import { Sheet } from "@/design-system/components/Sheet";
import { TextField } from "@/design-system/components/TextField";
import { personRail } from "@/features/persons/personRail";
import { daysUntil, useAppointments, useCreateAppointment } from "@/lib/appointments";
import type { PersonOut } from "@/lib/persons";
import styles from "./appointments.module.css";

/** The person's appointments as a page: the ones planned, and planning a new one in a sheet. */
export function PrepareAppointment({ person, canEdit }: { person: PersonOut; canEdit: boolean }) {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const appointments = useAppointments(person.id);
  const create = useCreateAppointment(person.id);
  const [open, setOpen] = useState(false);
  const [date, setDate] = useState("");
  const [notes, setNotes] = useState("");
  const dateFormat = new Intl.DateTimeFormat(i18n.resolvedLanguage, { dateStyle: "long" });

  function submit(event: FormEvent) {
    event.preventDefault();
    create.mutate(
      { date, notes: notes.trim() || null },
      { onSuccess: (made) => void navigate(`/appointments/${made.id}`) },
    );
  }

  const list = appointments.data ?? [];
  return (
    <div className={styles.page}>
      <PageHeader
        back={{ to: `/persons/${person.id}`, label: person.display_name }}
        title={t("appointments.sectionTitle")}
        rail={personRail(t, person.id, person.display_name)}
        primary={canEdit ? { label: t("appointments.new"), onClick: () => setOpen(true) } : undefined}
      >
        <p className={["text-secondary", styles.intro].join(" ")}>
          {t("appointments.hint")}
          <Help title={t("appointments.sectionTitle")} as="text">
            <p>{t("appointments.intro")}</p>
          </Help>
        </p>
      </PageHeader>
      {appointments.error && <Notice kind="error">{appointments.error.message}</Notice>}
      {appointments.data && list.length === 0 && <EmptyState>{t("appointments.empty")}</EmptyState>}
      {list.length > 0 && (
        <RowList>
          {list.map((item) => {
            const left = item.checklist.filter((entry) => entry.state !== "photographed").length;
            const days = daysUntil(item.date);
            return (
              <Row
                key={item.id}
                to={`/appointments/${item.id}`}
                title={t("appointments.title", {
                  date: dateFormat.format(new Date(`${item.date}T12:00:00`)),
                })}
                meta={
                  days < 0
                    ? t("appointments.past")
                    : left === 0
                      ? t("appointments.ready")
                      : t("appointments.left", { count: left })
                }
              />
            );
          })}
        </RowList>
      )}
      <Sheet open={open} title={t("appointments.new")} onClose={() => setOpen(false)}>
        <form className={styles.editForm} onSubmit={submit}>
          <TextField
            label={t("appointments.date")}
            type="date"
            value={date}
            onChange={(e) => setDate(e.target.value)}
            required
          />
          <TextField
            label={t("appointments.notes")}
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            maxLength={2000}
          />
          {create.error && <Notice kind="error">{create.error.message}</Notice>}
          <div className={styles.actions}>
            <Button type="button" variant="quiet" onClick={() => setOpen(false)}>
              {t("common.cancel")}
            </Button>
            <Button type="submit" disabled={create.isPending}>
              {t("appointments.prepare")}
            </Button>
          </div>
        </form>
      </Sheet>
    </div>
  );
}

/** On the home page: the appointments ahead, for every person the user may see. */
export function UpcomingAppointments({
  appointments,
}: {
  appointments: ReturnType<typeof useAppointments>["data"];
}) {
  const { t, i18n } = useTranslation();
  const dateFormat = new Intl.DateTimeFormat(i18n.resolvedLanguage, { dateStyle: "long" });
  if (!appointments || appointments.length === 0) return null;
  return (
    <Section title={t("appointments.upcoming")}>
      <RowList>
        {appointments.map((item) => {
          const left = item.checklist.filter((entry) => entry.state !== "photographed").length;
          return (
            <Row
              key={item.id}
              to={`/appointments/${item.id}`}
              title={t("appointments.title", { date: dateFormat.format(new Date(`${item.date}T12:00:00`)) })}
              meta={`${item.person_name} · ${left === 0 ? t("appointments.ready") : t("appointments.left", { count: left })}`}
            />
          );
        })}
      </RowList>
    </Section>
  );
}
