import { Component, type ErrorInfo, type ReactNode } from "react";

interface State {
  error: Error | null;
  info: ErrorInfo | null;
}

/**
 * Top-level error boundary so a runtime crash surfaces as a readable
 * error card instead of a black page. The webview inspector is normally
 * the right place to diagnose, but it isn't always reachable in a
 * production launch — this gives the user enough information to paste
 * back to the maintainer.
 */
export class ErrorBoundary extends Component<{ children: ReactNode }, State> {
  state: State = { error: null, info: null };

  static getDerivedStateFromError(error: Error): Partial<State> {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    console.error("App crashed", error, info);
    this.setState({ info });
  }

  reset = () => this.setState({ error: null, info: null });

  render(): ReactNode {
    if (this.state.error) {
      return (
        <div className="min-h-screen bg-background p-8 text-foreground">
          <div className="mx-auto flex max-w-2xl flex-col gap-4">
            <h1 className="text-xl font-semibold">Something went wrong</h1>
            <p className="text-sm text-muted-foreground">
              The app hit a runtime error. Copy the details below and share them
              with the maintainer.
            </p>
            <pre className="overflow-x-auto rounded-md border border-destructive/40 bg-destructive/5 p-3 text-xs">
              {this.state.error.message}
              {"\n\n"}
              {this.state.error.stack}
              {this.state.info?.componentStack
                ? `\n\nComponent stack:${this.state.info.componentStack}`
                : ""}
            </pre>
            <button
              type="button"
              onClick={this.reset}
              className="self-start rounded-md border border-border bg-muted px-3 py-1.5 text-sm hover:bg-accent"
            >
              Try again
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
