'use client';

import React, { useEffect, useRef } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  Home,
  LayoutDashboard,
  Files,
  MessageSquareText,
  GitCompare,
  Database,
  FileCheck,
  Scale,
  Clock,
  Shield,
  X,
} from 'lucide-react';
import { cn } from '../../lib/utils/cn';

interface SidebarProps {
  mobileOpen?: boolean;
  onCloseMobile?: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  mobileOpen = false,
  onCloseMobile,
}) => {
  const pathname = usePathname();
  const sidebarRef = useRef<HTMLElement>(null);

  // Close mobile drawer on route change
  useEffect(() => {
    if (mobileOpen && onCloseMobile) {
      onCloseMobile();
    }
  }, [pathname]);

  // Handle Escape key to close mobile drawer
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && mobileOpen && onCloseMobile) {
        onCloseMobile();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [mobileOpen, onCloseMobile]);

  const navGroups = [
    {
      title: 'Workspace',
      items: [
        { name: 'Overview', href: '/', icon: Home },
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

  const sidebarContent = (
    <div className="flex flex-col h-full justify-between">
      <div>
        {/* Brand */}
        <div className="h-16 border-b border-slate-200 dark:border-slate-800 px-6 flex items-center justify-between">
          <Link
            href="/"
            className="flex items-center gap-3 group focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 rounded-lg p-1"
          >
            <div className="w-8 h-8 rounded-lg bg-blue-600 group-hover:bg-blue-500 text-white flex items-center justify-center font-bold text-sm shadow-xs transition">
              LL
            </div>
            <div>
              <h1 className="font-bold text-sm text-slate-900 dark:text-slate-100 group-hover:text-blue-600 dark:group-hover:text-blue-400 tracking-tight transition">
                LegalLens
              </h1>
              <p className="text-xs text-slate-500 dark:text-slate-400 font-medium">
                Evidence-First AI
              </p>
            </div>
          </Link>

          {/* Close button for mobile drawer */}
          {onCloseMobile && (
            <button
              type="button"
              onClick={onCloseMobile}
              aria-label="Close navigation menu"
              className="md:hidden p-1.5 rounded-lg text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-100 hover:bg-slate-100 dark:hover:bg-slate-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600"
            >
              <X className="w-5 h-5" aria-hidden="true" />
            </button>
          )}
        </div>

        {/* Nav Links */}
        <div className="p-4 space-y-6 overflow-y-auto max-h-[calc(100vh-4rem)]">
          {navGroups.map((group) => (
            <div key={group.title}>
              <h2 className="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider px-3 mb-2">
                {group.title}
              </h2>
              <nav aria-label={group.title} className="space-y-1">
                {group.items.map((item) => {
                  const isActive =
                    pathname === item.href ||
                    (item.href !== '/' &&
                      item.href !== '/dashboard' &&
                      pathname?.startsWith(item.href) &&
                      item.href !== '/documents/SYN-CONT-001/summary');
                  const Icon = item.icon;

                  return (
                    <Link
                      key={item.name}
                      href={item.href}
                      aria-current={isActive ? 'page' : undefined}
                      className={cn(
                        'flex items-center gap-3 px-3 py-2 rounded-lg text-xs font-medium transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-1',
                        isActive
                          ? 'bg-blue-50 dark:bg-blue-950/50 text-blue-700 dark:text-blue-400 font-semibold'
                          : 'text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800/60 hover:text-slate-900 dark:hover:text-slate-200'
                      )}
                    >
                      <Icon
                        className={cn('w-4 h-4', isActive ? 'text-blue-600 dark:text-blue-400' : 'text-slate-400 dark:text-slate-500')}
                        aria-hidden="true"
                      />
                      <span>{item.name}</span>
                    </Link>
                  );
                })}
              </nav>
            </div>
          ))}
        </div>
      </div>
    </div>
  );

  return (
    <>
      {/* Desktop Persistent Sidebar */}
      <aside
        id="primary-sidebar"
        aria-label="Primary sidebar"
        className="hidden md:flex w-64 border-r border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 flex-col justify-between h-screen sticky top-0 transition-colors"
      >
        {sidebarContent}
      </aside>

      {/* Mobile Drawer Backdrop & Drawer */}
      {mobileOpen && (
        <div className="fixed inset-0 z-50 md:hidden">
          {/* Backdrop */}
          <div
            className="fixed inset-0 bg-slate-900/60 backdrop-blur-xs transition-opacity"
            onClick={onCloseMobile}
            aria-hidden="true"
          />

          {/* Drawer Panel */}
          <aside
            ref={sidebarRef}
            id="mobile-sidebar"
            aria-label="Mobile navigation menu"
            className="fixed inset-y-0 left-0 w-64 bg-white dark:bg-slate-900 border-r border-slate-200 dark:border-slate-800 z-50 shadow-2xl flex flex-col justify-between"
          >
            {sidebarContent}
          </aside>
        </div>
      )}
    </>
  );
};
