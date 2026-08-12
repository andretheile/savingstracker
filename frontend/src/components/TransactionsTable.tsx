import React, { useMemo, useState } from 'react';
import type { Transaction } from '../types';
import { ArrowUpDown, ChevronDown, ChevronUp, Eye, EyeOff } from 'lucide-react';
import { CategoryIcon } from './CategoryIcon';
import { SelectMenu } from './SelectMenu';

interface TransactionsTableProps {
  transactions: Transaction[];
  accounts: { id: string; name: string }[];
  householdAccountIds?: string[];
  searchQuery: string;
  onClassifyTx: (txId: string, categoryName: string, categoryIcon: string) => void;
  onExcludeTx: (txId: string, exclude: boolean) => void;
}

const CATEGORIES = [
  { name: 'Salary', direction: 'income' },
  { name: 'Freelance', direction: 'income' },
  { name: 'Other Income', direction: 'income' },
  { name: 'Rent & Housing', direction: 'expense' },
  { name: 'Groceries', direction: 'expense' },
  { name: 'Transport', direction: 'expense' },
  { name: 'Dining Out', direction: 'expense' },
  { name: 'Travel & Vacation', direction: 'expense' },
  { name: 'Entertainment', direction: 'expense' },
  { name: 'Subscriptions', direction: 'expense' },
  { name: 'Sports & Fitness', direction: 'expense' },
  { name: 'Healthcare', direction: 'expense' },
  { name: 'Insurance', direction: 'expense' },
  { name: 'Utilities', direction: 'expense' },
  { name: 'Shopping', direction: 'expense' },
  { name: 'Education', direction: 'expense' },
  { name: 'Gifts & Donations', direction: 'expense' },
  { name: 'Taxes & Fees', direction: 'expense' },
  { name: 'Cash', direction: 'expense' },
  { name: 'Other Expense', direction: 'expense' },
  { name: 'Savings & Investments', direction: 'transfer' },
  { name: 'Internal Transfer', direction: 'transfer' },
];

type SortKey = 'date' | 'account' | 'description' | 'category' | 'amount';
type SortDir = 'asc' | 'desc';
type TypeFilter = 'all' | 'income' | 'expense' | 'transfer' | 'uncategorized' | 'excluded';

const SortHeader: React.FC<{
  label: string;
  column: SortKey;
  sortKey: SortKey;
  sortDir: SortDir;
  align?: 'left' | 'right';
  onSort: (key: SortKey) => void;
}> = ({ label, column, sortKey, sortDir, align = 'left', onSort }) => {
  const active = sortKey === column;
  return (
    <button
      type="button"
      onClick={() => onSort(column)}
      className={`inline-flex items-center gap-1 font-medium ${
        align === 'right' ? 'ml-auto' : ''
      } ${active ? 'text-[#1A1714]' : 'text-[#8A8278] hover:text-[#1A1714]'}`}
    >
      <span>{label}</span>
      {active ? (
        sortDir === 'asc' ? (
          <ChevronUp className="w-3 h-3" strokeWidth={1.8} />
        ) : (
          <ChevronDown className="w-3 h-3" strokeWidth={1.8} />
        )
      ) : (
        <ArrowUpDown className="w-3 h-3 opacity-40" strokeWidth={1.6} />
      )}
    </button>
  );
};

