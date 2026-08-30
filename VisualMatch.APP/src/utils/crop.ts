export interface Rect {
  x: number;
  y: number;
  width: number;
  height: number;
}
export interface Size {
  width: number;
  height: number;
}

/** Maps an overlay ROI to source pixels when the preview uses resizeMode="cover". */
export function calculateCropRegion(
  preview: Size,
  image: Size,
  roi: Rect,
): Rect {
  if (
    [
      preview.width,
      preview.height,
      image.width,
      image.height,
      roi.width,
      roi.height,
    ].some((v) => !Number.isFinite(v) || v <= 0)
  )
    throw new Error("Dimensões inválidas para crop.");
  const scale = Math.max(
    preview.width / image.width,
    preview.height / image.height,
  );
  const renderedWidth = image.width * scale;
  const renderedHeight = image.height * scale;
  const hiddenX = (renderedWidth - preview.width) / 2;
  const hiddenY = (renderedHeight - preview.height) / 2;
  const x = Math.max(0, Math.round((roi.x + hiddenX) / scale));
  const y = Math.max(0, Math.round((roi.y + hiddenY) / scale));
  return {
    x,
    y,
    width: Math.min(image.width - x, Math.round(roi.width / scale)),
    height: Math.min(image.height - y, Math.round(roi.height / scale)),
  };
}
