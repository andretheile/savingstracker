import { useEffect, useState } from 'react';
import { UserPlus, X } from 'lucide-react';
import { fetchJson } from '../api';

interface Member {
  email: string;
  name: string;
  status: string;
  picture: string | null;
}

export const HouseholdMembersCard: React.FC = () => {
  const [members, setMembers] = useState<Member[]>([]);
  const [email, setEmail] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const refresh = async () => {
    const data = await fetchJson<Member[]>('/household/members');
    setMembers(data);
  };

  useEffect(() => {
    refresh().catch((err) => console.error('Failed to load household members', err));
  }, []);

  const handleInvite = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError('');
    try {
      await fetchJson('/household/invites', {
        method: 'POST',
        body: JSON.stringify({ email: email.trim() }),
      });
      setEmail('');
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not send invite');
    } finally {
      setBusy(false);
    }
  };

  const handleRemove = async (member: Member) => {
    setBusy(true);
    setError('');
    try {
      const path =
        member.status === 'pending'
          ? `/household/invites/${encodeURIComponent(member.email)}`
          : `/household/members/${encodeURIComponent(member.email)}`;
      await fetchJson(path, { method: 'DELETE' });
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not remove');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="cream-panel p-6 mb-8">
      <h3 className="text-lg font-semibold text-[#1A1714] font-heading">Household</h3>
      <p className="text-xs text-[#6B645A] mt-1">
        Invite a partner with Google so they share this dashboard. A new Google login without an
        invite creates a separate household.
      </p>
      {error && <p className="mt-3 text-xs text-[#8C4A3A]">{error}</p>}
      <ul className="mt-4 space-y-2">
        {members.map((member) => (
          <li
            key={`${member.status}:${member.email}`}
            className="flex items-center justify-between gap-3 text-xs text-[#1A1714]"
          >
            <div>
              <span className="font-medium">{member.email}</span>
              {member.name ? <span className="text-[#8A8278]"> · {member.name}</span> : null}
              <span className="ml-2 uppercase tracking-wide text-[10px] text-[#8A8278]">
                {member.status}
              </span>
            </div>
            <button
              type="button"
              onClick={() => handleRemove(member)}
              disabled={busy}
              className="cream-button h-7 w-7 px-0 text-[#8A8278]"
              aria-label={`Remove ${member.email}`}
            >
              <X className="w-3.5 h-3.5" strokeWidth={1.6} />
            </button>
          </li>
        ))}
      </ul>
      <form onSubmit={handleInvite} className="mt-4 flex flex-col sm:flex-row gap-2">
        <input
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="partner@gmail.com"
          required
          className="cream-input text-xs px-3 py-2 flex-1"
        />
        <button type="submit" disabled={busy} className="gold-button-primary text-xs px-4 py-2 inline-flex items-center gap-1.5">
          <UserPlus className="w-3.5 h-3.5" strokeWidth={1.6} />
          {busy ? 'Inviting…' : 'Invite'}
        </button>
      </form>
    </div>
  );
};
