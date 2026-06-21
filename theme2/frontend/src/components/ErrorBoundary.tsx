import { Component, type ErrorInfo, type ReactNode } from "react";
import { AlertTriangle } from "lucide-react";

interface Props {
  children: ReactNode;
}
interface State {
  error: Error | null;
}

/** App-wide safety net: a render error in any page shows a recoverable card, not a blank screen. */
export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    // eslint-disable-next-line no-console
    console.error("Render error:", error, info);
  }

  render() {
    if (this.state.error) {
      return (
        <div className="grid h-screen place-items-center bg-bg p-6">
          <div className="glass max-w-lg p-8 text-center">
            <AlertTriangle className="mx-auto mb-3 h-10 w-10 text-danger" />
            <div className="font-display text-xl font-bold text-ink">Something went wrong</div>
            <div className="mt-2 break-words text-sm text-ink-muted">{this.state.error.message}</div>
            <button
              onClick={() => this.setState({ error: null })}
              className="mt-5 rounded-xl bg-gradient-to-r from-brand to-brand-cyan px-4 py-2.5 font-semibold text-white shadow-glow hover:brightness-110"
            >
              Reload view
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
