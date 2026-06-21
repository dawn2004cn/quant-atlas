import { Component, type ErrorInfo, type ReactNode } from "react";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

type FallbackRender = (props: {
  error: Error;
  retry: () => void;
  retryCount: number;
}) => ReactNode;

type Props = {
  children: ReactNode;
  fallback?: FallbackRender;
  maxRetries?: number;
  label?: string;
};

type State = {
  error: Error | null;
  retryCount: number;
};

/* ------------------------------------------------------------------ */
/*  Default fallback                                                   */
/* ------------------------------------------------------------------ */

function defaultFallback({ error, retry, retryCount }: {
  error: Error;
  retry: () => void;
  retryCount: number;
}): ReactNode {
  const isNetwork =
    error.message.includes("fetch") ||
    error.message.includes("network") ||
    error.message.includes("Network") ||
    error.message.includes("Failed to fetch");

  return (
    <div className="flex min-h-[60vh] items-center justify-center px-4">
      <div className="glass-card w-full max-w-md space-y-4 p-8 text-center">
        <h2 className="text-xl font-bold text-rose-600">
          {isNetwork ? "网络连接异常" : "页面遇到了问题"}
        </h2>
        <p className="text-sm text-slate-500">
          {isNetwork
            ? "请检查网络连接后重试"
            : error.message || "发生了未知错误"}
        </p>
        <div className="flex items-center justify-center gap-3">
          <button type="button" className="btn btn-primary" onClick={retry}>
            {retryCount > 0 ? "重试 (" + retryCount + ")" : "重试"}
          </button>
          <button
            type="button"
            className="btn btn-ghost"
            onClick={() => {
              window.location.href = "/app";
            }}
          >
            返回首页
          </button>
        </div>
        {retryCount > 1 && (
          <p className="text-xs text-slate-400">已重试 {retryCount} 次</p>
        )}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  ErrorBoundary                                                      */
/* ------------------------------------------------------------------ */

export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null, retryCount: 0 };

  static getDerivedStateFromError(error: Error): Partial<State> {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    const label = this.props.label ?? "ErrorBoundary";
    console.error("[" + label + "]", error.message, info.componentStack);
  }

  private handleRetry = () => {
    const max = this.props.maxRetries ?? 3;
    const nextCount = this.state.retryCount + 1;

    if (max >= 0 && nextCount > max) {
      this.setState({ retryCount: nextCount });
      console.warn(
        "[ErrorBoundary] maxRetries (" + max + ") exceeded, giving up.",
      );
      return;
    }

    this.setState({ error: null, retryCount: nextCount });
  };

  render() {
    if (this.state.error) {
      const renderFn = this.props.fallback ?? defaultFallback;
      return renderFn({
        error: this.state.error,
        retry: this.handleRetry,
        retryCount: this.state.retryCount,
      });
    }
    return this.props.children;
  }
}
