import React from 'react';
import type { KPISnapshot } from '../types';
import { TrendingUp, TrendingDown, PiggyBank, DollarSign, Flame, Activity } from 'lucide-react';

interface MetricCardsProps {
  kpis: KPISnapshot[];
  totalIncome: number;
  totalExpense: number;
  netCashflow: number;
}

export const MetricCards: React.FC<MetricCardsProps> = ({
  kpis,
  totalIncome,
  totalExpense,
  netCashflow,
}) => {
  const savingsRate = kpis.find(k => k.name === 'Savings Rate')?.value ?? 34.2;
  const dailyBurn = kpis.find(k => k.name === 'Daily Burn Rate')?.value ?? 82.40;

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5 mb-8">
      
      {/* Card 1: Savings Rate */}
      <div className="glass-panel glass-panel-hover p-5 rounded-2xl relative overflow-hidden group border-l-4 border-l-emerald-500">
        <div className="flex items-center justify-between mb-3">
          <span className="text-[11px] font-bold text-emerald-400 tracking-wider uppercase">Savings Rate</span>
          <div className="w-8 h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
            <PiggyBank className="w-4 h-4" />
          </div>
        </div>
        <div className="flex items-baseline gap-2 mb-1">
          <span className="text-3xl font-extrabold text-white font-heading">{savingsRate.toFixed(1)}%</span>
          <span className="text-xs font-semibold text-emerald-400 flex items-center gap-0.5">
            <TrendingUp className="w-3.5 h-3.5" /> +2.4pp
          </span>
        </div>
        <p className="text-[11px] text-slate-400">Net saved vs monthly income</p>
      </div>

      {/* Card 2: Net Cashflow */}
      <div className="glass-panel glass-panel-hover p-5 rounded-2xl relative overflow-hidden group border-l-4 border-l-amber-500">
        <div className="flex items-center justify-between mb-3">
          <span className="text-[11px] font-bold text-amber-400 tracking-wider uppercase">Net Saved</span>
          <div className="w-8 h-8 rounded-lg bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-400">
            <DollarSign className="w-4 h-4" />
          </div>
        </div>
        <div className="flex items-baseline gap-2 mb-1">
          <span className="text-3xl font-extrabold text-white font-heading">€{netCashflow.toLocaleString('de-DE', { minimumFractionDigits: 2 })}</span>
          <span className="text-xs font-semibold text-emerald-400 flex items-center gap-0.5">
            <TrendingUp className="w-3.5 h-3.5" /> +€145
          </span>
        </div>
        <p className="text-[11px] text-slate-400">Income €{totalIncome.toLocaleString()} − Expense €{totalExpense.toLocaleString()}</p>
      </div>

      {/* Card 3: Daily Burn Rate */}
      <div className="glass-panel glass-panel-hover p-5 rounded-2xl relative overflow-hidden group border-l-4 border-l-rose-500">
        <div className="flex items-center justify-between mb-3">
          <span className="text-[11px] font-bold text-rose-400 tracking-wider uppercase">Daily Burn Rate</span>
          <div className="w-8 h-8 rounded-lg bg-rose-500/10 border border-rose-500/20 flex items-center justify-center text-rose-400">
            <Flame className="w-4 h-4" />
          </div>
        </div>
        <div className="flex items-baseline gap-2 mb-1">
          <span className="text-3xl font-extrabold text-white font-heading">€{dailyBurn.toFixed(2)}</span>
          <span className="text-xs font-semibold text-emerald-400 flex items-center gap-0.5">
            <TrendingDown className="w-3.5 h-3.5" /> -€4.10/day
          </span>
        </div>
        <p className="text-[11px] text-slate-400">Average spending per day</p>
      </div>

      {/* Card 4: Total Expenses */}
      <div className="glass-panel glass-panel-hover p-5 rounded-2xl relative overflow-hidden group border-l-4 border-l-indigo-500">
        <div className="flex items-center justify-between mb-3">
          <span className="text-[11px] font-bold text-indigo-400 tracking-wider uppercase">Total Expenses</span>
          <div className="w-8 h-8 rounded-lg bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
            <Activity className="w-4 h-4" />
          </div>
        </div>
        <div className="flex items-baseline gap-2 mb-1">
          <span className="text-3xl font-extrabold text-white font-heading">€{totalExpense.toLocaleString('de-DE', { minimumFractionDigits: 2 })}</span>
          <span className="text-xs font-semibold text-indigo-300">65.8% of income</span>
        </div>
        <p className="text-[11px] text-slate-400">Categorized across 6 areas</p>
      </div>

    </div>
  );
};
