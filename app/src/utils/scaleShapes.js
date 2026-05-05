export function scaleCircles(rawCircles, imageInfo) {
  const { scaleX, scaleY } = imageInfo;
  return rawCircles.map((c) => ({
    ...c,
    x: c.x * scaleX,
    y: c.y * scaleY,
    r: c.r * Math.min(scaleX, scaleY),
  }));
}

export function scaleTexts(rawTexts, imageInfo) {
  const { scaleX, scaleY } = imageInfo;
  return rawTexts.map((t) => ({
    ...t,
    x1: t.x1 * scaleX,
    y1: t.y1 * scaleY,
    x2: t.x2 * scaleX,
    y2: t.y2 * scaleY,
  }));
}
