export default function RequestDiagnostics({ diagnostics }) {
  if (!diagnostics) {
    return null;
  }

  return (
    <details>
      <summary>Failure diagnostics</summary>
      <pre>{JSON.stringify(diagnostics, null, 2)}</pre>
    </details>
  );
}
