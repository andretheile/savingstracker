import React, { useState } from 'react';
import type { Transaction } from '../types';
import { ListFilter, Tag } from 'lucide-react';

interface TransactionsTableProps {
  transactions: Transaction[];
  searchQuery: string;
  onClassifyTx: (txId: string, categoryName: string, categoryIcon: string) => void;
}

export const TransactionsTable: React.FC<TransactionsTableProps> = ({
  transactions,
  searchQuery,
  onClassifyTx,
}) => {
  const [filterAccount, setFilterAccount] = useState<string>('all');
  const [selectedTx, setSelectedTx] = useState<Transaction | null>(null);

  const categories = [
    { name: 'Salary', icon: '💰', direction: 'income' },
    { name: 'Rent & Housing', icon: '🏠', direction: 'expense' },
    { name: 'Groceries', icon: '🛒', direction: 'expense' },
    { name: 'Dining Out', icon: '🍽️', direction: 'expense' },
    { name: 'Utilities', icon: '⚡', direction: 'expense' },
    { name: 'Subscriptions', icon: '📱', direction: 'expense' },
    { name: 'Savings & Investments', icon: '📈', direction: 'transfer' },
  ];

  const filtered = transactions.filter((tx) => {
    const matchesSearch =
      tx.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
      tx.counterparty.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (tx.category_name && tx.category_name.toLowerCase().includes(searchQuery.toLowerCase()));

    const matchesAccount = filterAccount === 'all' || tx.account_id === filterAccount;

    return matchesSearch && matchesAccount;
  });

  return (
    <div className="cream-panel p-6 mb-8">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-6">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <ListFilter className="w-5 h-5 text-[#B8860B]" />
            <h2 className="text-xl font-bold text-[#1C160C] font-heading">Transactions Feed</h2>
          </div>
          <p className="text-xs text-[#6E5E4A]">
            Real-time classified bank transactions with auto-deduplication hash protection.
          </p>
        </div>

        {/* Account Filter */}
        <select
          value={filterAccount}
          onChange={(e) => setFilterAccount(e.target.value)}
          className="cream-input text-xs px-3 py-2 text-[#1C160C] font-semibold"
        >
          <option value="all">All Linked Accounts</option>
          <option value="acc-1">Sparkasse Girokonto</option>
          <option value="acc-2">DKB Cash & Depot</option>
          <option value="acc-3">N26 Smart</option>
        </select>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs text-[#362C1E]">
          <thead className="bg-[#FAF7F2] text-[#8C6D23] font-bold uppercase tracking-widest border-b border-[#E0D4C1]">
            <tr>
              <th className="py-3 px-4">Date</th>
              <th className="py-3 px-4">Account</th>
              <th className="py-3 px-4">Description / Counterparty</th>
              <th className="py-3 px-4">Category</th>
              <th className="py-3 px-4 text-right">Amount</th>
              <th className="py-3 px-4 text-center">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#E0D4C1]">
            {filtered.map((tx) => {
              const isIncome = tx.amount > 0;
              return (
                <tr key={tx.id} className="hover:bg-[#FAF5EC] transition">
                  <td className="py-3.5 px-4 font-mono text-[#6E5E4A] whitespace-nowrap">
                    {tx.transaction_date}
                  </td>

                  <td className="py-3.5 px-4 font-semibold text-[#1C160C] whitespace-nowrap">
                    {tx.account_name || 'Girokonto'}
                  </td>

                  <td className="py-3.5 px-4 max-w-xs">
                    <div className="font-bold text-[#1C160C] truncate">{tx.description}</div>
                    {tx.counterparty && <div className="text-[10px] text-[#7A6E5D] truncate">{tx.counterparty}</div>}
                  </td>

                  <td className="py-3.5 px-4 whitespace-nowrap">
                    {tx.category_name ? (
                      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-[#F4EFE6] border border-[#D5C7B0] text-[#362C1E] text-[11px] font-medium">
                        <span>{tx.category_icon || '🏷️'}</span>
                        <span>{tx.category_name}</span>
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 px-2.5 py-1 bg-[#FDF4F2] border border-[#F0D0CB] text-[#A34836] text-[11px] font-bold">
                        ⚠️ Uncategorized
                      </span>
                    )}
                  </td>

                  <td className="py-3.5 px-4 text-right whitespace-nowrap font-mono font-extrabold">
                    <span className={isIncome ? 'text-[#2D6A4F]' : 'text-[#1C160C]'}>
                      {isIncome ? '+' : ''}€{tx.amount.toLocaleString('de-DE', { minimumFractionDigits: 2 })}
                    </span>
                  </td>

                  <td className="py-3.5 px-4 text-center">
                    <button
                      onClick={() => setSelectedTx(tx)}
                      className="cream-button p-1.5 text-[#524330] hover:text-[#B8860B]"
                      title="Re-classify Category"
                    >
                      <Tag className="w-3.5 h-3.5" />
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Category Classification Modal */}
      {selectedTx && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-[#1C160C]/60 backdrop-blur-sm">
          <div className="cream-panel p-6 max-w-sm w-full border border-[#C5A059] bg-[#FFFFFF]">
            <h3 className="text-base font-bold text-[#1C160C] font-heading mb-2">Re-classify Transaction</h3>
            <p className="text-xs text-[#6E5E4A] mb-4">{selectedTx.description}</p>

            <div className="space-y-2 mb-6 max-h-60 overflow-y-auto pr-1">
              {categories.map((cat) => (
                <button
                  key={cat.name}
                  onClick={() => {
                    onClassifyTx(selectedTx.id, cat.name, cat.icon);
                    setSelectedTx(null);
                  }}
                  className="w-full flex items-center justify-between p-2.5 bg-[#FAF7F2] border border-[#E0D4C1] hover:border-[#C5A059] text-xs text-[#1C160C] transition font-medium"
                >
                  <span className="flex items-center gap-2">
                    <span>{cat.icon}</span>
                    <span>{cat.name}</span>
                  </span>
                  <span className="text-[10px] text-[#7A6E5D] uppercase tracking-wider">{cat.direction}</span>
                </button>
              ))}
            </div>

            <button
              onClick={() => setSelectedTx(null)}
              className="w-full cream-button text-xs font-semibold py-2"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

    </div>
  );
};
