/** The mark of the app icon, drawn in the current ink: the divider holding the mark between its points. */
export function Mark({ size = 32, className }: { size?: number; className?: string }) {
  return (
    <svg
      viewBox="0 0 256 256"
      width={size}
      height={size}
      aria-hidden="true"
      focusable="false"
      className={className}
    >
      <g stroke="currentColor" strokeWidth="18" strokeLinecap="butt">
        <line x1="64" y1="70" x2="122.35" y2="179.41" />
        <line x1="192" y1="70" x2="133.65" y2="179.41" />
      </g>
      <circle cx="64" cy="70" r="11" fill="currentColor" />
      <circle cx="192" cy="70" r="11" fill="currentColor" />
      <circle cx="128" cy="190" r="18" fill="currentColor" />
      <circle cx="128" cy="190" r="9" fill="var(--color-paper)" />
      <circle cx="128" cy="84" r="21" fill="var(--color-accent)" />
    </svg>
  );
}
