import { useI18n } from "../i18n";
import { ChemClawPageShell } from "./ChemClawPageShell";
import { SkillsTab } from "./SkillsTab";

export function ChemClawSkillsView({
  onCreateSkill,
}: {
  onCreateSkill?: (description: string) => void;
}) {
  const { t } = useI18n();
  return (
    <ChemClawPageShell>
      <div className="max-w-[860px] mx-auto px-6 py-6">
        <h1 className="text-[20px] font-semibold mb-1">{t("skills.pageTitle")}</h1>
        <p className="text-[13px] text-muted mb-5 leading-relaxed">{t("skills.pageIntro")}</p>
        <SkillsTab onCreateSkill={onCreateSkill} hideHeader />
      </div>
    </ChemClawPageShell>
  );
}
