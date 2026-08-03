/** State for left-nav auto-collapse while an artifact preview is open (#3). */
export type ArtifactPreviewNavState = {
  /** Whether a full artifact preview is currently open. */
  previewOpen: boolean;
  /** Current left-nav collapsed flag. */
  navCollapsed: boolean;
  /**
   * Collapse state captured when preview first opened, or null if the user
   * manually toggled the nav during the preview (takes control) / no restore pending.
   */
  navBeforePreview: boolean | null;
};

export type ArtifactPreviewNavResult = {
  previewOpen: boolean;
  navCollapsed: boolean;
  navBeforePreview: boolean | null;
  /** Clear peek overlay when collapsing for a newly opened preview. */
  clearPeek: boolean;
};

/**
 * Apply artifact-preview open/close to left-nav collapse.
 * Only auto-collapses on the closed→open edge so effect re-entrancy cannot
 * snap the nav shut after the user manually expands it during a preview.
 */
export function applyArtifactPreviewNav(
  state: ArtifactPreviewNavState,
  open: boolean,
): ArtifactPreviewNavResult {
  if (open) {
    if (state.previewOpen) {
      return {
        previewOpen: true,
        navCollapsed: state.navCollapsed,
        navBeforePreview: state.navBeforePreview,
        clearPeek: false,
      };
    }
    const navBeforePreview =
      state.navBeforePreview === null ? state.navCollapsed : state.navBeforePreview;
    return {
      previewOpen: true,
      navCollapsed: true,
      navBeforePreview,
      clearPeek: true,
    };
  }

  if (state.navBeforePreview !== null) {
    return {
      previewOpen: false,
      navCollapsed: state.navBeforePreview,
      navBeforePreview: null,
      clearPeek: false,
    };
  }
  return {
    previewOpen: false,
    navCollapsed: state.navCollapsed,
    navBeforePreview: null,
    clearPeek: false,
  };
}
