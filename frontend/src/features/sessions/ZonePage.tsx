import type { TFunction } from "i18next";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router";
import { Button } from "@/design-system/components/Button";
import { Notice } from "@/design-system/components/Notice";
import { TextField } from "@/design-system/components/TextField";
import { zoneName } from "@/features/lesions/lesionName";
import { PhotoCanvas, useCanvas } from "@/features/measure/PhotoCanvas";
import { imageUrl } from "@/lib/images";
import { useLesions, type LesionOut } from "@/lib/lesions";
import type { Point } from "@/lib/measurements";
import {
  useAddMark,
  useBlurZone,
  useBodySession,
  useDeleteMark,
  useProtocol,
  useUpdateMark,
  type MarkOut,
} from "@/lib/sessions";
import styles from "./sessions.module.css";

/** A rectangle of the photo to blur, as fractions of its width and height. */
interface Region {
  x: number;
  y: number;
  width: number;
  height: number;
}

const clamp01 = (value: number) => Math.min(1, Math.max(0, value));

/** One zone photo of a session: the marks on it, placed by the person or proposed, linked to the registry. */
export function ZonePage() {
  const { sessionId = "", zone: zoneId = "" } = useParams();
  const { t } = useTranslation();
  const session = useBodySession(sessionId);
  const protocol = useProtocol();
  const lesions = useLesions(session.data?.person_id ?? "");
  const add = useAddMark(sessionId, zoneId);
  const update = useUpdateMark();
  const remove = useDeleteMark();
  const blur = useBlurZone(sessionId, zoneId);
  const [draft, setDraft] = useState<Point | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [blurring, setBlurring] = useState(false);
  const [corner, setCorner] = useState<Point | null>(null);
  const [regions, setRegions] = useState<Region[]>([]);

  if (session.error) return <Notice kind="error">{session.error.message}</Notice>;
  const zone = session.data?.zones.find((item) => item.zone === zoneId);
  if (!session.data || !zone || !protocol.data) return <p className="text-secondary">…</p>;
  const capture = protocol.data.find((item) => item.id === zoneId);
  const covers = capture?.covers ?? [];
  const all = lesions.data ?? [];
  const here = [...all].sort(
    (a, b) => Number(covers.includes(b.location.zone)) - Number(covers.includes(a.location.zone)),
  );
  const title = (lesion: LesionOut) => lesion.label ?? zoneName(lesion.location.zone, t);
  const named = (id: string | null) => {
    const lesion = all.find((item) => item.id === id);
    return lesion ? title(lesion) : "";
  };
  const width = zone.upright_width ?? 1;
  const height = zone.upright_height ?? 1;
  const mark = zone.marks.find((item) => item.id === selected) ?? null;
  const canEdit = session.data.can_edit;
  const regionName = t(`sessions.zones.${zoneId}.name`);

  function place(point: Point) {
    if (!canEdit) return;
    const at = { x: clamp01(point.x / width), y: clamp01(point.y / height) };
    if (blurring) {
      if (!corner) {
        setCorner(at);
        return;
      }
      const region = {
        x: Math.min(corner.x, at.x),
        y: Math.min(corner.y, at.y),
        width: Math.abs(at.x - corner.x),
        height: Math.abs(at.y - corner.y),
      };
      setCorner(null);
      if (region.width >= 0.01 && region.height >= 0.01) setRegions((current) => [...current, region]);
      return;
    }
    setSelected(null);
    setDraft(at);
  }

  function startBlurring() {
    setBlurring(true);
    setDraft(null);
    setSelected(null);
    setCorner(null);
    setRegions([]);
  }

  function stopBlurring() {
    setBlurring(false);
    setCorner(null);
    setRegions([]);
  }

  const hint = blurring
    ? t("sessions.blurHint")
    : canEdit
      ? t("sessions.markHint")
      : t("sessions.markHintView");

  return (
    <div className={styles.page}>
      <p>
        <Link to={`/sessions/${sessionId}`}>{t("sessions.backToSession")}</Link>
      </p>
      <h1>{regionName}</h1>
      <p className="text-secondary">{hint}</p>
      {zone.analysing && (
        <p className="text-secondary" role="status">
          {t("sessions.analysing")}
        </p>
      )}
      {zone.image_id ? (
        <PhotoCanvas
          src={imageUrl(zone.image_id, "full")}
          width={width}
          height={height}
          label={t("sessions.canvas", { zone: regionName })}
          onTap={place}
        >
          {regions.map((region, index) => (
            <rect
              key={index}
              x={region.x * width}
              y={region.y * height}
              width={region.width * width}
              height={region.height * height}
              className={styles.blurRegion}
            />
          ))}
          {zone.marks.map((item, index) => (
            <Dot
              key={item.id}
              mark={item}
              index={index + 1}
              x={item.x * width}
              y={item.y * height}
              selected={item.id === selected}
            />
          ))}
          {draft && <Dot index={0} x={draft.x * width} y={draft.y * height} selected />}
          {corner && <Dot index={0} x={corner.x * width} y={corner.y * height} selected />}
        </PhotoCanvas>
      ) : (
        <Notice kind="info">{t("sessions.noPhoto")}</Notice>
      )}

      {canEdit && zone.image_id && !blurring && !draft && (
        <div>
          <Button variant="quiet" onClick={startBlurring}>
            {t("sessions.blur")}
          </Button>
        </div>
      )}

      {blurring && (
        <section className={styles.panel} aria-labelledby="blur-heading">
          <h2 id="blur-heading">{t("sessions.blurTitle")}</h2>
          <p className="text-secondary">{t("sessions.blurNote")}</p>
          <div className={styles.row}>
            <Button
              onClick={() => blur.mutate({ regions }, { onSuccess: stopBlurring })}
              disabled={regions.length === 0 || blur.isPending}
            >
              {t("sessions.blurApply", { count: regions.length })}
            </Button>
            <Button
              variant="secondary"
              onClick={() => setRegions((current) => current.slice(0, -1))}
              disabled={regions.length === 0}
            >
              {t("sessions.blurUndo")}
            </Button>
            <Button variant="quiet" onClick={stopBlurring}>
              {t("common.cancel")}
            </Button>
          </div>
          {blur.error && <Notice kind="error">{blur.error.message}</Notice>}
        </section>
      )}

      {draft && canEdit && !blurring && (
        <NewMarkForm
          covers={covers}
          lesions={here}
          title={title}
          pending={add.isPending}
          error={add.error?.message}
          onCancel={() => setDraft(null)}
          onSave={(link) => add.mutate({ ...draft, ...link }, { onSuccess: () => setDraft(null) })}
        />
      )}

      {zone.marks.length > 0 && (
        <section className={styles.section} aria-labelledby="marks-heading">
          <h2 id="marks-heading">{t("sessions.marksTitle")}</h2>
          <ol className={styles.marks}>
            {zone.marks.map((item, index) => (
              <li key={item.id}>
                <button
                  type="button"
                  className={[styles.markButton, item.id === selected ? styles.markSelected : ""].join(" ")}
                  onClick={() => {
                    setSelected(item.id);
                    setDraft(null);
                  }}
                >
                  <img src={item.crop_url} alt="" />
                  <span>
                    {index + 1}. {describe(item, named, t)}
                  </span>
                </button>
              </li>
            ))}
          </ol>
        </section>
      )}

      {mark && canEdit && (
        <MarkPanel
          mark={mark}
          covers={covers}
          lesions={here}
          title={title}
          named={named}
          busy={update.isPending || remove.isPending}
          onUpdate={(body) => update.mutate({ id: mark.id, body })}
          onRemove={() => remove.mutate(mark.id, { onSuccess: () => setSelected(null) })}
        />
      )}
      {(update.error ?? remove.error) && (
        <Notice kind="error">{(update.error ?? remove.error)?.message}</Notice>
      )}
    </div>
  );
}

