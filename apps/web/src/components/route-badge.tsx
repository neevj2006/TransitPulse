function contrastText(hex: string) {
  const value = hex.replace("#", "");
  if (!/^[0-9a-f]{6}$/i.test(value)) return "var(--text)";
  const [red, green, blue] = [0, 2, 4].map((start) =>
    Number.parseInt(value.slice(start, start + 2), 16),
  );
  const luminance = (red * 299 + green * 587 + blue * 114) / 1000;
  return luminance > 145 ? "#142033" : "#ffffff";
}

export function RouteBadge({
  label,
  color,
}: {
  label: string;
  color?: string;
}) {
  const safeColor = color && /^#[0-9a-f]{6}$/i.test(color) ? color : undefined;
  if (!safeColor)
    return (
      <span className="bg-surface-muted text-text rounded-full border px-3 py-1 text-sm font-semibold">
        {label}
      </span>
    );
  return (
    <span
      className="rounded-full border px-3 py-1 text-sm font-semibold"
      style={{
        backgroundColor: safeColor,
        color: contrastText(safeColor),
        borderColor: "var(--border-strong)",
      }}
    >
      {label}
    </span>
  );
}
