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
      <div className="cream-panel cream-panel-hover p-5 relative overflow-hidden group">
        <div className="flex items-center justify-between mb-3">
          <span className="text-[11px] font-semibold text-[#7A602B] tracking-widest uppercase">Savings Rate</span>
          <div className="w-8 h-8 bg-[#F7F3EB] border border-[#E5DEC9] flex items-center justify-center text-[#A38038]">
            <PiggyBank className="w-4 h-4" />
          </div>
        </div>
        <div className="flex items-baseline gap-2 mb-1">
          <span className="text-3xl font-extrabold text-[#1A150E] font-heading">{savingsRate.toFixed(1)}%</span>
          <span className="text-xs font-semibold text-[#8C6D23] flex items-center gap-0.5">
            <TrendingUp className="w-3.5 h-3.5 text-[#A38038]" /> +2.4pp
          </span>
        </div>
        <p className="text-[11px] text-[#6E604D]">Net saved vs monthly income</p>
      </div>

      {/* Card 2: Net Cashflow */}
      <div className="cream-panel cream-panel-hover p-5 relative overflow-hidden group">
        <div className="flex items-center justify-between mb-3">
          <span className="text-[11px] font-semibold text-[#7A602B] tracking-widest uppercase">Net Saved</span>
          <div className="w-8 h-8 bg-[#F7F3EB] border border-[#E5DEC9] flex items-center justify-center text-[#A38038]">
            <DollarSign className="w-4 h-4" />
          </div>
        </div>
        <div className="flex items-baseline gap-2 mb-1">
          <span className="text-3xl font-extrabold text-[#1A150E] font-heading">€{netCashflow.toLocaleString('de-DE', { minimumFractionDigits: 2 })}</span>
          <span className="text-xs font-semibold text-[#8C6D23] flex items-center gap-0.5">
            <TrendingUp className="w-3.5 h-3.5 text-[#A38038]" /> +€145
          </span>
        </div>
        <p className="text-[11px] text-[#6E604D]">Income €{totalIncome.toLocaleString()} − Expense €{totalExpense.toLocaleString()}</p>
      </div>

      {/* Card 3: Daily Burn Rate */}
      <div className="cream-panel cream-panel-hover p-5 relative overflow-hidden group">
        <div className="flex items-center justify-between mb-3">
          <span className="text-[11px] font-semibold text-[#7A602B] tracking-widest uppercase">Daily Burn Rate</span>
          <div className="w-8 h-8 bg-[#F7F3EB] border border-[#E5DEC9] flex items-center justify-center text-[#A38038]">
            <Flame className="w-4 h-4" />
          </div>
        </div>
        <div className="flex items-baseline gap-2 mb-1">
          <span className="text-3xl font-extrabold text-[#1A150E] font-heading">€{dailyBurn.toFixed(2)}</span>
          <span className="text-xs font-semibold text-[#8C6D23] flex items-center gap-0.5">
            <TrendingDown className="w-3.5 h-3.5 text-[#A38038]" /> -€4.10/day
          </span>
        </div>
        <p className="text-[11px] text-[#6E604D]">Average spending per day</p>
      </div>

      {/* Card 4: Total Expenses */}
      <div className="cream-panel cream-panel-hover p-5 relative overflow-hidden group">
        <div className="flex items-center justify-between mb-3">
          <span className="text-[11px] font-semibold text-[#7A602B] tracking-widest uppercase">Total Expenses</span>
          <div className="w-8 h-8 bg-[#F7F3EB] border border-[#E5DEC9] flex items-center justify-center text-[#A38038]">
            <Activity className="w-4 h-4" />
          </div>
        </div>
        <div className="flex items-baseline gap-2 mb-1">
          <span className="text-3xl font-extrabold text-[#1A150E] font-heading">€{totalExpense.toLocaleString('de-DE', { minimumFractionDigits: 2 })}</span>
          <span className="text-xs font-semibold text-[#594E3F]">65.8% of income</span>
        </div>
        <p className="text-[11px] text-[#6E604D]">Categorized across 6 areas</p>
      </div>

    </div>
  );
};
