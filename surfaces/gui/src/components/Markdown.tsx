import {
  Children,
  isValidElement,
  useMemo,
  type ReactElement,
  type ReactNode,
} from "react";
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

const REMARK_PLUGINS = [remarkGfm];

/** Suffixes that open in the session artifact viewer (aligned with server list_artifacts). */
const ARTIFACT_SUFFIXES = new Set([
  ".md",
  ".markdown",
  ".html",
  ".htm",
  ".txt",
  ".json",
  ".csv",
  ".tsv",
  ".py",
  ".js",
  ".ts",
  ".tsx",
  ".css",
  ".png",
  ".jpg",
  ".jpeg",
  ".webp",
  ".gif",
  ".svg",
  ".pdf",
  ".xlsx",
  ".xls",
  ".pptx",
  ".ppt",
  ".pptm",
  ".docx",
  ".doc",
  ".docm",
]);

function urlTransform(url: string): string {
  return url.startsWith("artifact:") ? url : defaultUrlTransform(url);
}

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

/** Workspace-relative deliverable links → ArtifactChip; http(s)/mailto stay external. */
export function isArtifactHref(href: string | undefined): boolean {
  if (!href) return false;
  if (href.startsWith("artifact:")) return true;
  if (/^(https?:|mailto:|tel:|#|\/\/)/i.test(href)) return false;
  const path = href.split(/[?#]/)[0] || "";
  const slash = path.lastIndexOf("/");
  const base = slash >= 0 ? path.slice(slash + 1) : path;
  const dot = base.lastIndexOf(".");
  if (dot < 0) return false;
  return ARTIFACT_SUFFIXES.has(base.slice(dot).toLowerCase());
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

function MarkdownLink({
  node: _node,
  href,
  children,
  ...props
}: {
  node?: unknown;
  href?: string;
  children?: ReactNode;
  [key: string]: unknown;
}) {
  if (isArtifactHref(href)) {
    const title = Array.isArray(children) ? children.join("") : String(children ?? "");
    return <ArtifactChip path={artifactPathFromHref(href!)} title={title} />;
  }
  return (
    <a href={href} {...props} target="_blank" rel="noreferrer">
      {children}
    </a>
  );
}

// Assistant messages rendered as GitHub-flavored markdown (headings, lists, tables, code,
// links). Links open externally — never navigate the app shell — except artifact: links,
// which open the session's artifact viewer. Fenced ```mermaid blocks become MermaidBlock
// unless renderMermaid is false (live streaming).
//
// remarkPlugins / urlTransform / components MUST stay referentially stable across parent
// re-renders. Inline object/array identities made react-markdown remount custom nodes,
// which cleared MermaidBlock state, collapsed scrollHeight, and jittered the transcript.
export function Markdown({ text, renderMermaid = true }: { text: string; renderMermaid?: boolean }) {
  const components = useMemo(
    () => ({
      a: MarkdownLink,
      pre: ({ children }: { children?: ReactNode }) => {
        if (renderMermaid) {
          const src = mermaidSourceFromPreChildren(children);
          if (src !== null) return <MermaidBlock source={src} />;
        }
        return <pre>{children}</pre>;
      },
    }),
    [renderMermaid],
  );

  return (
    <div className="md">
      <ReactMarkdown
        remarkPlugins={REMARK_PLUGINS}
        urlTransform={urlTransform}
        components={components}
      >
        {text}
      </ReactMarkdown>
    </div>
  );
}
