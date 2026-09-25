import React from 'react';
import { AlertCircle, AlertTriangle, ShieldCheck, ShieldX, Info } from 'lucide-react';
import { cn } from '../../lib/utils/cn';

export type SafetyBannerVariant =
  | 'information'
  | 'warning'
  | 'conflict'
  | 'limited-evidence'
  | 'synthetic'
  | 'professional-review'
  | 'blocked';

interface SafetyBannerProps {
  variant: SafetyBannerVariant;
  title: string;
  message: string;
  className?: string;
  actionText?: string;
  onAction?: () => void;
}

export const SafetyBanner: React.FC<SafetyBannerProps> = ({
  variant,
  title,
  message,
  className,
  actionText,
  onAction,
}) => {
  const getVariantStyles = () => {
    switch (variant) {
      case 'warning':
      case 'conflict':
        return {
          bg: 'bg-amber-50 border-amber-200 text-amber-900',
          icon: <AlertTriangle className="w-5 h-5 text-amber-600 flex-shrink-0" />,
        };
      case 'blocked':
        return {
          bg: 'bg-rose-50 border-rose-200 text-rose-900',
          icon: <ShieldX className="w-5 h-5 text-rose-600 flex-shrink-0" />,
        };
      case 'synthetic':
        return {
          bg: 'bg-purple-50 border-purple-200 text-purple-900',
          icon: <AlertCircle className="w-5 h-5 text-purple-600 flex-shrink-0" />,
        };
      case 'limited-evidence':
        return {
          bg: 'bg-yellow-50 border-yellow-200 text-yellow-900',
          icon: <Info className="w-5 h-5 text-yellow-600 flex-shrink-0" />,
        };
      case 'professional-review':
        return {
          bg: 'bg-blue-50 border-blue-200 text-blue-900',
          icon: <ShieldCheck className="w-5 h-5 text-blue-600 flex-shrink-0" />,
        };
      case 'information':
      default:
        return {
          bg: 'bg-slate-50 border-slate-200 text-slate-900',
          icon: <Info className="w-5 h-5 text-slate-600 flex-shrink-0" />,
        };
    }
  };

  const { bg, icon } = getVariantStyles();

  return (
    <div className={cn('border rounded-lg p-3.5 flex items-start gap-3 text-sm', bg, className)} role="alert">
      {icon}
      <div className="flex-1">
        <h4 className="font-semibold text-xs uppercase tracking-wider mb-0.5">{title}</h4>
        <p className="text-xs leading-relaxed opacity-90">{message}</p>
        {actionText && onAction && (
          <button
            onClick={onAction}
            className="mt-2 text-xs font-medium underline hover:opacity-80 transition"
          >
            {actionText}
          </button>
        )}
      </div>
    </div>
  );
};
