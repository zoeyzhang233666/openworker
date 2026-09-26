import { useEffect, useState } from "react";
import { getModelProfile, setModelProfile, type ModelProfile } from "../api";
import { useI18n } from "../i18n";

export function ModelProfileCard({ models }: { models: string[] }) {
  const { locale } = useI18n();
  const t = (text: string) => locale === "en-US" ? labels[text] || text : text;
  const [model, setModel] = useState("");
  const [profile, setProfile] = useState<ModelProfile | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [revision, setRevision] = useState(0);
  useEffect(() => {
    const refresh = () => setRevision((v) => v + 1);
    window.addEventListener("chemclaw-compaction-settings", refresh);
    return () => window.removeEventListener("chemclaw-compaction-settings", refresh);
  }, []);
  const selected = model || models[0] || "";
  useEffect(() => {
    let active = true;
    setProfile(null);
    if (selected) getModelProfile(selected).then(p => { if (active) { setProfile(p); setError(""); } })
      .catch(e => { if (active) setError(String(e.message)); });
    return () => { active = false; };
  }, [selected, revision]);
  async function save(reset = false) {
    if (!profile) return;
    setBusy(true);
    try {
      setProfile(await setModelProfile(selected, reset ? {} : {
        context_window: profile.context_window, max_output_tokens: profile.max_output_tokens,
        reasoning_effort: profile.reasoning_effort,
        structured_tools_streaming: profile.structured_tools_streaming,
      }));
      setError("");
    } catch (e) { setError(e instanceof Error ? e.message : String(e)); }
    finally { setBusy(false); }
  }
  return <div className="mt-4 border-t border-line pt-3" data-testid="model-profile-card">
    <label>{t("模型能力与有效上下文")}
      <select aria-label={t("模型能力配置模型")} value={selected} onChange={e => setModel(e.target.value)} disabled={busy} className="ml-2 bg-paper">
        {models.map(m => <option key={m} value={m}>{m}</option>)}
      </select>
    </label>
    {profile && <>
      <p className="text-xs text-muted mt-2">{profile.provider} {profile.endpoint} · {t(profile.source === "estimated" ? "窗口为保守估计，请按服务商文档核实" : profile.source === "override" ? "使用用户核实配置" : "使用内置模型配置")}</p>
      <div className="flex flex-wrap gap-3 mt-2 text-sm">
        <label>{t("上下文窗口")} <input type="number" min={256} value={profile.context_window} onChange={e => setProfile({ ...profile, context_window: Number(e.target.value) })} className="w-28 bg-paper border border-line" /></label>
        <label>{t("最大输出")} <input type="number" min={256} value={profile.max_output_tokens} onChange={e => setProfile({ ...profile, max_output_tokens: Number(e.target.value) })} className="w-24 bg-paper border border-line" /></label>
        <label>{t("推理参数")} <select value={profile.reasoning_effort} onChange={e => setProfile({ ...profile, reasoning_effort: e.target.value })} className="bg-paper">
          <option value="">{t("不发送（默认）")}</option>{["none", "minimal", "low", "medium", "high", "xhigh"].map(v => <option key={v}>{v}</option>)}
        </select></label>
        <label>{t("结构化工具流式")} <select value={String(profile.structured_tools_streaming)} onChange={e => setProfile({ ...profile, structured_tools_streaming: e.target.value === "null" ? null : e.target.value === "true" })} className="bg-paper">
          <option value="null">{t("自动兼容")}</option><option value="true">{t("已验证支持")}</option><option value="false">{t("使用缓冲兼容")}</option>
        </select></label>
      </div>
      <p className="text-xs text-muted mt-2">{t("已保存配置的有效触发线")}：{profile.effective_trigger.toLocaleString()} tokens；{t("压缩目标")}：{profile.target_tokens.toLocaleString()} tokens。</p>
      <button disabled={busy} onClick={() => void save()} className="mt-2 mr-3 text-sm text-accent">{t("保存模型能力")}</button>
      <button disabled={busy} onClick={() => void save(true)} className="text-sm text-muted">{t("恢复自动配置")}</button>
    </>}
    {error && <p role="alert" className="text-sm text-red-600">{error}</p>}
  </div>;
}

const labels: Record<string, string> = {"模型能力与有效上下文": "Model capabilities and effective context", "模型能力配置模型": "Model to configure", "窗口为保守估计，请按服务商文档核实": "Estimated window; verify against provider documentation", "使用用户核实配置": "Using user-supplied configuration", "使用内置模型配置": "Using built-in model configuration", "上下文窗口": "Context window", "最大输出": "Maximum output", "推理参数": "Reasoning parameter", "不发送（默认）": "Omit (default)", "结构化工具流式": "Structured tool streaming", "自动兼容": "Automatic compatibility", "已验证支持": "Verified supported", "使用缓冲兼容": "Buffered compatibility", "已保存配置的有效触发线": "Effective trigger for saved settings", "压缩目标": "Compaction target", "保存模型能力": "Save model capabilities", "恢复自动配置": "Restore automatic settings"};
