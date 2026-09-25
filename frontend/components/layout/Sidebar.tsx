'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  LayoutDashboard,
  Files,
  MessageSquareText,
  GitCompare,
  Database,
  FileCheck,
  Scale,
  Clock,
  Shield,
} from 'lucide-react';
import { cn } from '../../lib/utils/cn';

export const Sidebar: React.FC = () => {
  const pathname = usePathname();

  const navGroups = [
    {
      title: 'Workspace',
      items: [
        { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
        { name: 'Documents', href: '/documents', icon: Files },
        { name: 'Ask LegalLens', href: '/ask', icon: MessageSquareText },
        { name: 'Compare', href: '/compare', icon: GitCompare },
        { name: 'Sources', href: '/sources', icon: Database },
      ],
    },
    {
      title: 'Analysis',
      items: [
        { name: 'Summaries', href: '/documents/SYN-CONT-001/summary', icon: FileCheck },
        { name: 'Clauses', href: '/documents/SYN-CONT-001/clauses', icon: Scale },
        { name: 'Obligations', href: '/documents/SYN-CONT-001/obligations', icon: Shield },
        { name: 'Deadlines', href: '/documents/SYN-CONT-001/deadlines', icon: Clock },
      ],
    },
  ];

  return (
    <aside className="w-64 border-r border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 flex flex-col justify-between h-screen sticky top-0 transition-colors">
      <div>
        {/* Brand */}
        <div className="h-16 border-b border-slate-200 dark:border-slate-800 px-6 flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-blue-600 text-white flex items-center justify-center font-bold text-sm shadow-xs">
            LL
          </div>
          <div>
            <h1 className="font-bold text-sm text-slate-900 dark:text-slate-100 tracking-tight">LegalLens</h1>
            <p className="text-[10px] text-slate-500 dark:text-slate-400 uppercase tracking-widest font-medium">
              Evidence-First AI
            </p>
          </div>
        </div>

        {/* Nav Links */}
        <div className="p-4 space-y-6 overflow-y-auto">
          {navGroups.map((group) => (
            <div key={group.title}>
              <h2 className="text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider px-3 mb-2">
                {group.title}
              </h2>
              <nav className="space-y-1">
                {group.items.map((item) => {
                  const isActive =
                    pathname === item.href ||
                    (item.href !== '/dashboard' &&
                      pathname?.startsWith(item.href) &&
                      item.href !== '/documents/SYN-CONT-001/summary');
                  const Icon = item.icon;

                  return (
                    <Link
                      key={item.name}
                      href={item.href}
                      className={cn(
                        'flex items-center gap-3 px-3 py-2 rounded-lg text-xs font-medium transition',
                        isActive
                          ? 'bg-blue-50 dark:bg-blue-950/50 text-blue-700 dark:text-blue-400 font-semibold'
                          : 'text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800/60 hover:text-slate-900 dark:hover:text-slate-200'
                      )}
                    >
                      <Icon className={cn('w-4 h-4', isActive ? 'text-blue-600 dark:text-blue-400' : 'text-slate-400 dark:text-slate-500')} />
                      <span>{item.name}</span>
                    </Link>
                  );
                })}
              </nav>
            </div>
          ))}
        </div>
      </div>
    </aside>
  );
};
