/** Soft check for unlabeled directed edges in flowchart/graph Mermaid source (D-063). */

const RELATION_DIAGRAM =
  /^\s*(?:flowchart|graph)(?:\s+\w+)?\b/im;

/** Edges that look directed/undirected without a `|label|` segment. */
const BARE_EDGE =
  /(?:-->|---|==>|-\.-|-.->)(?!\s*\|)/;

export function mermaidNeedsEdgeLabels(source: string): boolean {
  const trimmed = source.trim();
  if (!RELATION_DIAGRAM.test(trimmed)) return false;
  // Ignore init / comment-only lines when scanning edges.
  const body = trimmed
    .split("\n")
    .filter((line) => {
      const t = line.trim();
      return t && !t.startsWith("%%") && !t.startsWith("classDef") && !t.startsWith("style ");
    })
    .join("\n");
  return BARE_EDGE.test(body);
}
