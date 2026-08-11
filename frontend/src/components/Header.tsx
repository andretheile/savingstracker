import React from 'react';
import { RefreshCw, Send, Plus, Search, Crown } from 'lucide-react';

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
    <header className="sticky top-0 z-40 cream-panel border-b border-[#E5DEC9] px-6 py-4 bg-[#FFFFFF]/95 backdrop-blur-md">
      <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
        
        {/* Brand & Logo */}
        <div className="flex items-center gap-3.5">
          <div className="w-10 h-10 bg-[#1A150E] border border-[#C5A059] flex items-center justify-center text-[#F4E5C2]">
            <Crown className="w-5 h-5 text-[#E5C158]" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-extrabold tracking-tight text-[#1A150E] font-heading">
                Savings<span className="text-[#A38038]">Tracker</span>
              </h1>
              <span className="px-2.5 py-0.5 text-[10px] font-bold tracking-widest uppercase bg-[#F7F3EB] text-[#8C6D23] border border-[#E5DEC9]">
                FinTS / HBCI Active
              </span>
            </div>
            <p className="text-[11px] text-[#6E604D] font-medium">Modular Financial Intelligence & Custom KPI Engine</p>
          </div>
        </div>

        {/* Search & Actions */}
        <div className="flex flex-wrap items-center gap-3 w-full md:w-auto">
          {/* Search */}
          <div className="relative flex-1 md:flex-initial min-w-[220px]">
            <Search className="absolute left-3.5 top-2.5 w-4 h-4 text-[#8C7B65]" />
            <input
              type="text"
              placeholder="Search accounts, rules, KPIs..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="cream-input pl-9 pr-4 py-2 text-xs w-full focus:outline-none placeholder:text-[#9A8B76]"
            />
          </div>

          {/* Telegram Status */}
          <div className="hidden lg:flex items-center gap-2 px-3 py-1.5 bg-[#F7F3EB] border border-[#E5DEC9] text-[#7A602B] text-xs font-semibold">
            <Send className="w-3.5 h-3.5 text-[#A38038]" />
            <span>Telegram Bot Connected</span>
          </div>

          {/* Action Buttons */}
          <button
            onClick={onSyncBank}
            disabled={isSyncing}
            className="cream-button px-3.5 py-2 text-xs font-semibold text-[#1A150E] flex items-center gap-2 border-[#E5DEC9] disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 text-[#A38038] ${isSyncing ? 'animate-spin' : ''}`} />
            <span>{isSyncing ? 'Syncing Bank...' : 'Sync Banks'}</span>
          </button>

          <button
            onClick={onOpenNewTx}
            className="gold-button-primary px-4 py-2 text-xs flex items-center gap-1.5"
          >
            <Plus className="w-4 h-4 text-[#E5C158]" />
            <span>Add Transaction</span>
          </button>
        </div>

      </div>
    </header>
  );
};
