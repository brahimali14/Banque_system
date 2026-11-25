const TRACES = {
  valide: <path d="M5 12.5l4.2 4.2L19 7" />,
  refus: <path d="M7 7l10 10M17 7L7 17" />,
  fermer: <path d="M7 7l10 10M17 7L7 17" />,
  attente: <circle cx="12" cy="12" r="6.5" />,
  retour: <path d="M19 12H5m0 0l6-6m-6 6l6 6" />,
}
const SENS = new Set(['retour'])

export default function Icone({ nom, className = '' }) {
  return (
    <svg
      className={`icone ${SENS.has(nom) ? 'icone-sens' : ''} ${className}`}
      viewBox="0 0 24 24"
      aria-hidden="true"
      focusable="false"
    >
      {TRACES[nom]}
    </svg>
  )
}
