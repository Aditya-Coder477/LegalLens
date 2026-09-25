'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Search, ShieldCheck, Sparkles } from 'lucide-react';
import { ThemeToggle } from '../theme/ThemeToggle';

export const Header: React.FC = () => {
  const [searchQuery, setSearchQuery] = useState('');
  const router = useRouter();

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      router.push(`/ask?q=${encodeURIComponent(searchQuery.trim())}`);
    }
  };

  return (
    <header className="h-16 border-b border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 px-8 flex items-center justify-between sticky top-0 z-30 transition-colors">
      {/* Global Query / Ask Bar */}
      <form onSubmit={handleSearchSubmit} className="relative w-full max-w-md">
        <Search className="w-4 h-4 text-slate-400 dark:text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
        <input
          type="text"
          placeholder="Ask a legal question or search sections..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-full bg-slate-50 hover:bg-slate-100/80 focus:bg-white dark:bg-slate-800 dark:hover:bg-slate-700/80 dark:focus:bg-slate-800 pl-9 pr-4 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 text-xs text-slate-900 dark:text-slate-100 placeholder-slate-400 dark:placeholder-slate-500 focus:outline-hidden focus:ring-1 focus:ring-blue-600 transition"
        />
      </form>

      {/* Badges, Theme Toggle, and Actions */}
      <div className="flex items-center gap-3">
        <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-blue-50 dark:bg-blue-950/60 text-blue-800 dark:text-blue-300 border border-blue-200 dark:border-blue-800">
          <ShieldCheck className="w-3.5 h-3.5 text-blue-600 dark:text-blue-400" />
          <span>Evidence-First AI</span>
        </div>

        <Link
          href="/demo"
          className="hidden md:inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-purple-50 hover:bg-purple-100 dark:bg-purple-950/60 dark:hover:bg-purple-900/60 text-purple-700 dark:text-purple-300 border border-purple-200 dark:border-purple-800 transition"
        >
          <Sparkles className="w-3.5 h-3.5" />
          <span>Demo Flow</span>
        </Link>

        {/* Theme Toggle Button */}
        <ThemeToggle />
      </div>
    </header>
  );
};
