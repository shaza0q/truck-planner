import { Component, ErrorInfo, ReactNode } from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';

interface Props {
  children: ReactNode;
  fallbackTitle?: string;
  fallbackMessage?: string;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('ErrorBoundary caught an error:', error, errorInfo);
  }

  public handleReset = () => {
    this.setState({ hasError: false, error: null });
  };

  public render() {
    if (this.state.hasError) {
      return (
        <div className="p-5 rounded-lg bg-white border border-[#D9DAD5] text-[#202321] space-y-3">
          <div className="flex items-start gap-3">
            <div className="p-2 rounded bg-[#FEF2F2] text-[#B91C1C] border border-[#FCA5A5] shrink-0">
              <AlertTriangle className="w-4 h-4" />
            </div>
            <div>
              <h4 className="text-sm font-semibold text-[#202321]">
                {this.props.fallbackTitle || 'Component Display Notice'}
              </h4>
              <p className="text-xs text-[#626862] mt-0.5">
                {this.props.fallbackMessage || this.state.error?.message || 'A rendering issue occurred in this section.'}
              </p>
            </div>
          </div>
          <button
            onClick={this.handleReset}
            className="px-3.5 py-1.5 rounded bg-[#FAFAF8] hover:bg-[#F5F5F2] text-xs font-medium text-[#202321] border border-[#D9DAD5] flex items-center gap-1.5 transition cursor-pointer"
          >
            <RefreshCw className="w-3.5 h-3.5 text-[#245C4A]" />
            Retry Rendering
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}

