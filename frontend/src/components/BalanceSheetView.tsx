import React from 'react';
import type { BalanceSheetData } from '../types';
import { Scale } from 'lucide-react';

interface BalanceSheetViewProps {
  balanceSheet: BalanceSheetData;
}

export const BalanceSheetView: React.FC<BalanceSheetViewProps> = ({ balanceSheet }) => {
  return (
    <div className="cream-panel p-6 mb-8">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-2">
          <Scale className="w-5 h-5 text-[#B8860B]" />
          <h2 className="text-xl font-bold text-[#1C160C] font-heading">Balance Sheet — {balanceSheet.period_name}</h2>
        </div>
        <span className="text-xs font-bold text-[#8C6D23] bg-[#F4EFE6] border border-[#D5C7B0] px-3 py-1">
          Net Cashflow: +€{balanceSheet.net_cashflow.toLocaleString('de-DE', { minimumFractionDigits: 2 })}
        </span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        
        {/* Expense Breakdown Column */}
        <div className="lg:col-span-7 space-y-4">
          <h3 className="text-xs font-bold text-[#8C6D23] uppercase tracking-widest mb-2 flex items-center justify-between">
            <span>Expenses Breakdown</span>
            <span className="text-[#1C160C]">Total: €{balanceSheet.total_expense.toLocaleString()}</span>
          </h3>

          <div className="space-y-3">
            {balanceSheet.expense_items.map((item, idx) => (
              <div key={idx} className="bg-[#FAF7F2] p-3.5 border border-[#E0D4C1] hover:border-[#C5A059] transition">
                <div className="flex items-center justify-between text-xs mb-1.5">
                  <span className="flex items-center gap-2 font-bold text-[#1C160C]">
                    <span className="text-base">{item.icon}</span>
                    <span>{item.category_name}</span>
                  </span>
                  <div className="flex items-center gap-3">
                    <span className="text-[#6E5E4A] font-mono">{item.percentage.toFixed(1)}%</span>
                    <span className="font-bold text-[#1C160C] font-mono">€{item.amount.toLocaleString('de-DE', { minimumFractionDigits: 2 })}</span>
                  </div>
                </div>

                {/* Progress bar */}
                <div className="w-full bg-[#E2D5C3] h-2 overflow-hidden">
                  <div
                    className="bg-[#1C160C] h-full transition-all duration-500"
                    style={{ width: `${Math.min(100, item.percentage)}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Account Balances Summary Column */}
        <div className="lg:col-span-5 bg-[#FAF7F2] p-5 border border-[#E0D4C1] flex flex-col justify-between">
          <div>
            <h3 className="text-xs font-bold text-[#8C6D23] uppercase tracking-widest mb-4">
              Running Account Balances
            </h3>

            <div className="space-y-3 mb-6">
              {Object.entries(balanceSheet.account_balances).map(([accName, balance], idx) => (
                <div key={idx} className="flex items-center justify-between p-3 bg-[#FFFFFF] border border-[#E0D4C1]">
                  <span className="text-xs font-semibold text-[#362C1E]">{accName}</span>
                  <span className="text-sm font-extrabold text-[#B8860B] font-heading">
                    €{balance.toLocaleString('de-DE', { minimumFractionDigits: 2 })}
                  </span>
                </div>
              ))}
            </div>
          </div>

          <div className="bg-[#FFFFFF] p-4 border border-[#E0D4C1]">
            <div className="flex justify-between text-xs mb-1">
              <span className="text-[#6E5E4A] font-medium">Total Liquid Capital</span>
              <span className="font-extrabold text-[#1C160C] font-heading">
                €{Object.values(balanceSheet.account_balances).reduce((a, b) => a + b, 0).toLocaleString('de-DE', { minimumFractionDigits: 2 })}
              </span>
            </div>
            <p className="text-[10px] text-[#7A6E5D]">Includes Giro, Savings & Depot accounts</p>
          </div>

        </div>

      </div>
    </div>
  );
};
