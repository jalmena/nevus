import { Download, Trash2 } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Help } from "@/design-system/components/Help";
import { Notice } from "@/design-system/components/Notice";
import { PageHeader } from "@/design-system/components/PageHeader";
import { Row, RowList } from "@/design-system/components/Row";
import { Select } from "@/design-system/components/Select";
import { Switch } from "@/design-system/components/Switch";
import { ExportSheet } from "@/features/data/ExportForm";
import { PurgeSheet } from "@/features/data/PurgePerson";
import { formatBytes, useUsage } from "@/lib/data";
import { bodyMap, type BodyPart } from "@/features/bodymap/zones";
import { useConfirm } from "@/lib/confirm/ConfirmProvider";
import { useLesions } from "@/lib/lesions";
import { useUpdatePerson, type PersonOut } from "@/lib/persons";
import { personRail } from "./personRail";
import styles from "./persons.module.css";

/** The person's profile: the anatomy the body map draws, the experimental analysis switch, the space used, export, deletion. */
export function ProfilePage({ person }: { person: PersonOut }) {
  const { t, i18n } = useTranslation();
  const update = useUpdatePerson(person.id);
  const lesions = useLesions(person.id);
  const confirm = useConfirm();

  /** Changes the anatomy, asking first when a part with marks on it leaves the map. */
  async function changeAnatomy(
    body: { chest?: PersonOut["chest"]; genitals?: PersonOut["genitals"] },
    removed?: BodyPart,
  ) {
    const zones = new Set(bodyMap.zones.filter((zone) => zone.part === removed).map((zone) => zone.code));
    const count = removed
      ? (lesions.data ?? []).filter((lesion) => zones.has(lesion.location.zone)).length
      : 0;
    if (count > 0) {
      const yes = await confirm({
        title: t("persons.anatomyRemoveTitle"),
        text: t("persons.anatomyRemoveText", { count }),
        action: t("persons.anatomyRemoveAction"),
        danger: true,
      });
      if (!yes) return;
    }
    update.mutate(body);
  }
  const usage = useUsage(person.id);
  const [exporting, setExporting] = useState(false);
  const [purging, setPurging] = useState(false);
  const locale = i18n.resolvedLanguage ?? "en";
  return (
    <div className={styles.page}>
      <PageHeader
        back={{ to: `/persons/${person.id}`, label: person.display_name }}
        title={t("persons.profile")}
        meta={[
          usage.data
            ? t("data.usage", { count: usage.data.images, size: formatBytes(usage.data.bytes, locale) })
            : null,
        ]}
        rail={personRail(t, person.id, person.display_name)}
        menu={[
          { label: t("data.purgeTitle"), icon: <Trash2 />, danger: true, onSelect: () => setPurging(true) },
        ]}
      />
      <div className={styles.switchRow}>
        <Select
          label={t("persons.chest")}
          value={person.chest ?? ""}
          disabled={person.my_role === "viewer" || update.isPending}
          onChange={(event) => {
            const chest = (event.target.value || null) as PersonOut["chest"];
            void changeAnatomy(
              { chest },
              person.chest === "breasts" && chest !== "breasts" ? "breasts" : undefined,
            );
          }}
          options={[
            { value: "", label: t("persons.chestOptions.unset") },
            { value: "breasts", label: t("persons.chestOptions.breasts") },
          ]}
        />
        <Select
          label={t("persons.genitals")}
          value={person.genitals ?? ""}
          disabled={person.my_role === "viewer" || update.isPending}
          onChange={(event) => {
            const genitals = (event.target.value || null) as PersonOut["genitals"];
            void changeAnatomy(
              { genitals },
              person.genitals === "penis" && genitals !== "penis" ? "penis" : undefined,
            );
          }}
          options={[
            { value: "", label: t("persons.genitalsOptions.unset") },
            { value: "vulva", label: t("persons.genitalsOptions.vulva") },
            { value: "penis", label: t("persons.genitalsOptions.penis") },
          ]}
        />
        <p className={["text-secondary", styles.fieldHint].join(" ")}>{t("persons.anatomyHint")}</p>
        <Switch
          label={t("persons.experimental")}
          hint={
            <>
              {t("persons.experimentalShort")}{" "}
              <Help title={t("persons.experimental")} as="text">
                <p>{t("persons.experimentalHint")}</p>
              </Help>
            </>
          }
          checked={person.experimental_analysis}
          onChange={(checked) => update.mutate({ experimental_analysis: checked })}
        />
        {update.error && <Notice kind="error">{update.error.message}</Notice>}
        {usage.data?.over_quota && <Notice kind="attention">{t("data.overQuota")}</Notice>}
      </div>
      <RowList>
        <Row
          onClick={() => setExporting(true)}
          leading={<Download />}
          title={t("data.exportPerson")}
          meta={t("data.hint")}
          chevron
        />
      </RowList>
      <ExportSheet
        personId={person.id}
        open={exporting}
        onClose={() => setExporting(false)}
        title={t("data.exportPerson")}
      />
      <PurgeSheet
        personId={person.id}
        name={person.display_name}
        open={purging}
        onClose={() => setPurging(false)}
      />
    </div>
  );
}
