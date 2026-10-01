import { useTranslation } from "react-i18next";
import { Link } from "react-router";
import { Button } from "@/design-system/components/Button";
import { Notice } from "@/design-system/components/Notice";
import { useSession } from "@/lib/auth/session";
import { imageUrl, type ImageOut } from "@/lib/images";
import { formatMm } from "@/lib/measurements";
import { confidenceWord, useDecideProposal, useVisitProposals, type ProposalOut } from "@/lib/proposals";
import styles from "./measure.module.css";

function upright(image: ImageOut): { width: number; height: number } {
  return image.orientation >= 5 && image.orientation <= 8
    ? { width: image.height, height: image.width }
    : { width: image.width, height: image.height };
}

/**
 * Experimental outline proposals for the visit's photos, for persons who turned the experimental
 * analysis on. Nothing enters the record until the person uses a proposal.
 */
export function Proposals({
  observationId,
  images,
  canEdit,
}: {
  observationId: string;
  images: ImageOut[];
  canEdit: boolean;
}) {
  const { t, i18n } = useTranslation();
  const session = useSession();
  const decide = useDecideProposal();
  const locale = i18n.resolvedLanguage ?? "en";
  const showUncertainty = session.data?.user.show_uncertainty ?? true;
  const photos = images.filter((image) => image.role === "close_up" || image.role === "with_reference");
  const results = useVisitProposals(
    photos.map((image) => image.id),
    false,
  );
  const items = photos.flatMap((image, index) =>
    (results[index]?.data ?? []).map((proposal) => ({ image, proposal })),
  );
  if (items.length === 0) return null;
  const pending = items.filter((item) => item.proposal.decision === "pending");
  const abstained = items.filter((item) => !item.proposal.found);

  return (
    <section className={styles.panel} aria-labelledby="proposals-heading">
      <h2 id="proposals-heading">
        {t("proposals.title")} <span className={styles.experimental}>{t("proposals.experimental")}</span>
      </h2>
      <p className="text-secondary">{t("proposals.intro")}</p>
      {pending.map(({ image, proposal }) => (
        <Pending
          key={proposal.id}
          image={image}
          proposal={proposal}
          observationId={observationId}
          canEdit={canEdit}
          busy={decide.isPending}
          onDecide={(decision) => decide.mutate({ id: proposal.id, decision })}
          size={
            proposal.size
              ? `${formatMm(proposal.size.longest_mm, proposal.size.sigma_longest_mm, locale, showUncertainty)} × ${formatMm(
                  proposal.size.perpendicular_mm,
                  proposal.size.sigma_perpendicular_mm,
                  locale,
                  showUncertainty,
                )}`
              : null
          }
        />
      ))}
      {abstained.map(({ proposal }) => (
        <Notice key={proposal.id} kind="info">
          {t("proposals.nothing", { reason: t(`proposals.reasons.${proposal.reason ?? "no_mark_found"}`) })}
        </Notice>
      ))}
      {items
        .filter(({ proposal }) => proposal.framing_flags.some((flag) => flag !== "no_mark_found"))
        .map(({ proposal }) => (
          <Notice key={`${proposal.id}-framing`} kind="info">
            {t("proposals.framingIntro")}{" "}
            {proposal.framing_flags
              .filter((flag) => flag !== "no_mark_found")
              .map((flag) => t(`proposals.framing.${flag}`))
              .join(" ")}
          </Notice>
        ))}
      {decide.error && <Notice kind="error">{decide.error.message}</Notice>}
    </section>
  );
}

function Pending({
  image,
  proposal,
  observationId,
  canEdit,
  busy,
  size,
  onDecide,
}: {
  image: ImageOut;
  proposal: ProposalOut;
  observationId: string;
  canEdit: boolean;
  busy: boolean;
  size: string | null;
  onDecide: (decision: "confirm" | "reject") => void;
}) {
  const { t } = useTranslation();
  const { width, height } = upright(image);
  return (
    <article className={styles.proposal}>
      <div className={styles.proposalPhoto}>
        <img src={imageUrl(image.id, "preview")} alt={t(`images.roles.${image.role}`)} />
        {proposal.outline && (
          <svg viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none" aria-hidden="true">
            <polygon
              className={styles.proposalHalo}
              points={proposal.outline.map((p) => p.join(",")).join(" ")}
            />
            <polygon
              className={styles.proposalLine}
              points={proposal.outline.map((p) => p.join(",")).join(" ")}
            />
          </svg>
        )}
      </div>
      <div className={styles.proposalText}>
        <p className="numeric">{size ?? t("proposals.noScale")}</p>
        <p className="text-secondary">
          {t("proposals.confidence", { level: t(`proposals.levels.${confidenceWord(proposal.confidence)}`) })}
        </p>
        {canEdit && (
          <div className={styles.proposalActions}>
            <Button onClick={() => onDecide("confirm")} disabled={busy || !proposal.size}>
              {t("proposals.use")}
            </Button>
            <Link to={`/observations/${observationId}/measure/${image.id}?proposal=${proposal.id}`}>
              {t("proposals.adjust")}
            </Link>
            <Button variant="quiet" onClick={() => onDecide("reject")} disabled={busy}>
              {t("proposals.reject")}
            </Button>
          </div>
        )}
      </div>
    </article>
  );
}
