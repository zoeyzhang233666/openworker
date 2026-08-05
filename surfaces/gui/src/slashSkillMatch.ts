// Rank session skills for the Composer "/" popup. Chinese users usually remember
// what a skill *does* (description), not the English id (name) — so description
// hits outrank name hits. Empty query keeps the full enabled menu in original order.

export interface SlashSkillCandidate {
  name: string;
  description: string;
}

const MAX_RESULTS = 40;

const SCORE_DESC_SUBSTR = 100;
const SCORE_DESC_SUBSEQ = 60;
const SCORE_NAME_PREFIX = 50;
const SCORE_NAME_SUBSTR = 30;

function isCharSubsequence(query: string, haystack: string): boolean {
  if (!query) return true;
  let i = 0;
  for (const ch of haystack) {
    if (ch === query[i]) i += 1;
    if (i >= query.length) return true;
  }
  return false;
}

export function scoreSlashSkill(skill: SlashSkillCandidate, query: string): number {
  const q = query.trim().toLowerCase();
  if (!q) return 0;
  const name = skill.name.toLowerCase();
  const desc = (skill.description || "").toLowerCase();

  let best = 0;
  if (desc.includes(q)) best = Math.max(best, SCORE_DESC_SUBSTR);
  else if (isCharSubsequence(q, desc)) best = Math.max(best, SCORE_DESC_SUBSEQ);

  if (name.startsWith(q)) best = Math.max(best, SCORE_NAME_PREFIX);
  else if (name.includes(q)) best = Math.max(best, SCORE_NAME_SUBSTR);

  return best;
}

/** Filter + rank skills for the "/" force-run popup. Empty query → all, original order. */
export function rankSlashSkills<T extends SlashSkillCandidate>(skills: T[], query: string): T[] {
  const q = query.trim().toLowerCase();
  if (!q) return skills;

  const scored = skills
    .map((skill, index) => ({ skill, score: scoreSlashSkill(skill, q), index }))
    .filter((row) => row.score > 0);

  scored.sort((a, b) => {
    if (b.score !== a.score) return b.score - a.score;
    const len = a.skill.name.length - b.skill.name.length;
    if (len !== 0) return len;
    const byName = a.skill.name.localeCompare(b.skill.name, "zh");
    if (byName !== 0) return byName;
    return a.index - b.index;
  });

  return scored.slice(0, MAX_RESULTS).map((row) => row.skill);
}
