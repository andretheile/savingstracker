import React from 'react';
import type { BalanceSheetData } from '../types';
import { Scale } from 'lucide-react';

interface BalanceSheetViewProps {
  balanceSheet: BalanceSheetData;
}

export const BalanceSheetView: React.FC<BalanceSheetViewProps> = ({ balanceSheet }) => {
  return (
    <div className="glass-panel p-6 rounded-3xl mb-8">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-2">
          <Scale className="w-5 h-5 text-emerald-400" />
          <h2 className="text-xl font-bold text-white font-heading">Balance Sheet — {balanceSheet.period_name}</h2>
        </div>
        <span className="text-xs font-semibold text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-3 py-1 rounded-xl">
          Net Cashflow: +€{balanceSheet.net_cashflow.toLocaleString('de-DE', { minimumFractionDigits: 2 })}
        </span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        
        {/* Expense Breakdown Column */}
        <div className="lg:col-span-7 space-y-4">
          <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2 flex items-center justify-between">
            <span>Expenses Breakdown</span>
            <span>Total: €{balanceSheet.total_expense.toLocaleString()}</span>
          </h3>

          <div className="space-y-3">
            {balanceSheet.expense_items.map((item, idx) => (
              <div key={idx} className="bg-slate-900/60 p-3.5 rounded-2xl border border-slate-800/80 hover:border-slate-700 transition">
                <div className="flex items-center justify-between text-xs mb-1.5">
                  <span className="flex items-center gap-2 font-semibold text-slate-200">
                    <span className="text-base">{item.icon}</span>
                    <span>{item.category_name}</span>
                  </span>
                  <div className="flex items-center gap-3">
                    <span className="text-slate-400 font-mono">{item.percentage.toFixed(1)}%</span>
                    <span className="font-bold text-slate-100 font-mono">€{item.amount.toLocaleString('de-DE', { minimumFractionDigits: 2 })}</span>
                  </div>
                </div>

                {/* Progress bar */}
                <div className="w-full bg-slate-950 h-2 rounded-full overflow-hidden">
                  <div
                    className="bg-gradient-to-r from-cyan-500 to-indigo-500 h-full rounded-full transition-all duration-500"
                    style={{ width: `${Math.min(100, item.percentage)}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Account Balances Summary Column */}
        <div className="lg:col-span-5 bg-slate-900/50 p-5 rounded-2xl border border-slate-800/80 flex flex-col justify-between">
          <div>
            <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-4">
              Running Account Balances
            </h3>

            <div className="space-y-3 mb-6">
              {Object.entries(balanceSheet.account_balances).map(([accName, balance], idx) => (
                <div key={idx} className="flex items-center justify-between p-3 rounded-xl bg-slate-950/60 border border-slate-800">
                  <span className="text-xs font-medium text-slate-300">{accName}</span>
                  <span className="text-sm font-bold text-cyan-400 font-heading">
                    €{balance.toLocaleString('de-DE', { minimumFractionDigits: 2 })}
                  </span>
                </div>
              ))}
            </div>
          </div>

          <div className="bg-slate-950/80 p-4 rounded-xl border border-slate-800">
            <div className="flex justify-between text-xs mb-1">
              <span className="text-slate-400">Total Liquid Capital</span>
              <span className="font-bold text-white font-heading">
                €{Object.values(balanceSheet.account_balances).reduce((a, b) => a + b, 0).toLocaleString('de-DE', { minimumFractionDigits: 2 })}
              </span>
            </div>
            <p className="text-[10px] text-slate-500">Includes Giro, Savings & Depot accounts</p>
          </div>

        </div>

      </div>
    </div>
  );
};
