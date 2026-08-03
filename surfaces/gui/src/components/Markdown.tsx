import { Children, isValidElement, type ReactElement, type ReactNode } from "react";
import ReactMarkdown, { defaultUrlTransform } from "react-markdown";
import remarkGfm from "remark-gfm";
import { Icon } from "./Icon";
import { useI18n } from "../i18n";
import { MermaidBlock } from "./MermaidBlock";

// §34 (UX-016): the agent ends a deliverable turn with plain markdown —
// [Title](artifact:relative/path) — and the renderer turns it into a chip that opens the
// artifact viewer in place. Plumbing is a window event (the viewer lives in RightRail;
// this component renders deep inside the transcript): RightRail resolves the path against
// the session's artifact list, App un-hides the rail.
export const OPEN_ARTIFACT_EVENT = "ocw-open-artifact";

// react-markdown percent-encodes non-ASCII characters in hrefs. Decode so the
// path matches the real workspace-relative filename used by readArtifact.
export function artifactPathFromHref(href: string): string {
  const raw = href.startsWith("artifact:") ? href.slice("artifact:".length) : href;
  try {
    return decodeURIComponent(raw);
  } catch {
    return raw;
  }
}

function ArtifactChip({ path, title }: { path: string; title: string }) {
  const { t } = useI18n();
  const file = path.split("/").pop() || path;
  return (
    <button
      className="art-chip"
      data-testid="artifact-chip"
      title={path}
      onClick={() =>
        window.dispatchEvent(new CustomEvent(OPEN_ARTIFACT_EVENT, { detail: { path } }))
      }
    >
      <span className="art-chip-ico">
        <Icon name="file" size={14} />
      </span>
      <span className="art-chip-meta">
        <b>{title || file}</b>
        {title && title !== file && <span>{file}</span>}
      </span>
      <span className="art-chip-open">{t("Open")} ›</span>
    </button>
  );
}

function mermaidSourceFromPreChildren(children: ReactNode): string | null {
  const arr = Children.toArray(children);
  if (arr.length !== 1 || !isValidElement(arr[0])) return null;
  const el = arr[0] as ReactElement<{ className?: string; children?: ReactNode }>;
  const cls = el.props.className || "";
  if (!cls.includes("language-mermaid")) return null;
  return String(el.props.children ?? "");
}

// Assistant messages rendered as GitHub-flavored markdown (headings, lists, tables, code,
// links). Links open externally — never navigate the app shell — except artifact: links,
// which open the session's artifact viewer. Fenced ```mermaid blocks become MermaidBlock
// unless renderMermaid is false (live streaming).
export function Markdown({ text, renderMermaid = true }: { text: string; renderMermaid?: boolean }) {
  return (
    <div className="md">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        // artifact: is ours — keep it through the sanitizer (everything else gets the default
        // http/https/mailto policy).
        urlTransform={(url) => (url.startsWith("artifact:") ? url : defaultUrlTransform(url))}
        components={{
          a: ({ node: _n, href, children, ...props }) => {
            if (href?.startsWith("artifact:")) {
              const title = Array.isArray(children) ? children.join("") : String(children ?? "");
              return <ArtifactChip path={artifactPathFromHref(href)} title={title} />;
            }
            return (
              <a href={href} {...props} target="_blank" rel="noreferrer">
                {children}
              </a>
            );
          },
          pre: ({ children }) => {
            if (renderMermaid) {
              const src = mermaidSourceFromPreChildren(children);
              if (src !== null) return <MermaidBlock source={src} />;
            }
            return <pre>{children}</pre>;
          },
        }}
      >
        {text}
      </ReactMarkdown>
    </div>
  );
}
