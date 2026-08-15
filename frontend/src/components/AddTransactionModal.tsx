import { useState } from 'react';
import { Plus } from 'lucide-react';
import { fetchJson } from '../api';
import type { Account } from '../types';
import { SelectMenu } from './SelectMenu';

interface AddTransactionModalProps {
  userId: string;
  accounts: Account[];
  onClose: () => void;
  onCreated: () => void | Promise<void>;
}

function todayIso() {
  const now = new Date();
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
}

export const AddTransactionModal: React.FC<AddTransactionModalProps> = ({
  userId,
  accounts,
  onClose,
  onCreated,
}) => {
  const [accountId, setAccountId] = useState(accounts[0]?.id || '');
  const [txDate, setTxDate] = useState(todayIso());
  const [direction, setDirection] = useState<'expense' | 'income'>('expense');
  const [amount, setAmount] = useState('');
  const [description, setDescription] = useState('');
  const [counterparty, setCounterparty] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const value = Number(amount.replace(',', '.'));
    if (!accountId) {
      setError('Link a bank account first, then add a transaction.');
      return;
    }
    if (!description.trim()) {
      setError('Enter a description.');
      return;
    }
    if (!Number.isFinite(value) || value <= 0) {
      setError('Enter an amount greater than zero.');
      return;
    }
    setBusy(true);
    setError('');
    try {
      await fetchJson('/transactions/', {
        method: 'POST',
        body: JSON.stringify({
          user_id: userId,
          account_id: accountId,
          transaction_date: txDate,
          amount: direction === 'expense' ? -Math.abs(value) : Math.abs(value),
          description: description.trim(),
          counterparty: counterparty.trim(),
        }),
      });
      await onCreated();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not save transaction');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-[#1A1714]/40 backdrop-blur-[2px]">
      <div className="cream-panel p-6 max-w-md w-full relative bg-[#FFFFFF]">
        <div className="flex items-center gap-2 mb-4">
          <Plus className="w-4 h-4 text-[#8F7848]" strokeWidth={1.6} />
          <h3 className="text-base font-semibold text-[#1A1714] font-heading">Add transaction</h3>
        </div>
        {accounts.length === 0 ? (
          <p className="text-xs text-[#6B645A]">
            No accounts yet. Open Banking and link a bank, then you can add a transaction here.
          </p>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            {error && <p className="text-xs text-[#8C4A3A]">{error}</p>}
            <div>
              <label className="text-xs text-[#6B645A] font-medium block mb-1">Account</label>
              <SelectMenu
                aria-label="Account"
                value={accountId}
                onChange={setAccountId}
                className="w-full"
                options={accounts.map((acc) => ({ value: acc.id, label: acc.name }))}
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs text-[#6B645A] font-medium block mb-1">Date</label>
                <input
                  type="date"
                  value={txDate}
                  onChange={(e) => setTxDate(e.target.value)}
                  required
                  className="cream-input text-xs px-3 py-2 w-full"
                />
              </div>
              <div>
                <label className="text-xs text-[#6B645A] font-medium block mb-1">Type</label>
                <SelectMenu
                  aria-label="Type"
                  value={direction}
                  onChange={(value) => setDirection(value as 'expense' | 'income')}
                  className="w-full"
                  options={[
                    { value: 'expense', label: 'Expense' },
                    { value: 'income', label: 'Income' },
                  ]}
                />
              </div>
            </div>
            <div>
              <label className="text-xs text-[#6B645A] font-medium block mb-1">Amount (€)</label>
              <input
                type="number"
                min="0.01"
                step="0.01"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                required
                className="cream-input text-xs px-3 py-2 w-full"
              />
            </div>
            <div>
              <label className="text-xs text-[#6B645A] font-medium block mb-1">Description</label>
              <input
                type="text"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                required
                placeholder="REWE, rent, salary…"
                className="cream-input text-xs px-3 py-2 w-full"
              />
            </div>
            <div>
              <label className="text-xs text-[#6B645A] font-medium block mb-1">Counterparty (optional)</label>
              <input
                type="text"
                value={counterparty}
                onChange={(e) => setCounterparty(e.target.value)}
                className="cream-input text-xs px-3 py-2 w-full"
              />
            </div>
            <div className="flex justify-end gap-2 pt-1">
              <button type="button" onClick={onClose} className="cream-button text-xs font-medium px-4 py-2">
                Cancel
              </button>
              <button type="submit" disabled={busy} className="gold-button-primary text-xs px-4 py-2">
                {busy ? 'Saving…' : 'Save'}
              </button>
            </div>
          </form>
        )}
        {accounts.length === 0 && (
          <div className="flex justify-end gap-2 mt-4">
            <button type="button" onClick={onClose} className="cream-button text-xs font-medium px-4 py-2">
              Close
            </button>
          </div>
        )}
      </div>
    </div>
  );
};
