import React from "react";

interface State {
  error: Error | null;
}

/**
 * Keeps one page's render error from blanking the whole dashboard.
 * Navigating to another page (a new location key) clears the error.
 */
export class ErrorBoundary extends React.Component<{ children: React.ReactNode }, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error("Page crashed:", error, info.componentStack);
  }

  render() {
    if (!this.state.error) return this.props.children;

    return (
      <div className="p-8 max-w-xl mx-auto text-center space-y-4">
        <h2 className="text-2xl font-black text-[#2d1e18] font-display">Something went wrong on this page</h2>
        <p className="text-sm font-semibold text-[#3d2b1f]/70">
          The rest of the dashboard is unaffected. Reload the page, or pick another section from the sidebar.
        </p>
        <button
          onClick={() => window.location.reload()}
          className="px-5 py-2.5 bg-[#d4a373] text-white font-bold rounded-lg hover:bg-[#b5835a] cursor-pointer"
        >
          Reload
        </button>
      </div>
    );
  }
}

export default ErrorBoundary;
