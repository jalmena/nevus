import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router";
import { Button } from "@/design-system/components/Button";
import { Notice } from "@/design-system/components/Notice";
import { TextField } from "@/design-system/components/TextField";
import { daysUntil, useAppointments, useCreateAppointment } from "@/lib/appointments";
import styles from "./appointments.module.css";

/** On a person's page: plan an appointment, and the ones already planned. */
export function PrepareAppointment({
  personId,
  canEdit,
  embedded = false,
}: {
  personId: string;
  canEdit: boolean;
  /** Under a disclosure that carries the heading. */
  embedded?: boolean;
}) {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const appointments = useAppointments(personId);
  const create = useCreateAppointment(personId);
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
  if (!canEdit && list.length === 0) return null;
  const Wrapper = embedded ? "div" : "section";
  return (
    <Wrapper className={styles.section} aria-labelledby={embedded ? undefined : "appointments-heading"}>
      {!embedded && <h2 id="appointments-heading">{t("appointments.sectionTitle")}</h2>}
      <p className="text-secondary">{t("appointments.intro")}</p>
      {canEdit && (
        <form className={styles.form} onSubmit={submit}>
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
          <Button type="submit" disabled={create.isPending || !date}>
            {t("appointments.prepare")}
          </Button>
        </form>
      )}
      {create.error && <Notice kind="error">{create.error.message}</Notice>}
      {list.length > 0 && (
        <ul className={styles.list}>
          {list.map((item) => {
            const left = item.checklist.filter((entry) => entry.state !== "photographed").length;
            const days = daysUntil(item.date);
            return (
              <li key={item.id} className={styles.item}>
                <span className={styles.what}>
                  <Link to={`/appointments/${item.id}`}>
                    {t("appointments.title", { date: dateFormat.format(new Date(`${item.date}T12:00:00`)) })}
                  </Link>
                  <span className="text-secondary">
                    {days < 0
                      ? t("appointments.past")
                      : left === 0
                        ? t("appointments.ready")
                        : t("appointments.left", { count: left })}
                  </span>
                </span>
              </li>
            );
          })}
        </ul>
      )}
    </Wrapper>
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
    <section className={styles.section} aria-labelledby="upcoming-heading">
      <h2 id="upcoming-heading">{t("appointments.upcoming")}</h2>
      <ul className={styles.list}>
        {appointments.map((item) => {
          const left = item.checklist.filter((entry) => entry.state !== "photographed").length;
          return (
            <li key={item.id}>
              <Link to={`/appointments/${item.id}`} className={styles.card}>
                <span className={styles.cardTitle}>
                  {t("appointments.title", { date: dateFormat.format(new Date(`${item.date}T12:00:00`)) })}
                </span>
                <span className="text-secondary">
                  {item.person_name} ·{" "}
                  {left === 0 ? t("appointments.ready") : t("appointments.left", { count: left })}
                </span>
              </Link>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
