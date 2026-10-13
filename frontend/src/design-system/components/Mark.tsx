/** The divider mark of the wordmark, drawn in the current ink; the hinge's hole shows the paper. */
export function Mark({ size = 24, className }: { size?: number; className?: string }) {
  return (
    <svg
      viewBox="0 0 256 256"
      width={size}
      height={size}
      aria-hidden="true"
      focusable="false"
      className={className}
    >
      <g stroke="currentColor" strokeWidth="22" strokeLinecap="butt">
        <line x1="64" y1="62" x2="122.35" y2="179.41" />
        <line x1="192" y1="62" x2="133.65" y2="179.41" />
      </g>
      <circle cx="64" cy="62" r="13" fill="currentColor" />
      <circle cx="192" cy="62" r="13" fill="currentColor" />
      <circle cx="128" cy="192" r="22" fill="currentColor" />
      <circle cx="128" cy="192" r="10" fill="var(--color-paper)" />
    </svg>
  );
}
