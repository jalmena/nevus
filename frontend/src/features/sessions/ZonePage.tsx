import type { TFunction } from "i18next";
import { Camera, EyeOff, Undo2 } from "lucide-react";
import { useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router";
import { Button } from "@/design-system/components/Button";
import { Help } from "@/design-system/components/Help";
import { Notice } from "@/design-system/components/Notice";
import { PageHeader } from "@/design-system/components/PageHeader";
import { Row, RowList, Thumb } from "@/design-system/components/Row";
import { Select } from "@/design-system/components/Select";
import { Sheet } from "@/design-system/components/Sheet";
import { StatusChip } from "@/design-system/components/StatusChip";
import { TextField } from "@/design-system/components/TextField";
import { zoneName } from "@/features/lesions/lesionName";
import { PhotoCanvas, useCanvas } from "@/features/measure/PhotoCanvas";
import { useConfirm } from "@/lib/confirm/ConfirmProvider";
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
  useZonePhoto,
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
  const { t, i18n } = useTranslation();
  const confirm = useConfirm();
  const session = useBodySession(sessionId);
  const protocol = useProtocol();
  const lesions = useLesions(session.data?.person_id ?? "");
  const add = useAddMark(sessionId, zoneId);
  const update = useUpdateMark();
  const remove = useDeleteMark();
  const blur = useBlurZone(sessionId, zoneId);
  const retake = useZonePhoto(sessionId);
  const camera = useRef<HTMLInputElement>(null);
  const [draft, setDraft] = useState<Point | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [blurring, setBlurring] = useState(false);
  const [corner, setCorner] = useState<Point | null>(null);
  const [regions, setRegions] = useState<Region[]>([]);
  const dateFormat = new Intl.DateTimeFormat(i18n.resolvedLanguage, { dateStyle: "long" });

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

  function applyBlur() {
    void confirm({
      title: t("sessions.blurQuestion"),
      text: t("sessions.blurNoteMore"),
      action: t("sessions.blurApply", { count: regions.length }),
      danger: true,
    }).then((yes) => yes && blur.mutate({ regions }, { onSuccess: stopBlurring }));
  }

  const hint = blurring
    ? t("sessions.blurHint")
    : canEdit
      ? t("sessions.markHint")
      : t("sessions.markHintView");

  return (
    <div className={[styles.page, "page-wide"].join(" ")}>
      <PageHeader
        back={{
          to: `/sessions/${sessionId}`,
          label: t("sessions.titleFor", { date: dateFormat.format(new Date(session.data.started_at)) }),
        }}
        title={regionName}
        meta={[zone.analysing ? t("sessions.analysing") : null]}
        actions={
          blurring
            ? [
                {
                  key: "undo",
                  label: t("sessions.blurUndo"),
                  icon: <Undo2 />,
                  disabled: regions.length === 0,
                  onClick: () => setRegions((current) => current.slice(0, -1)),
                },
              ]
            : []
        }
        primary={
          blurring
            ? {
                label: t("sessions.blurApply", { count: regions.length }),
                disabled: regions.length === 0,
                pending: blur.isPending,
                onClick: applyBlur,
              }
            : undefined
        }
        secondary={blurring ? { label: t("common.cancel"), onClick: stopBlurring } : undefined}
        menu={
          canEdit && zone.image_id && !blurring
            ? [
                { label: t("sessions.blur"), icon: <EyeOff />, onSelect: startBlurring },
                { label: t("sessions.retake"), icon: <Camera />, onSelect: () => camera.current?.click() },
              ]
            : []
        }
      >
        <p className={["text-secondary", styles.hint].join(" ")}>
          {hint}
          {blurring && (
            <>
              {" "}
              {t("sessions.blurNote")}
              <Help title={t("sessions.blurTitle")} as="text">
                <p>{t("sessions.blurNoteMore")}</p>
              </Help>
            </>
          )}
        </p>
      </PageHeader>
      {canEdit && (
        <input
          ref={camera}
          type="file"
          accept="image/*"
          capture="environment"
          className={styles.hiddenInput}
          aria-label={t("sessions.retake")}
          onChange={(event) => {
            const file = event.target.files?.[0];
            event.target.value = "";
            if (file) retake.mutate({ zone: zoneId, file });
          }}
        />
      )}
      {(blur.error ?? retake.error ?? update.error ?? remove.error) && (
        <Notice kind="error">{(blur.error ?? retake.error ?? update.error ?? remove.error)?.message}</Notice>
      )}

      <div className={styles.layout}>
        <div className={styles.photoPane}>
          {zone.image_id ? (
            <div className={styles.canvasFrame}>
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
            </div>
          ) : (
            <Notice kind="info">{t("sessions.noPhoto")}</Notice>
          )}
        </div>
        <div className={styles.dataPane}>
          {zone.marks.length > 0 && (
            <RowList label={t("sessions.marksTitle")}>
              {zone.marks.map((item, index) => (
                <Row
                  key={item.id}
                  onClick={() => {
                    setSelected(item.id);
                    setDraft(null);
                  }}
                  selected={item.id === selected}
                  leading={<Thumb src={item.crop_url} />}
                  title={`${index + 1}. ${describe(item, named, t)}`}
                  meta={
                    item.source === "candidate" && item.state === "pending"
                      ? t("proposals.experimental")
                      : item.lesion_id
                        ? named(item.lesion_id)
                        : undefined
                  }
                />
              ))}
            </RowList>
          )}
        </div>
      </div>

      <Sheet
        open={draft !== null && canEdit && !blurring}
        title={t("sessions.newMarkTitle")}
        onClose={() => setDraft(null)}
      >
        {draft && (
          <LinkChooser
            covers={covers}
            lesions={here}
            title={title}
            pending={add.isPending}
            error={add.error?.message}
            onCancel={() => setDraft(null)}
            onLink={(link) => add.mutate({ ...draft, ...link }, { onSuccess: () => setDraft(null) })}
          />
        )}
      </Sheet>
      <Sheet
        open={mark !== null && canEdit}
        title={
          mark?.source === "candidate" && mark.state === "pending"
            ? t("sessions.proposalTitle")
            : t("sessions.markTitle")
        }
        onClose={() => setSelected(null)}
      >
        {mark && (
          <MarkPanel
            mark={mark}
            covers={covers}
            lesions={here}
            title={title}
            named={named}
            busy={update.isPending || remove.isPending}
            onUpdate={(body) => update.mutate({ id: mark.id, body }, { onSuccess: () => setSelected(null) })}
            onRemove={() => remove.mutate(mark.id, { onSuccess: () => setSelected(null) })}
            onClose={() => setSelected(null)}
          />
        )}
      </Sheet>
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

/** A radio list of the marks the region covers, and "a new mark"; one primary for the choice made. */
function LinkChooser({
  covers,
  lesions,
  title,
  pending,
  error,
  initial,
  onCancel,
  onLink,
  extra,
}: {
  covers: string[];
  lesions: LesionOut[];
  title: (lesion: LesionOut) => string;
  pending: boolean;
  error?: string;
  /** The mark linked today, when there is one. */
  initial?: string | null;
  onCancel: () => void;
  onLink: (link: MarkLink) => void;
  extra?: React.ReactNode;
}) {
  const { t } = useTranslation();
  const [chosen, setChosen] = useState<string>(initial ?? (lesions.length > 0 ? "" : "new"));
  const choice = chosen || lesions[0]?.id || "new";
  const [zoneChosen, setZone] = useState("");
  const zone = zoneChosen || covers[0] || "";
  const [label, setLabel] = useState("");
  const isNew = choice === "new";
  return (
    <div className={styles.chooser}>
      <div className={styles.choices} role="radiogroup" aria-label={t("sessions.knownMark")}>
        {lesions.map((lesion) => (
          <div key={lesion.id} className={styles.choiceItem}>
            <button
              type="button"
              role="radio"
              aria-checked={choice === lesion.id}
              className={[styles.choice, choice === lesion.id ? styles.choiceSelected : ""].join(" ")}
              onClick={() => setChosen(lesion.id)}
            >
              <Thumb
                src={lesion.latest_image_id ? imageUrl(lesion.latest_image_id, "thumb") : null}
                size={40}
              />
              <span>{title(lesion)}</span>
            </button>
          </div>
        ))}
        <div className={styles.choiceItem}>
          <button
            type="button"
            role="radio"
            aria-checked={isNew}
            className={[styles.choice, isNew ? styles.choiceSelected : ""].join(" ")}
            onClick={() => setChosen("new")}
          >
            <span>{t("sessions.newMarkChoice")}</span>
          </button>
        </div>
      </div>
      {isNew && (
        <>
          <Select
            label={t("sessions.newMarkZone")}
            value={zone}
            onChange={(e) => setZone(e.target.value)}
            options={covers.map((code) => ({ value: code, label: zoneName(code, t) }))}
          />
          <TextField
            label={t("sessions.newMarkName")}
            value={label}
            onChange={(e) => setLabel(e.target.value)}
            maxLength={120}
          />
        </>
      )}
      {error && <Notice kind="error">{error}</Notice>}
      <div className={styles.sheetActions}>
        {extra}
        <Button type="button" variant="quiet" onClick={onCancel}>
          {t("common.cancel")}
        </Button>
        <Button
          onClick={() =>
            isNew
              ? onLink({ new_mark: { zone_code: zone, label: label.trim() || null } })
              : onLink({ lesion_id: choice })
          }
          disabled={pending || (isNew && !zone)}
        >
          {isNew ? t("sessions.recordNew") : t("sessions.linkKnown")}
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
  onClose,
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
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const proposal = mark.source === "candidate" && mark.state === "pending";
  return (
    <div className={styles.chooser}>
      <div className={styles.cropRow}>
        <img className={styles.crop} src={mark.crop_url} alt={t("sessions.cropAlt")} />
        {proposal && <StatusChip kind="experimental">{t("proposals.experimental")}</StatusChip>}
      </div>
      {proposal && mark.lesion_id && (
        <p>
          {mark.match === "uncertain"
            ? t("sessions.proposedUncertain", { name: named(mark.lesion_id) })
            : t("sessions.proposedMatched", { name: named(mark.lesion_id) })}
        </p>
      )}
      {proposal && mark.lesion_id ? (
        <div className={styles.sheetActions}>
          <Button variant="secondary" onClick={() => onUpdate({ state: "rejected" })} disabled={busy}>
            {t("sessions.rejectProposal")}
          </Button>
          <Button onClick={() => onUpdate({ state: "confirmed" })} disabled={busy}>
            {t("sessions.confirmMatch")}
          </Button>
        </div>
      ) : (
        <>
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
            initial={mark.lesion_id}
            onCancel={onClose}
            onLink={(link) => onUpdate(link)}
            extra={
              proposal ? (
                <Button variant="quiet" onClick={() => onUpdate({ state: "rejected" })} disabled={busy}>
                  {t("sessions.rejectProposal")}
                </Button>
              ) : (
                <Button variant="quiet" onClick={onRemove} disabled={busy}>
                  {t("sessions.removeMark")}
                </Button>
              )
            }
          />
        </>
      )}
    </div>
  );
}
