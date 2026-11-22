// Not in Figr: built plainly from design tokens. Stub, replaced in the next build round.
export default function ParkedHome() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-2 bg-night text-ink">
      <span className="rounded-md border border-warn/50 bg-warn-deep px-2.5 py-1 text-sm font-medium text-warn">Simulated</span>
      <h1 className="text-2xl font-semibold">Parked home</h1>
      <p className="text-lg text-ink-muted">Coming up at <code className="font-mono">/home</code></p>
    </div>
  );
}
