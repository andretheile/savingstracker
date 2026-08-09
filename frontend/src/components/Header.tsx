import React from 'react';
import { RefreshCw, Send, Plus, Search, Sparkles } from 'lucide-react';

interface HeaderProps {
  onSyncBank: () => void;
  onOpenNewTx: () => void;
  onOpenNewKpi: () => void;
  searchQuery: string;
  setSearchQuery: (query: string) => void;
  isSyncing: boolean;
}

export const Header: React.FC<HeaderProps> = ({
  onSyncBank,
  onOpenNewTx,
  searchQuery,
  setSearchQuery,
  isSyncing,
}) => {
  return (
    <header className="sticky top-0 z-40 glass-panel border-b border-slate-800/80 px-6 py-4">
      <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
        
        {/* Brand & Logo */}
        <div className="flex items-center gap-3.5">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-emerald-500 via-teal-500 to-amber-500 flex items-center justify-center shadow-lg shadow-emerald-500/20 text-slate-950 font-bold">
            <Sparkles className="w-5 h-5 text-slate-950" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-extrabold tracking-tight text-white font-heading">
                Savings<span className="text-gradient-emerald">Tracker</span>
              </h1>
              <span className="px-2.5 py-0.5 text-[10px] font-bold tracking-wide uppercase rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                FinTS / HBCI Active
              </span>
            </div>
            <p className="text-[11px] text-slate-400 font-medium">Modular Financial Intelligence & Custom KPI Engine</p>
          </div>
        </div>

        {/* Search & Actions */}
        <div className="flex flex-wrap items-center gap-3 w-full md:w-auto">
          {/* Search */}
          <div className="relative flex-1 md:flex-initial min-w-[220px]">
            <Search className="absolute left-3.5 top-2.5 w-4 h-4 text-slate-500" />
            <input
              type="text"
              placeholder="Search accounts, rules, KPIs..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="glass-input pl-9 pr-4 py-2 text-xs rounded-xl w-full focus:outline-none placeholder:text-slate-500"
            />
          </div>

          {/* Telegram Status */}
          <div className="hidden lg:flex items-center gap-2 px-3 py-1.5 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 text-xs font-medium">
            <Send className="w-3.5 h-3.5 text-emerald-400" />
            <span>Telegram Bot Connected</span>
          </div>

          {/* Action Buttons */}
          <button
            onClick={onSyncBank}
            disabled={isSyncing}
            className="glass-button px-3.5 py-2 rounded-xl text-xs font-semibold text-emerald-300 flex items-center gap-2 hover:border-emerald-500/40 disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isSyncing ? 'animate-spin' : ''}`} />
            <span>{isSyncing ? 'Syncing Bank...' : 'Sync Banks'}</span>
          </button>

          <button
            onClick={onOpenNewTx}
            className="bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-400 hover:to-teal-400 text-slate-950 font-bold px-4 py-2 rounded-xl text-xs flex items-center gap-1.5 shadow-lg shadow-emerald-500/25 transition-all transform hover:scale-[1.02]"
          >
            <Plus className="w-4 h-4" />
            <span>Add Transaction</span>
          </button>
        </div>

      </div>
    </header>
  );
};
