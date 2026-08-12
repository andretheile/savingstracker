import React from 'react';
import type { BalanceSheetData, LineItem } from '../types';
import { CategoryIcon } from './CategoryIcon';

interface BalanceSheetViewProps {
  balanceSheet: BalanceSheetData;
}

const CategoryList: React.FC<{
  title: string;
  total: number;
  items: LineItem[];
  empty: string;
}> = ({ title, total, items, empty }) => (
  <div className="space-y-4">
    <h3 className="text-[11px] font-medium text-[#8A8278] uppercase tracking-wide mb-2 flex items-center justify-between">
      <span>{title}</span>
      <span className="text-[#1A1714] normal-case tracking-normal tabular-nums">
        €{total.toLocaleString('de-DE', { minimumFractionDigits: 2 })}
      </span>
    </h3>

    <div className="space-y-2.5">
      {items.length === 0 ? (
        <p className="text-xs text-[#8A8278] p-3.5 border border-dashed border-[#E5DFD4]">{empty}</p>
      ) : (
        items.map((item, idx) => (
          <div key={`${item.category_name}-${idx}`} className="p-3.5 border border-[#E5DFD4]">
            <div className="flex items-center justify-between text-xs mb-2">
              <span className="flex items-center gap-2 font-medium text-[#1A1714]">
                <CategoryIcon name={item.category_name} className="w-3.5 h-3.5 text-[#8F7848] shrink-0" />
                <span>{item.category_name}</span>
              </span>
              <div className="flex items-center gap-4 shrink-0">
                <span className="text-[#8A8278] tabular-nums w-12 text-right">{item.percentage.toFixed(1)}%</span>
                <span className="font-medium text-[#1A1714] tabular-nums w-[5.5rem] text-right">
                  €{item.amount.toLocaleString('de-DE', { minimumFractionDigits: 2 })}
                </span>
              </div>
            </div>
            <div className="w-full bg-[#EDE8DC] h-1 overflow-hidden">
              <div
                className="bg-[#1A1714] h-full"
                style={{ width: `${Math.min(100, item.percentage)}%` }}
              />
            </div>
          </div>
        ))
      )}
    </div>
  </div>
);

export const BalanceSheetView: React.FC<BalanceSheetViewProps> = ({ balanceSheet }) => {
  return (
    <div className="cream-panel p-6 mb-8">
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-3 mb-6">
        <div>
          <h2 className="text-lg font-semibold text-[#1A1714] font-heading">
            Balance sheet — {balanceSheet.period_name}
          </h2>
          <p className="text-xs text-[#6B645A] mt-0.5">
            Household accounts only. Transfers between them are excluded. Money in from personal accounts counts as income.
          </p>
        </div>
        <span className="text-xs font-medium text-[#1A1714] tabular-nums">
          Net {balanceSheet.net_cashflow >= 0 ? '+' : ''}€{balanceSheet.net_cashflow.toLocaleString('de-DE', { minimumFractionDigits: 2 })}
        </span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 mb-8">
        <div className="lg:col-span-6">
          <CategoryList
            title="Income"
            total={balanceSheet.total_income}
            items={balanceSheet.income_items}
            empty="No counted household income this month. Mark salary accounts as Personal in Banking so transfers in are treated as income."
          />
        </div>
        <div className="lg:col-span-6">
          <CategoryList
            title="Expenses"
            total={balanceSheet.total_expense}
            items={balanceSheet.expense_items}
            empty="No expenses recorded this month yet."
          />
        </div>
      </div>

      <div className="bg-[#F3F0EA] p-5 border border-[#E5DFD4]">
        <h3 className="text-[11px] font-medium text-[#8A8278] uppercase tracking-wide mb-4">
          Household accounts
        </h3>

        <div className="space-y-2 mb-4">
          {Object.keys(balanceSheet.account_balances).length === 0 ? (
            <p className="text-xs text-[#8A8278]">No household accounts yet.</p>
          ) : (
            Object.entries(balanceSheet.account_balances).map(([accName, balance]) => (
              <div key={accName} className="flex items-center justify-between p-3 bg-[#FFFFFF] border border-[#E5DFD4]">
                <span className="text-xs font-medium text-[#1A1714]">{accName}</span>
                <span className="text-sm font-semibold text-[#1A1714] font-heading tabular-nums">
                  €{balance.toLocaleString('de-DE', { minimumFractionDigits: 2 })}
                </span>
              </div>
            ))
          )}
        </div>

        <div className="flex justify-between text-xs pt-1">
          <span className="text-[#6B645A]">Liquid capital</span>
          <span className="font-semibold text-[#1A1714] font-heading tabular-nums">
            €{Object.values(balanceSheet.account_balances).reduce((a, b) => a + b, 0).toLocaleString('de-DE', { minimumFractionDigits: 2 })}
          </span>
        </div>
      </div>
    </div>
  );
};