function describe(mark: MarkOut, named: (id: string | null) => string, t: TFunction) {
  if (mark.source === "candidate" && mark.state === "pending") {
    if (mark.match === "matched") return t("sessions.proposedMatched", { name: named(mark.lesion_id) });
    if (mark.match === "uncertain") return t("sessions.proposedUncertain", { name: named(mark.lesion_id) });
    return t("sessions.proposedNew");
  }
  return mark.lesion_id ? named(mark.lesion_id) : t("sessions.unlinked");
}

function Dot({
  mark,
  index,
  x,
  y,
  selected,
}: {
  mark?: MarkOut;
  index: number;
  x: number;
  y: number;
  selected: boolean;
}) {
  const { unit } = useCanvas();
  const pending = mark?.state === "pending";
  return (
    <g aria-hidden="true">
      <circle
        cx={x}
        cy={y}
        r={(selected ? 16 : 12) * unit}
        className={pending ? styles.dotPending : styles.dot}
        strokeWidth={3 * unit}
      />
      {index > 0 && (
        <text x={x} y={y + 4 * unit} fontSize={11 * unit} textAnchor="middle" className={styles.dotLabel}>
          {index}
        </text>
      )}
    </g>
  );
}

type MarkLink = { lesion_id: string } | { new_mark: { zone_code: string; label: string | null } };

