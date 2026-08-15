import React from 'react';
import { LogOut, RefreshCw, Plus, Search, Settings } from 'lucide-react';

interface HeaderProps {
  onSyncBank: () => void;
  onOpenNewTx: () => void;
  onOpenNewKpi: () => void;
  onOpenSettings: () => void;
  onLogout: () => void;
  settingsActive?: boolean;
  searchQuery: string;
  setSearchQuery: (query: string) => void;
  isSyncing: boolean;
  userEmail?: string;
}

export const Header: React.FC<HeaderProps> = ({
  onSyncBank,
  onOpenNewTx,
  onOpenNewKpi,
  onOpenSettings,
  onLogout,
  settingsActive = false,
  searchQuery,
  setSearchQuery,
  isSyncing,
  userEmail,
}) => {
  return (
    <header className="py-3.5">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-[#1A1714] flex items-center justify-center rounded-sm shrink-0">
            <span className="text-[#F4F1EA] font-heading text-[13px] font-semibold tracking-tight leading-none">S</span>
          </div>
          <div className="leading-tight">
            <h1 className="text-[15px] font-semibold tracking-tight text-[#1A1714] font-heading">
              SavingsTracker
            </h1>
            <p className="text-[11px] text-[#8A8278]">Personal finance</p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2.5 w-full md:w-auto">
          <div className="relative flex-1 md:flex-initial md:w-[220px]">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-[#8A8278] pointer-events-none" strokeWidth={1.6} />
            <input
              type="text"
              placeholder="Search transactions…"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="cream-input h-8 pl-9 pr-3 text-xs w-full focus:outline-none placeholder:text-[#A39B90]"
            />
          </div>

          <button
            onClick={onSyncBank}
            disabled={isSyncing}
            className="cream-button h-8 px-3 text-xs font-medium flex items-center gap-2 disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isSyncing ? 'animate-spin' : ''}`} strokeWidth={1.6} />
            <span>{isSyncing ? 'Syncing…' : 'Sync'}</span>
          </button>

          <button
            onClick={onOpenNewTx}
            className="gold-button-primary h-8 px-3.5 text-xs flex items-center gap-1.5"
          >
            <Plus className="w-3.5 h-3.5" strokeWidth={1.6} />
            <span>Add transaction</span>
          </button>

          <button
            type="button"
            onClick={onOpenNewKpi}
            className="cream-button h-8 px-3 text-xs flex items-center gap-1.5"
          >
            <Plus className="w-3.5 h-3.5" strokeWidth={1.6} />
            <span>New KPI</span>
          </button>

          <button
            type="button"
            onClick={onOpenSettings}
            aria-label="Settings"
            aria-pressed={settingsActive}
            className={`cream-button h-8 w-8 px-0 ${
              settingsActive ? 'border-[#C4B49A] bg-[#F3F0EA] text-[#1A1714]' : 'text-[#6B645A]'
            }`}
          >
            <Settings className="w-3.5 h-3.5" strokeWidth={1.6} />
          </button>
          <button
            type="button"
            onClick={onLogout}
            title={userEmail ? `Log out ${userEmail}` : 'Log out'}
            className="cream-button h-8 px-3 text-xs text-[#6B645A] inline-flex items-center gap-1.5"
          >
            <LogOut className="w-3.5 h-3.5" strokeWidth={1.6} />
            <span className="hidden sm:inline">Log out</span>
          </button>
        </div>
      </div>
    </header>
  );
};
