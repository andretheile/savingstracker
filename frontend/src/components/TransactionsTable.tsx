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
    <div className="glass-panel p-6 rounded-3xl mb-8">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-6">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <ListFilter className="w-5 h-5 text-indigo-400" />
            <h2 className="text-xl font-bold text-white font-heading">Transactions Feed</h2>
          </div>
          <p className="text-xs text-slate-400">
            Real-time classified bank transactions with auto-deduplication hash protection.
          </p>
        </div>

        {/* Account Filter */}
        <select
          value={filterAccount}
          onChange={(e) => setFilterAccount(e.target.value)}
          className="glass-input text-xs px-3 py-2 rounded-xl text-slate-200"
        >
          <option value="all">All Linked Accounts</option>
          <option value="acc-1">Sparkasse Girokonto</option>
          <option value="acc-2">DKB Cash & Depot</option>
          <option value="acc-3">N26 Smart</option>
        </select>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs text-slate-300">
          <thead className="bg-slate-900/80 text-slate-400 font-semibold uppercase tracking-wider border-b border-slate-800">
            <tr>
              <th className="py-3 px-4">Date</th>
              <th className="py-3 px-4">Account</th>
              <th className="py-3 px-4">Description / Counterparty</th>
              <th className="py-3 px-4">Category</th>
              <th className="py-3 px-4 text-right">Amount</th>
              <th className="py-3 px-4 text-center">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60">
            {filtered.map((tx) => {
              const isIncome = tx.amount > 0;
              return (
                <tr key={tx.id} className="hover:bg-slate-900/40 transition">
                  <td className="py-3.5 px-4 font-mono text-slate-400 whitespace-nowrap">
                    {tx.transaction_date}
                  </td>

                  <td className="py-3.5 px-4 font-medium text-slate-300 whitespace-nowrap">
                    {tx.account_name || 'Girokonto'}
                  </td>

                  <td className="py-3.5 px-4 max-w-xs">
                    <div className="font-semibold text-slate-100 truncate">{tx.description}</div>
                    {tx.counterparty && <div className="text-[10px] text-slate-500 truncate">{tx.counterparty}</div>}
                  </td>

                  <td className="py-3.5 px-4 whitespace-nowrap">
                    {tx.category_name ? (
                      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-slate-800 border border-slate-700 text-slate-200 text-[11px]">
                        <span>{tx.category_icon || '🏷️'}</span>
                        <span>{tx.category_name}</span>
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-300 text-[11px]">
                        ⚠️ Uncategorized
                      </span>
                    )}
                  </td>

                  <td className="py-3.5 px-4 text-right whitespace-nowrap font-mono font-bold">
                    <span className={isIncome ? 'text-emerald-400' : 'text-slate-100'}>
                      {isIncome ? '+' : ''}€{tx.amount.toLocaleString('de-DE', { minimumFractionDigits: 2 })}
                    </span>
                  </td>

                  <td className="py-3.5 px-4 text-center">
                    <button
                      onClick={() => setSelectedTx(tx)}
                      className="glass-button p-1.5 rounded-lg text-slate-400 hover:text-cyan-400"
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
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md">
          <div className="glass-panel p-6 rounded-3xl max-w-sm w-full border border-slate-700">
            <h3 className="text-base font-bold text-white font-heading mb-2">Re-classify Transaction</h3>
            <p className="text-xs text-slate-400 mb-4">{selectedTx.description}</p>

            <div className="space-y-2 mb-6 max-h-60 overflow-y-auto pr-1">
              {categories.map((cat) => (
                <button
                  key={cat.name}
                  onClick={() => {
                    onClassifyTx(selectedTx.id, cat.name, cat.icon);
                    setSelectedTx(null);
                  }}
                  className="w-full flex items-center justify-between p-2.5 rounded-xl bg-slate-900/60 border border-slate-800 hover:border-cyan-500/40 text-xs text-slate-200 transition"
                >
                  <span className="flex items-center gap-2">
                    <span>{cat.icon}</span>
                    <span>{cat.name}</span>
                  </span>
                  <span className="text-[10px] text-slate-500 uppercase">{cat.direction}</span>
                </button>
              ))}
            </div>

            <button
              onClick={() => setSelectedTx(null)}
              className="w-full glass-button text-xs font-semibold py-2 rounded-xl text-slate-300"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

    </div>
  );
};
