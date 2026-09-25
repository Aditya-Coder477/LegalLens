import React from 'react';
import { cn } from '../../lib/utils/cn';

interface SourceBadgeProps {
  authority: string;
  synthetic?: boolean;
  className?: string;
}

export const SourceBadge: React.FC<SourceBadgeProps> = ({
  authority,
  synthetic = true,
  className,
}) => {
  const getBadgeConfig = () => {
    const auth = (authority || '').toUpperCase();
    if (auth === 'USER_DOCUMENT') {
      return {
        label: 'User Document',
        classes: 'bg-orange-50 text-orange-800 border-orange-200',
      };
    }
    if (auth === 'OFFICIAL') {
      return {
        label: 'Official Gazette',
        classes: 'bg-emerald-50 text-emerald-800 border-emerald-200',
      };
    }
    if (auth === 'COURT') {
      return {
        label: 'Judicial Ruling',
        classes: 'bg-blue-50 text-blue-800 border-blue-200',
      };
    }
    if (auth === 'GOVERNMENT') {
      return {
        label: 'Government Authority',
        classes: 'bg-teal-50 text-teal-800 border-teal-200',
      };
    }
    if (synthetic || auth === 'SYNTHETIC') {
      return {
        label: 'Reference Corpus',
        classes: 'bg-purple-50 text-purple-800 border-purple-200',
      };
    }
    return {
      label: authority,
      classes: 'bg-slate-50 text-slate-800 border-slate-200',
    };
  };

  const { label, classes } = getBadgeConfig();

  return (
    <span
      className={cn(
        'inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium border shadow-xs',
        classes,
        className
      )}
    >
      {label}
    </span>
  );
};
