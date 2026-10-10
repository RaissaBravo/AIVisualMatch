// Cosine is measured after centroid subtraction, so these are not raw-cosine values.
export const MATCH_THRESHOLD = 0.5;
/** Minimum lead the winner must have over the runner-up to be trusted. */
export const MATCH_MARGIN = 0.08;
/** Frames averaged before ranking, to reject single-frame flukes. */
export const SMOOTHING_WINDOW = 3;
/** Below this, the centroid collapses the references instead of separating them. */
export const MIN_REFERENCES_FOR_CENTERING = 3;
export const DETECTION_INTERVAL_MS = 1000;
export const MAX_RESULTS = 5;
export const ROI_WIDTH_RATIO = 0.75;
export const ROI_HEIGHT_RATIO = 0.45;
