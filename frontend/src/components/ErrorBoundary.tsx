/* Doc #1 §6.2 — graceful degradation, never a blank screen */
import React from 'react';

interface ErrorBoundaryProps {
  children: React.ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends React.Component<
  ErrorBoundaryProps,
  ErrorBoundaryState
> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  render() {
    if (this.state.hasError) {
      return (
        <div
          role="alert"
          className="flex min-h-screen flex-col items-center justify-center gap-4 p-4"
        >
          <h1 className="text-field-xl text-field-text-primary">
            Something went wrong
          </h1>
          <p className="text-field-base text-field-text-secondary">
            {this.state.error?.message ?? 'An unexpected error occurred.'}
          </p>
          <button
            onClick={() => {
              this.setState({ hasError: false, error: null });
              window.location.reload();
            }}
            className="min-h-thumb rounded-lg bg-field-text-accent px-6 text-field-base font-semibold text-white"
          >
            Retry
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