export const TransactionsTable: React.FC<TransactionsTableProps> = ({
  transactions,
  accounts,
  householdAccountIds = [],
  searchQuery,
  onClassifyTx,
  onExcludeTx,
}) => {
  const [filterAccount, setFilterAccount] = useState<string>('household');
  const [filterCategory, setFilterCategory] = useState<string>('all');
  const [filterType, setFilterType] = useState<TypeFilter>('all');
  const [sortKey, setSortKey] = useState<SortKey>('date');
  const [sortDir, setSortDir] = useState<SortDir>('desc');

  const categoryOptions = useMemo(() => {
    const names = new Set<string>();
    for (const tx of transactions) {
      if (tx.category_name) names.add(tx.category_name);
    }
    return [...names].sort((a, b) => a.localeCompare(b));
  }, [transactions]);

  const categorySelectOptions = useMemo(
    () => [
      { value: 'all', label: 'All categories' },
      { value: 'uncategorized', label: 'Uncategorized' },
      ...categoryOptions.map((name) => ({
        value: name,
        label: name,
        icon: <CategoryIcon name={name} className="w-3.5 h-3.5 text-[#8F7848]" />,
      })),
    ],
    [categoryOptions]
  );

  const classifyOptions = useMemo(
    () =>
      CATEGORIES.map((cat) => ({
        value: cat.name,
        label: cat.name,
        hint: cat.direction,
        icon: <CategoryIcon name={cat.name} className="w-3.5 h-3.5 text-[#8F7848]" />,
      })),
    []
  );

  const accountOptions = useMemo(
    () => [
      { value: 'household', label: 'Household accounts' },
      { value: 'all', label: 'All accounts' },
      ...accounts.map((acc) => ({ value: acc.id, label: acc.name })),
    ],
    [accounts]
  );

  const visible = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();

    const rows = transactions.filter((tx) => {
      const haystack = `${tx.description} ${tx.counterparty} ${tx.category_name ?? ''}`.toLowerCase();
      const matchesSearch = !q || haystack.includes(q);

      const matchesAccount =
        filterAccount === 'all' ||
        (filterAccount === 'household' && householdAccountIds.includes(tx.account_id)) ||
        tx.account_id === filterAccount;

      const matchesCategory =
        filterCategory === 'all' ||
        (filterCategory === 'uncategorized' && !tx.category_name) ||
        tx.category_name === filterCategory;

      const isTransfer = tx.category_direction === 'transfer';
      const matchesType =
        filterType === 'all' ||
        (filterType === 'income' && tx.amount > 0 && !isTransfer) ||
        (filterType === 'expense' && tx.amount < 0 && !isTransfer) ||
        (filterType === 'transfer' && isTransfer) ||
        (filterType === 'uncategorized' && !tx.category_name) ||
        (filterType === 'excluded' && Boolean(tx.exclude_from_totals));

      return matchesSearch && matchesAccount && matchesCategory && matchesType;
    });

    const sorted = [...rows].sort((a, b) => {
      let cmp = 0;
      switch (sortKey) {
        case 'date':
          cmp = a.transaction_date.localeCompare(b.transaction_date);
          break;
        case 'account':
          cmp = (a.account_name || '').localeCompare(b.account_name || '', undefined, { sensitivity: 'base' });
          break;
        case 'description':
          cmp = (a.description || a.counterparty || '').localeCompare(
            b.description || b.counterparty || '',
            undefined,
            { sensitivity: 'base' }
          );
          break;
        case 'category':
          cmp = (a.category_name || '').localeCompare(b.category_name || '', undefined, { sensitivity: 'base' });
          break;
        case 'amount':
          cmp = a.amount - b.amount;
          break;
      }
      if (cmp === 0) cmp = a.id.localeCompare(b.id);
      return sortDir === 'asc' ? cmp : -cmp;
    });

    return sorted;
  }, [transactions, searchQuery, filterAccount, filterCategory, filterType, householdAccountIds, sortKey, sortDir]);

  const filtersActive =
    filterAccount !== 'household' || filterCategory !== 'all' || filterType !== 'all';

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir((dir) => (dir === 'asc' ? 'desc' : 'asc'));
      return;
    }
    setSortKey(key);
    setSortDir(key === 'date' || key === 'amount' ? 'desc' : 'asc');
  };

  const resetFilters = () => {
    setFilterAccount('household');
    setFilterCategory('all');
    setFilterType('all');
  };

  return (
    <div className="cream-panel p-6 mb-8">
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-3 mb-4">
        <div>
          <h2 className="text-lg font-semibold text-[#1A1714] font-heading">Transactions</h2>
          <p className="text-xs text-[#6B645A] mt-0.5">
            Transfers between your accounts are ignored in totals. Flag one-offs to exclude them too.
          </p>
        </div>
        <p className="text-[11px] text-[#8A8278] tabular-nums shrink-0">
          {visible.length === transactions.length
            ? `${visible.length} transactions`
            : `${visible.length} of ${transactions.length}`}
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-2 mb-5">
        <SelectMenu
          aria-label="Filter by account"
          value={filterAccount}
          onChange={setFilterAccount}
          options={accountOptions}
          className="min-w-[10.5rem]"
        />
        <SelectMenu
          aria-label="Filter by type"
          value={filterType}
          onChange={(value) => setFilterType(value as TypeFilter)}
          options={[
            { value: 'all', label: 'All types' },
            { value: 'income', label: 'Income' },
            { value: 'expense', label: 'Expense' },
            { value: 'transfer', label: 'Transfer' },
            { value: 'uncategorized', label: 'Uncategorized' },
            { value: 'excluded', label: 'Excluded' },
          ]}
          className="min-w-[9rem]"
        />
        <SelectMenu
          aria-label="Filter by category"
          value={filterCategory}
          onChange={setFilterCategory}
          options={categorySelectOptions}
          className="min-w-[11rem]"
        />

        {filtersActive && (
          <button
            type="button"
            onClick={resetFilters}
            className="cream-button px-3 text-xs font-medium"
          >
            Reset
          </button>
        )}
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs text-[#1A1714]">
          <thead className="text-[#8A8278] font-medium border-b border-[#E5DFD4]">
            <tr>
              <th className="py-3 pr-4">
                <SortHeader label="Date" column="date" sortKey={sortKey} sortDir={sortDir} onSort={handleSort} />
              </th>
              <th className="py-3 px-4">
                <SortHeader label="Account" column="account" sortKey={sortKey} sortDir={sortDir} onSort={handleSort} />
              </th>
              <th className="py-3 px-4">
                <SortHeader label="Description" column="description" sortKey={sortKey} sortDir={sortDir} onSort={handleSort} />
              </th>
              <th className="py-3 px-4">
                <SortHeader label="Category" column="category" sortKey={sortKey} sortDir={sortDir} onSort={handleSort} />
              </th>
              <th className="py-3 px-4">
                <div className="flex justify-end">
                  <SortHeader label="Amount" column="amount" sortKey={sortKey} sortDir={sortDir} align="right" onSort={handleSort} />
                </div>
              </th>
              <th className="py-3 pl-4 text-right font-medium w-16" />
            </tr>
          </thead>
          <tbody className="divide-y divide-[#E5DFD4]">
            {visible.length === 0 ? (
              <tr>
                <td colSpan={6} className="py-8 text-center text-[#8A8278]">
                  {transactions.length === 0
                    ? 'No transactions imported yet.'
                    : 'No transactions match these filters.'}
                </td>
              </tr>
            ) : (
              visible.map((tx) => {
              const isIncome = tx.amount > 0;
              const skipped = Boolean(tx.exclude_from_totals) || tx.category_direction === 'transfer';
              return (
                <tr key={tx.id} className={`hover:bg-[#F3F0EA]/70 transition-colors ${skipped ? 'opacity-55' : ''}`}>
                  <td className="py-3.5 pr-4 font-mono text-[#6B645A] whitespace-nowrap tabular-nums">
                    {tx.transaction_date}
                  </td>

                  <td className="py-3.5 px-4 font-medium whitespace-nowrap">
                    {tx.account_name || 'Girokonto'}
                  </td>

                  <td className="py-3.5 px-4 max-w-xs">
                    <div className="font-medium truncate">{tx.description}</div>
                    {tx.counterparty && <div className="text-[10px] text-[#8A8278] truncate">{tx.counterparty}</div>}
                  </td>

                  <td className="py-3.5 px-4 whitespace-nowrap">
                    <SelectMenu
                      variant="inline"
                      aria-label="Set category"
                      value={tx.category_name || ''}
                      placeholder="Uncategorized"
                      options={classifyOptions}
                      onChange={(name) => onClassifyTx(tx.id, name, name)}
                    />
                    {tx.exclude_from_totals && (
                      <div className="text-[10px] text-[#8A8278] mt-0.5">Excluded from totals</div>
                    )}
                  </td>

                  <td className="py-3.5 px-4 text-right whitespace-nowrap font-mono tabular-nums font-medium">
                    <span className={skipped ? 'text-[#8A8278] line-through' : isIncome ? 'text-[#3D6B54]' : 'text-[#1A1714]'}>
                      {isIncome ? '+' : ''}€{tx.amount.toLocaleString('de-DE', { minimumFractionDigits: 2 })}
                    </span>
                  </td>

                  <td className="py-3.5 pl-4 text-right">
                    <button
                      onClick={() => onExcludeTx(tx.id, !tx.exclude_from_totals)}
                      className="cream-button p-1.5 text-[#6B645A] hover:text-[#1A1714]"
                      title={tx.exclude_from_totals ? 'Include in totals' : 'Exclude from totals'}
                    >
                      {tx.exclude_from_totals ? (
                        <EyeOff className="w-3.5 h-3.5" strokeWidth={1.6} />
                      ) : (
                        <Eye className="w-3.5 h-3.5" strokeWidth={1.6} />
                      )}
                    </button>
                  </td>
                </tr>
              );
            })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
