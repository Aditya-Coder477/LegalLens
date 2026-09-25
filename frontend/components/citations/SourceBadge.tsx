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
        classes: 'bg-amber-50 text-amber-800 border-amber-200 dark:bg-amber-950/40 dark:text-amber-300 dark:border-amber-800',
      };
    }
    if (auth === 'USER_PROVIDED' || auth === 'USER') {
      return {
        label: 'User Provided Document',
        classes: 'bg-amber-50 text-amber-800 border-amber-200 dark:bg-amber-950/40 dark:text-amber-300 dark:border-amber-800',
      };
    }
    if (auth === 'OFFICIAL') {
      return {
        label: 'Official Gazette',
        classes: 'bg-emerald-50 text-emerald-800 border-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-300 dark:border-emerald-800',
      };
    }
    if (auth === 'COURT') {
      return {
        label: 'Judicial Ruling',
        classes: 'bg-blue-50 text-blue-800 border-blue-200 dark:bg-blue-950/40 dark:text-blue-300 dark:border-blue-800',
      };
    }
    if (auth === 'GOVERNMENT' || auth === 'STATUTE') {
      return {
        label: 'Official Government Source',
        classes: 'bg-emerald-50 text-emerald-800 border-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-300 dark:border-emerald-800',
      };
    }
    if (auth === 'LEGAL_AID' || auth === 'NALSA') {
      return {
        label: 'Legal Aid Source',
        classes: 'bg-teal-50 text-teal-800 border-teal-200 dark:bg-teal-950/40 dark:text-teal-300 dark:border-teal-800',
      };
    }
    if (synthetic || auth === 'SYNTHETIC') {
      return {
        label: 'Reference Corpus',
        classes: 'bg-purple-50 text-purple-800 border-purple-200 dark:bg-purple-950/40 dark:text-purple-300 dark:border-purple-800',
      };
    }
    if (auth === 'DEMO') {
      return {
        label: 'Synthetic / Demo Data',
        classes: 'bg-purple-50 text-purple-800 border-purple-200 dark:bg-purple-950/40 dark:text-purple-300 dark:border-purple-800',
      };
    }
    if (auth === 'SECONDARY' || auth === 'REFERENCE') {
      return {
        label: 'Secondary Reference',
        classes: 'bg-slate-50 text-slate-800 border-slate-200 dark:bg-slate-800 dark:text-slate-300 dark:border-slate-700',
      };
    }
    return {
      label: authority,
      classes: 'bg-slate-50 text-slate-800 border-slate-200 dark:bg-slate-800 dark:text-slate-300 dark:border-slate-700',
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
