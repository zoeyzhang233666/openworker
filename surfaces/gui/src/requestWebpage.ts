/** Optional «做网页版» entry: inject align-then-generate intent into the chat turn. */

export const REQUEST_WEBPAGE_EVENT = "ocw-request-webpage";

export type RequestWebpageDetail = {
  title: string;
  path: string;
};

/** User message sent when the MD chip's «做网页版» button is clicked. */
export function webpageAlignIntentMessage(title: string, path: string): string {
  const name = (title || "").trim() || "报告";
  const rel = (path || "").trim() || "report.md";
  return `请基于《${name}》文档版（${rel}），先与我对齐网页细节再生成网页版`;
}
