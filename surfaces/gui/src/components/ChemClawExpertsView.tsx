import { useI18n } from "../i18n";
import { ChemClawPageShell } from "./ChemClawPageShell";
import { PersonasTab } from "./PersonasTab";

export function ChemClawExpertsView({
  onOpenPersona,
}: {
  onOpenPersona?: (id: string) => void;
}) {
  const { t } = useI18n();
  return (
    <ChemClawPageShell>
      <div className="max-w-[860px] mx-auto px-6 py-6">
        <h1 className="text-[20px] font-semibold mb-1">{t("nav.experts")}</h1>
        <p className="text-[13px] text-muted mb-5 leading-relaxed">{t("experts.pageIntro")}</p>
        <PersonasTab onOpenPersona={onOpenPersona} />
      </div>
    </ChemClawPageShell>
  );
}
