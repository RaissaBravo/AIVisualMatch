export interface MatchRule {
  /** Cosine is measured after centroid subtraction, so this is not a raw-cosine value. */
  threshold: number;
  /** Minimum lead the winner must have over the runner-up to be trusted. */
  margin: number;
}
/**
 * Each encoder spreads similarities differently, so every model gets its own
 * rule. The new models start from the MobileNetV2 values: on the catalog
 * (VisualMatch.API/scripts/evaluate_models.py) they already make fewer wrong
 * matches with them. Calibrate on device before trusting them.
 */
export const MATCH_RULES: Record<string, MatchRule> = {
  mobilenetv2: { threshold: 0.45, margin: 0.08 },
  mobilenetv3: { threshold: 0.45, margin: 0.08 },
  "dinov2-small": { threshold: 0.45, margin: 0.08 },
  "mobileclip2-s0": { threshold: 0.45, margin: 0.08 },
};
export const matchRuleFor = (model?: string | null): MatchRule =>
  (model && MATCH_RULES[model]) || MATCH_RULES.mobilenetv2;
/** Frames averaged before ranking, to reject single-frame flukes. */
export const SMOOTHING_WINDOW = 3;
/** Below this, the centroid collapses the references instead of separating them. */
export const MIN_REFERENCES_FOR_CENTERING = 3;
export const DETECTION_INTERVAL_MS = 1000;
export const MAX_RESULTS = 5;
export const ROI_WIDTH_RATIO = 0.75;
export const ROI_HEIGHT_RATIO = 0.45;
