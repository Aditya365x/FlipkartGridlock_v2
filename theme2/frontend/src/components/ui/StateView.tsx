import { AlertTriangle, RefreshCw } from "lucide-react";

export function Loading({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="grid h-[55vh] place-items-center text-ink-muted">
      <div className="flex items-center gap-3">
        <span className="h-3 w-3 animate-pulseDot rounded-full bg-brand" />
        {label}
      </div>
    </div>
  );
}

export function ErrorState({ msg, onRetry }: { msg: string; onRetry?: () => void }) {
  return (
    <div className="glass mx-auto mt-10 max-w-lg p-6 text-center">
      <AlertTriangle className="mx-auto mb-2 h-8 w-8 text-danger" />
      <div className="font-semibold text-ink">Cannot reach the API</div>
      <div className="mt-1 break-words text-sm text-ink-muted">{msg}</div>
      <div className="mt-3 text-xs text-ink-faint">
        Start the backend:{" "}
        <code className="rounded bg-white/10 px-1.5 py-0.5">uvicorn api.main:app --port 8000</code>
      </div>
      {onRetry && (
        <button onClick={onRetry} className="mt-4 inline-flex items-center gap-2 rounded-xl border border-line bg-white/5 px-4 py-2 text-sm text-ink-muted hover:border-brand/40">
          <RefreshCw className="h-4 w-4" /> Retry
        </button>
      )}
    </div>
  );
}
