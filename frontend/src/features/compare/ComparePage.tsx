import { useTranslation } from "react-i18next";
import { Link, useParams, useSearchParams } from "react-router";
import { Notice } from "@/design-system/components/Notice";
import { lesionTitle } from "@/features/lesions/lesionName";
import { type ImageOut } from "@/lib/images";
import { useLesion, useObservations, type ObservationOut } from "@/lib/lesions";
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
  const observations = useObservations(lesionId);
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
  const back = (
    <p>
      <Link to={`/lesions/${lesionId}`}>{t("compare.back")}</Link>
    </p>
  );
  if (visits.length < 2 && choices.length < 2) {
    return (
      <div className={styles.page}>
        {back}
        <h1>{t("compare.title")}</h1>
        <Notice kind="info">{t("compare.needTwo")}</Notice>
      </div>
    );
  }

  const label = (choice: Choice) =>
    `${dateFormat.format(new Date(choice.visit.captured_at))} · ${t(`images.roles.${choice.image.role}`)}`;
  const picker = (side: "a" | "b", value: string) => (
    <label className={styles.picker}>
      <span className="text-secondary">{side === "a" ? t("compare.earlier") : t("compare.later")}</span>
      <select
        value={value}
        onChange={(event) => choose(side === "a" ? { a: event.target.value } : { b: event.target.value })}
      >
        {visits.map((visit) => (
          <optgroup key={visit.id} label={dateFormat.format(new Date(visit.captured_at))}>
            {visit.images.map((image) => (
              <option key={image.id} value={image.id}>
                {label({ image, visit })}
              </option>
            ))}
          </optgroup>
        ))}
      </select>
    </label>
  );

  return (
    <div className={styles.page}>
      {back}
      <h1>{t("compare.titleFor", { name: lesionTitle(lesion.data, t) })}</h1>
      <div className={styles.pickers}>
        {picker("a", a)}
        {picker("b", b)}
      </div>
      {first && second && (
        <ComparisonViewer
          a={{ id: first.image.id, ...upright(first.image), label: label(first) }}
          b={{ id: second.image.id, ...upright(second.image), label: label(second) }}
          mode={requested && MODES.includes(requested) ? requested : null}
          onMode={(mode) => choose({ mode })}
        />
      )}
    </div>
  );
}
