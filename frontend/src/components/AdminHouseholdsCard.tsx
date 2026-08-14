import { useEffect, useState } from 'react';
import { Trash2 } from 'lucide-react';
import { fetchJson } from '../api';

interface Household {
  id: string;
  name: string;
  emails: string[];
  account_count: number;
  is_current: boolean;
}

export const AdminHouseholdsCard: React.FC = () => {
  const [households, setHouseholds] = useState<Household[]>([]);
  const [error, setError] = useState('');
  const [busyId, setBusyId] = useState<string | null>(null);

  const refresh = async () => {
    const data = await fetchJson<Household[]>('/admin/households');
    setHouseholds(data);
  };

  useEffect(() => {
    refresh().catch((err) => {
      setError(err instanceof Error ? err.message : 'Could not load households');
    });
  }, []);

  const handleDelete = async (household: Household) => {
    const label = household.emails.join(', ') || household.name;
    if (
      !window.confirm(
        `Delete household ${label}? Accounts, transactions, and logins for that household are removed. This cannot be undone.`,
      )
    ) {
      return;
    }
    setBusyId(household.id);
    setError('');
    try {
      await fetchJson(`/admin/households/${household.id}`, { method: 'DELETE' });
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not delete household');
    } finally {
      setBusyId(null);
    }
  };

  return (
    <div className="cream-panel p-6 mb-8">
      <h3 className="text-lg font-semibold text-[#1A1714] font-heading">Admin</h3>
      <p className="text-xs text-[#6B645A] mt-1">
        Other Google logins that created their own household. Delete extras so those emails can be
        invited into yours.
      </p>
      {error && <p className="mt-3 text-xs text-[#8C4A3A]">{error}</p>}
      <ul className="mt-4 space-y-2">
        {households.map((household) => (
          <li
            key={household.id}
            className="flex items-center justify-between gap-3 text-xs text-[#1A1714]"
          >
            <div>
              <span className="font-medium">
                {household.emails.join(', ') || household.name}
              </span>
              {household.emails.length > 0 && household.name ? (
                <span className="text-[#8A8278]"> · {household.name}</span>
              ) : null}
              <span className="ml-2 uppercase tracking-wide text-[10px] text-[#8A8278]">
                {household.account_count} accounts
                {household.is_current ? ' · yours' : ''}
              </span>
            </div>
            <button
              type="button"
              onClick={() => handleDelete(household)}
              disabled={household.is_current || busyId !== null}
              className="cream-button h-7 w-7 px-0 text-[#8A8278] disabled:opacity-40"
              aria-label={`Delete household ${household.emails.join(', ') || household.name}`}
            >
              <Trash2 className="w-3.5 h-3.5" strokeWidth={1.6} />
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
};
