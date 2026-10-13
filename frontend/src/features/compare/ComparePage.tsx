import { ChevronDown } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useParams, useSearchParams } from "react-router";
import { Button } from "@/design-system/components/Button";
import { Notice } from "@/design-system/components/Notice";
import { PageHeader } from "@/design-system/components/PageHeader";
import { Row, RowList, Thumb } from "@/design-system/components/Row";
import { Sheet } from "@/design-system/components/Sheet";
import { lesionTitle } from "@/features/lesions/lesionName";
import { shortDate } from "@/lib/dates";
import { imageUrl, type ImageOut } from "@/lib/images";
import { useLesion, useObservations, type ObservationOut } from "@/lib/lesions";
import { usePerson } from "@/lib/persons";
import { ComparisonViewer, MODES, type Mode } from "./ComparisonViewer";
import styles from "./compare.module.css";

interface Choice {
  image: ImageOut;
  visit: ObservationOut;
}

/** Photos with the reference card first (they align exactly), then close-ups. */
const ROLE_ORDER = ["with_reference", "close_up", "overview"];

function preferred(visit: ObservationOut | undefined): string {
  if (!visit) return "";
  const ranked = [...visit.images].sort(
    (x, y) => rank(x.role) - rank(y.role) || x.created_at.localeCompare(y.created_at),
  );
  return ranked[0]?.id ?? "";
}

function rank(role: string): number {
  const index = ROLE_ORDER.indexOf(role);
  return index === -1 ? ROLE_ORDER.length : index;
}

export function upright(image: ImageOut): { width: number; height: number } {
  return image.orientation >= 5 && image.orientation <= 8
    ? { width: image.height, height: image.width }
    : { width: image.width, height: image.height };
}

/** Two photos of one mark: side by side with a shared zoom, or aligned on top of each other. */
export function ComparePage() {
  const { lesionId = "" } = useParams();
  const [search, setSearch] = useSearchParams();
  const { t, i18n } = useTranslation();
  const lesion = useLesion(lesionId);
  const person = usePerson(lesion.data?.person_id ?? "");
  const observations = useObservations(lesionId);
  const [picking, setPicking] = useState<"a" | "b" | null>(null);
  const dateFormat = new Intl.DateTimeFormat(i18n.resolvedLanguage, { dateStyle: "medium" });

  const visits = [...(observations.data ?? [])]
    .filter((visit) => visit.images.length > 0)
    .sort((x, y) => x.captured_at.localeCompare(y.captured_at));
  const choices: Choice[] = visits.flatMap((visit) => visit.images.map((image) => ({ image, visit })));
  const a = search.get("a") ?? preferred(visits[0]);
  const b = search.get("b") ?? preferred(visits.at(-1));
  const requested = search.get("mode") as Mode | null;
  const first = choices.find((choice) => choice.image.id === a);
  const second = choices.find((choice) => choice.image.id === b);

  function choose(next: { a?: string; b?: string; mode?: Mode }) {
    const params = new URLSearchParams(search);
    for (const [key, value] of Object.entries(next)) if (value) params.set(key, value);
    setSearch(params, { replace: true });
  }

  if (lesion.error) return <Notice kind="error">{lesion.error.message}</Notice>;
  if (!lesion.data || !observations.data) return <p className="text-secondary">…</p>;
  const markTitle = lesionTitle(lesion.data, t);
  const header = (
    <PageHeader
      back={{ to: `/lesions/${lesionId}`, label: markTitle }}
      title={t("compare.title")}
      meta={[markTitle, person.data?.display_name ?? null]}
      help={{ title: t("common.help"), content: <p>{t("compare.zoomHint")}</p> }}
    />
  );
  if (visits.length < 2 && choices.length < 2) {
    return (
      <div className={styles.page}>
        {header}
        <Notice kind="info">{t("compare.needTwo")}</Notice>
      </div>
    );
  }

  const label = (choice: Choice) =>
    `${shortDate(i18n.resolvedLanguage, choice.visit.captured_at)} · ${t(`images.roles.${choice.image.role}`)}`;
  const picker = (side: "a" | "b", current: Choice | undefined) => (
    <Button variant="secondary" className={styles.picker} onClick={() => setPicking(side)}>
      <span className={styles.pickerSide}>{side === "a" ? t("compare.earlier") : t("compare.later")}</span>
      <span className={styles.pickerValue}>{current ? label(current) : "—"}</span>
      <ChevronDown aria-hidden="true" />
    </Button>
  );

  return (
    <div className={styles.page}>
      {header}
      <div className={styles.pickers}>
        {picker("a", first)}
        {picker("b", second)}
      </div>
      {first && second && (
        <ComparisonViewer
          a={{ id: first.image.id, ...upright(first.image), label: label(first) }}
          b={{ id: second.image.id, ...upright(second.image), label: label(second) }}
          mode={requested && MODES.includes(requested) ? requested : null}
          onMode={(mode) => choose({ mode })}
        />
      )}
      <Sheet
        open={picking !== null}
        title={picking === "a" ? t("compare.earlier") : t("compare.later")}
        onClose={() => setPicking(null)}
      >
        <RowList label={t("compare.pickPhoto")}>
          {choices.map((choice) => {
            const chosen = (picking === "a" ? a : b) === choice.image.id;
            return (
              <Row
                key={choice.image.id}
                onClick={() => {
                  choose(picking === "a" ? { a: choice.image.id } : { b: choice.image.id });
                  setPicking(null);
                }}
                selected={chosen}
                leading={<Thumb src={imageUrl(choice.image.id, "thumb")} />}
                title={dateFormat.format(new Date(choice.visit.captured_at))}
                meta={t(`images.roles.${choice.image.role}`)}
              />
            );
          })}
        </RowList>
      </Sheet>
    </div>
  );
}
