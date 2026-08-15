import React from 'react';
import { Percent, Wallet, CalendarDays, ArrowDownRight } from 'lucide-react';

interface MetricCardsProps {
  totalIncome: number;
  totalExpense: number;
  netCashflow: number;
  daysInPeriod: number;
  onOpenOverview?: () => void;
  onOpenTransactions?: () => void;
}

const euro = (n: number) =>
  n.toLocaleString('de-DE', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

export const MetricCards: React.FC<MetricCardsProps> = ({
  totalIncome,
  totalExpense,
  netCashflow,
  daysInPeriod,
  onOpenOverview,
  onOpenTransactions,
}) => {
  const savingsRate = totalIncome > 0 ? (netCashflow / totalIncome) * 100 : null;
  const dailyBurn = totalExpense / Math.max(1, daysInPeriod);
  const expenseRatio = totalIncome > 0 ? (totalExpense / totalIncome) * 100 : null;
  const cardClass =
    'cream-panel cream-panel-hover p-5 flex flex-col min-h-[148px] text-left w-full cursor-pointer';

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
      <button type="button" onClick={onOpenOverview} className={cardClass}>
        <div className="flex items-center justify-between mb-4">
          <span className="text-[11px] font-medium text-[#8A8278] tracking-wide uppercase">Savings rate</span>
          <Percent className="w-4 h-4 text-[#8F7848]" strokeWidth={1.6} />
        </div>
        <span className={`text-[28px] font-semibold font-heading tracking-tight leading-none ${
          savingsRate == null ? 'text-[#8A8278]' : savingsRate < 0 ? 'text-[#8C4A3A]' : 'text-[#1A1714]'
        }`}>
          {savingsRate == null ? '—' : `${savingsRate.toFixed(1)}%`}
        </span>
        <p className="text-[11px] text-[#8A8278] mt-auto pt-3">
          {totalIncome > 0
            ? 'Of counted household income'
            : 'No counted household income this month'}
        </p>
      </button>

      <button type="button" onClick={onOpenOverview} className={cardClass}>
        <div className="flex items-center justify-between mb-4">
          <span className="text-[11px] font-medium text-[#8A8278] tracking-wide uppercase">Net saved</span>
          <Wallet className="w-4 h-4 text-[#8F7848]" strokeWidth={1.6} />
        </div>
        <span className={`text-[28px] font-semibold font-heading tracking-tight leading-none ${
          netCashflow < 0 ? 'text-[#8C4A3A]' : 'text-[#1A1714]'
        }`}>
          €{euro(netCashflow)}
        </span>
        <p className="text-[11px] text-[#8A8278] mt-auto pt-3">Income €{euro(totalIncome)} − Expense €{euro(totalExpense)}</p>
      </button>

      <button type="button" onClick={onOpenTransactions} className={cardClass}>
        <div className="flex items-center justify-between mb-4">
          <span className="text-[11px] font-medium text-[#8A8278] tracking-wide uppercase">Daily spend</span>
          <CalendarDays className="w-4 h-4 text-[#8F7848]" strokeWidth={1.6} />
        </div>
        <span className="text-[28px] font-semibold text-[#1A1714] font-heading tracking-tight leading-none">
          €{dailyBurn.toFixed(2)}
        </span>
        <p className="text-[11px] text-[#8A8278] mt-auto pt-3">Average per day this month</p>
      </button>

      <button type="button" onClick={onOpenTransactions} className={cardClass}>
        <div className="flex items-center justify-between mb-4">
          <span className="text-[11px] font-medium text-[#8A8278] tracking-wide uppercase">Expenses</span>
          <ArrowDownRight className="w-4 h-4 text-[#8F7848]" strokeWidth={1.6} />
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[28px] font-semibold text-[#1A1714] font-heading tracking-tight leading-none">
            €{euro(totalExpense)}
          </span>
          {expenseRatio != null && (
            <span className="text-xs font-medium text-[#6B645A]">{expenseRatio.toFixed(1)}% of income</span>
          )}
        </div>
        <p className="text-[11px] text-[#8A8278] mt-auto pt-3">This calendar month</p>
      </button>
    </div>
  );
};