function NewMarkForm({
  covers,
  lesions,
  title,
  pending,
  error,
  onCancel,
  onSave,
}: {
  covers: string[];
  lesions: LesionOut[];
  title: (lesion: LesionOut) => string;
  pending: boolean;
  error?: string;
  onCancel: () => void;
  onSave: (link: MarkLink) => void;
}) {
  const { t } = useTranslation();
  return (
    <section className={styles.panel} aria-labelledby="new-mark-heading">
      <h2 id="new-mark-heading">{t("sessions.newMarkTitle")}</h2>
      <LinkChooser covers={covers} lesions={lesions} title={title} pending={pending} onLink={onSave} />
      {error && <Notice kind="error">{error}</Notice>}
      <div>
        <Button variant="quiet" onClick={onCancel}>
          {t("common.cancel")}
        </Button>
      </div>
    </section>
  );
}

function LinkChooser({
  covers,
  lesions,
  title,
  pending,
  onLink,
}: {
  covers: string[];
  lesions: LesionOut[];
  title: (lesion: LesionOut) => string;
  pending: boolean;
  onLink: (link: MarkLink) => void;
}) {
  const { t } = useTranslation();
  const [chosen, setKnown] = useState("");
  // The marks may arrive after the chooser opens: until one is chosen, the first is.
  const known = chosen || lesions[0]?.id || "";
  const [zoneChosen, setZone] = useState("");
  const zone = zoneChosen || covers[0] || "";
  const [label, setLabel] = useState("");
  return (
    <div className={styles.chooser}>
      {lesions.length > 0 && (
        <div className={styles.row}>
          <label className={styles.field}>
            <span>{t("sessions.knownMark")}</span>
            <select value={known} onChange={(e) => setKnown(e.target.value)}>
              {lesions.map((lesion) => (
                <option key={lesion.id} value={lesion.id}>
                  {title(lesion)}
                </option>
              ))}
            </select>
          </label>
          <Button onClick={() => onLink({ lesion_id: known })} disabled={pending || !known}>
            {t("sessions.linkKnown")}
          </Button>
        </div>
      )}
      <div className={styles.row}>
        <label className={styles.field}>
          <span>{t("sessions.newMarkZone")}</span>
          <select value={zone} onChange={(e) => setZone(e.target.value)}>
            {covers.map((code) => (
              <option key={code} value={code}>
                {zoneName(code, t)}
              </option>
            ))}
          </select>
        </label>
        <TextField
          label={t("sessions.newMarkName")}
          value={label}
          onChange={(e) => setLabel(e.target.value)}
          maxLength={120}
        />
        <Button
          variant="secondary"
          onClick={() => onLink({ new_mark: { zone_code: zone, label: label.trim() || null } })}
          disabled={pending || !zone}
        >
          {t("sessions.recordNew")}
        </Button>
      </div>
    </div>
  );
}

function MarkPanel({
  mark,
  covers,
  lesions,
  title,
  named,
  busy,
  onUpdate,
  onRemove,
}: {
  mark: MarkOut;
  covers: string[];
  lesions: LesionOut[];
  title: (lesion: LesionOut) => string;
  named: (id: string | null) => string;
  busy: boolean;
  onUpdate: (body: {
    state?: "confirmed" | "rejected";
    lesion_id?: string;
    new_mark?: { zone_code: string; label: string | null };
  }) => void;
  onRemove: () => void;
}) {
  const { t } = useTranslation();
  const proposal = mark.source === "candidate" && mark.state === "pending";
  return (
    <section className={styles.panel} aria-labelledby="mark-heading">
      <h2 id="mark-heading">
        {proposal ? t("sessions.proposalTitle") : t("sessions.markTitle")}{" "}
        {proposal && <span className={styles.experimental}>{t("proposals.experimental")}</span>}
      </h2>
      <img className={styles.crop} src={mark.crop_url} alt={t("sessions.cropAlt")} />
      {proposal && mark.lesion_id && (
        <div className={styles.row}>
          <p>
            {mark.match === "uncertain"
              ? t("sessions.proposedUncertain", { name: named(mark.lesion_id) })
              : t("sessions.proposedMatched", { name: named(mark.lesion_id) })}
          </p>
          <Button onClick={() => onUpdate({ state: "confirmed" })} disabled={busy}>
            {t("sessions.confirmMatch")}
          </Button>
        </div>
      )}
      {!proposal && mark.lesion_id && (
        <p>
          <Link to={`/lesions/${mark.lesion_id}`}>{named(mark.lesion_id)}</Link>
        </p>
      )}
      <LinkChooser
        covers={covers}
        lesions={lesions}
        title={title}
        pending={busy}
        onLink={(link) => onUpdate(link)}
      />
      <div className={styles.row}>
        {proposal ? (
          <Button variant="quiet" onClick={() => onUpdate({ state: "rejected" })} disabled={busy}>
            {t("sessions.rejectProposal")}
          </Button>
        ) : (
          <Button variant="quiet" onClick={onRemove} disabled={busy}>
            {t("sessions.removeMark")}
          </Button>
        )}
      </div>
    </section>
  );
}
