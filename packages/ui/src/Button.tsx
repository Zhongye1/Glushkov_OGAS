export function Button({ label, onClick }: { label: string; onClick?: () => void }) {
  return (
    <button type="button" onClick={onClick}>
      {label}
    </button>
  );
}
