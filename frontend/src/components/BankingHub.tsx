import React, { useState, useEffect, useCallback } from 'react';
import type { Account } from '../types';
import { Building2, Shield, CheckCircle2, Lock, Plus, Smartphone, AlertCircle, Loader2, RefreshCw } from 'lucide-react';

const getApiBase = () => {
  if (typeof window !== 'undefined' && window.location.hostname === 'localhost' && window.location.port !== '8000') {
    return 'http://localhost:8000/api';
  }
  return '/api';
};

interface BankingHubProps {
  accounts: Account[];
  onSyncBank: () => void;
  isSyncing: boolean;
  onDataChanged?: () => void;
}

interface BankAccount {
  id: string;
  name: string;
  iban: string | null;
  currency: string;
  current_balance: number;
  include_in_household?: boolean;
}

export const BankingHub: React.FC<BankingHubProps> = ({ onDataChanged }) => {
  const [showModal, setShowModal] = useState(false);
  const [blz, setBlz] = useState('12030000');
  const [login, setLogin] = useState('');
  const [pin, setPin] = useState('');

  // Connection flow state
  const [isConnecting, setIsConnecting] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [tanRequired, setTanRequired] = useState(false);
  const [tanChallenge, setTanChallenge] = useState('');
  const [tan, setTan] = useState('');
  const [syncDone, setSyncDone] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  const [accountsFound, setAccountsFound] = useState(0);

  // Bank accounts from API
  const [bankAccounts, setBankAccounts] = useState<BankAccount[]>([]);
  const [isLoadingAccounts, setIsLoadingAccounts] = useState(false);

  const fetchAccounts = useCallback(async () => {
    setIsLoadingAccounts(true);
    try {
      const resp = await fetch(`${getApiBase()}/banking/accounts`);
      if (resp.ok) {
        const data = await resp.json();
        setBankAccounts(data);
      }
    } catch (e) {
      console.error('Failed to fetch accounts:', e);
    } finally {
      setIsLoadingAccounts(false);
    }
  }, []);

  useEffect(() => {
    fetchAccounts();
  }, [fetchAccounts]);

  const handleConnectBank = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsConnecting(true);
    setErrorMsg('');

    try {
      const resp = await fetch(`${getApiBase()}/banking/connect`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          bank_blz: blz,
          login_name: login,
          pin: pin,
          bank_name: blz === '12030000' ? 'DKB' : 'Bank',
          fints_url: '',
        }),
      });

      const result = await resp.json();

      if (!result.success) {
        setErrorMsg(result.error || 'Connection failed');
        setIsConnecting(false);
        return;
      }

      setSessionId(result.session_id);

      if (result.requires_tan) {
        setTanRequired(true);
        setTanChallenge(result.tan_challenge || 'Please approve the login in your DKB Banking App');
      } else {
        // No TAN needed — accounts already fetched
        setAccountsFound(result.accounts_found || 0);
        setSyncDone(true);
        await fetchAccounts();
        onDataChanged?.();
        setTimeout(() => resetModal(), 2500);
      }
    } catch (e) {
      setErrorMsg(`Network error: ${e}`);
    } finally {
      setIsConnecting(false);
    }
  };

  const handleVerifyTan = async () => {
    if (!sessionId) return;
    setIsConnecting(true);
    setErrorMsg('');

    try {
      const resp = await fetch(`${getApiBase()}/banking/tan`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          tan: tan,
        }),
      });

      const result = await resp.json();

      if (!result.success) {
        setErrorMsg(result.error || 'TAN verification failed');
        setIsConnecting(false);
        return;
      }

      setAccountsFound(result.accounts_found || 0);
      setSyncDone(true);
      await fetchAccounts();
      onDataChanged?.();
      setTimeout(() => resetModal(), 2500);
    } catch (e) {
      setErrorMsg(`Network error: ${e}`);
    } finally {
      setIsConnecting(false);
    }
  };

  const resetModal = () => {
    setShowModal(false);
    setTanRequired(false);
    setSyncDone(false);
    setSessionId(null);
    setPin('');
    setTan('');
    setErrorMsg('');
    setTanChallenge('');
    setAccountsFound(0);
  };

  return (
    <div className="cream-panel p-6 mb-8">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-6">
        <div>
          <h2 className="text-lg font-semibold text-[#1A1714] font-heading">Banking</h2>
          <p className="text-xs text-[#6B645A] mt-0.5">
            Savings rate uses household accounts only. Mark salary accounts as Personal so transfers into the household count as income.
          </p>
        </div>

        <div className="flex gap-2">
          <button
            onClick={fetchAccounts}
            disabled={isLoadingAccounts}
            className="cream-button px-3 text-xs flex items-center gap-1.5"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoadingAccounts ? 'animate-spin' : ''}`} strokeWidth={1.6} /> Refresh
          </button>
          <button
            onClick={() => setShowModal(true)}
            className="gold-button-primary px-3.5 text-xs flex items-center gap-1.5"
          >
            <Plus className="w-3.5 h-3.5" strokeWidth={1.6} /> Link account
          </button>
        </div>
      </div>

      {bankAccounts.length === 0 && !isLoadingAccounts && (
        <div className="p-10 text-center border border-[#E5DFD4] bg-[#F3F0EA]">
          <Building2 className="w-7 h-7 text-[#8A8278] mx-auto mb-3" strokeWidth={1.4} />
          <p className="text-sm text-[#1A1714] font-medium mb-1">No accounts linked</p>
          <p className="text-xs text-[#8A8278]">Connect a bank to import balances and transactions.</p>
        </div>
      )}

      {isLoadingAccounts && bankAccounts.length === 0 && (
        <div className="p-8 text-center">
          <Loader2 className="w-5 h-5 text-[#8A8278] mx-auto mb-2 animate-spin" />
          <p className="text-xs text-[#6B645A]">Loading accounts…</p>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        {bankAccounts.map((acc) => {
          const household = acc.include_in_household !== false;
          return (
          <div key={acc.id} className={`p-5 border ${household ? 'border-[#C4B49A]' : 'border-[#E5DFD4]'}`}>
            <div className="flex items-center justify-between mb-3">
              <span className="text-[11px] font-medium text-[#8A8278]">
                {household ? 'Household' : 'Personal'}
              </span>
              <span className="w-1.5 h-1.5 bg-[#3D6B54]" title="Connected" />
            </div>

            <h3 className="text-sm font-medium text-[#1A1714] mb-1">{acc.name}</h3>
            <code className="text-[11px] font-mono text-[#8A8278] block mb-4">{acc.iban || 'No IBAN'}</code>

            <div className="flex items-baseline justify-between border-t border-[#E5DFD4] pt-3">
              <span className="text-xs text-[#6B645A]">Balance</span>
              <span className="text-base font-semibold text-[#1A1714] font-heading tabular-nums">
                €{acc.current_balance.toLocaleString('de-DE', { minimumFractionDigits: 2 })}
              </span>
            </div>

            <button
              type="button"
              onClick={async () => {
                await fetch(`${getApiBase()}/accounts/${acc.id}/household`, {
                  method: 'PATCH',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({ include_in_household: !household }),
                });
                await fetchAccounts();
                onDataChanged?.();
              }}
              className="mt-3 w-full cream-button text-[11px] py-1.5"
            >
              {household ? 'Exclude from household totals' : 'Include in household totals'}
            </button>
          </div>
          );
        })}
      </div>

      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-[#1A1714]/40 backdrop-blur-[2px]">
          <div className="cream-panel p-6 max-w-md w-full relative bg-[#FFFFFF]">
            <div className="flex items-center gap-2 mb-4">
              <Shield className="w-4 h-4 text-[#8F7848]" strokeWidth={1.6} />
              <h3 className="text-base font-semibold text-[#1A1714] font-heading">Connect bank</h3>
            </div>

            {errorMsg && (
              <div className="p-3 mb-4 bg-[#FAF4F2] border border-[#E8D4CE] text-xs text-[#8C4A3A] flex items-start gap-2">
                <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0" strokeWidth={1.6} />
                <div>
                  <p className="font-medium mb-0.5">Connection failed</p>
                  <p>{errorMsg}</p>
                </div>
              </div>
            )}

            {!tanRequired && !syncDone && (
              <form onSubmit={handleConnectBank} className="space-y-4">
                <div>
                  <label className="text-xs text-[#6B645A] font-medium block mb-1">Bank code (BLZ)</label>
                  <input
                    type="text"
                    value={blz}
                    onChange={(e) => setBlz(e.target.value)}
                    className="cream-input text-xs px-3 py-2 w-full font-mono"
                    placeholder="12030000"
                    required
                  />
                  <span className="text-[10px] text-[#8A8278] mt-1 block">12030000 — DKB</span>
                </div>

                <div>
                  <label className="text-xs text-[#6B645A] font-medium block mb-1">Username</label>
                  <input
                    type="text"
                    placeholder="Online banking login"
                    value={login}
                    onChange={(e) => setLogin(e.target.value)}
                    className="cream-input text-xs px-3 py-2 w-full"
                    required
                  />
                </div>

                <div>
                  <label className="text-xs text-[#6B645A] font-medium block mb-1">PIN</label>
                  <input
                    type="password"
                    placeholder="••••••••"
                    value={pin}
                    onChange={(e) => setPin(e.target.value)}
                    className="cream-input text-xs px-3 py-2 w-full"
                    required
                  />
                  <span className="text-[10px] text-[#8A8278] mt-1.5 flex items-center gap-1">
                    <Lock className="w-3 h-3" strokeWidth={1.6} /> Held in memory only, encrypted in transit.
                  </span>
                </div>

                <div className="flex items-center justify-end gap-2 pt-2">
                  <button
                    type="button"
                    onClick={resetModal}
                    className="cream-button text-xs font-medium px-4 py-2"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={isConnecting}
                    className="gold-button-primary text-xs px-4 py-2 flex items-center gap-1.5"
                  >
                    {isConnecting ? (
                      <><Loader2 className="w-3.5 h-3.5 animate-spin" /> Connecting…</>
                    ) : (
                      'Connect'
                    )}
                  </button>
                </div>
              </form>
            )}

            {tanRequired && !syncDone && (
              <div className="space-y-4">
                <div className="p-3.5 bg-[#F3F0EA] border border-[#E5DFD4] text-xs text-[#6B645A]">
                  <p className="font-medium mb-1.5 flex items-center gap-1.5 text-[#1A1714]">
                    <Smartphone className="w-3.5 h-3.5" strokeWidth={1.6} /> App approval required
                  </p>
                  <p className="whitespace-pre-line">{tanChallenge || 'Approve the login request in your banking app.'}</p>
                  <div className="mt-2.5 pt-2.5 border-t border-[#E5DFD4] space-y-1">
                    <p>1. Open the DKB app</p>
                    <p>2. Approve the FinTS login request</p>
                    <p>3. Confirm here — the server waits up to two minutes</p>
                  </div>
                </div>

                <div>
                  <label className="text-xs text-[#6B645A] font-medium block mb-1">
                    TAN <span className="font-normal text-[#8A8278]">(chipTAN only — leave empty for app approval)</span>
                  </label>
                  <input
                    type="text"
                    placeholder="Optional"
                    value={tan}
                    onChange={(e) => setTan(e.target.value)}
                    className="cream-input text-xs font-mono px-3 py-2 w-full"
                  />
                </div>

                <div className="flex items-center justify-end gap-2 pt-2">
                  <button
                    type="button"
                    onClick={() => { setTanRequired(false); setErrorMsg(''); }}
                    className="cream-button text-xs font-medium px-4 py-2"
                  >
                    Back
                  </button>
                  <button
                    type="button"
                    onClick={handleVerifyTan}
                    disabled={isConnecting}
                    className="gold-button-primary text-xs px-4 py-2 flex items-center gap-1.5"
                  >
                    {isConnecting ? (
                      <><Loader2 className="w-3.5 h-3.5 animate-spin" /> Waiting…</>
                    ) : (
                      'Approved in app'
                    )}
                  </button>
                </div>
              </div>
            )}

            {syncDone && (
              <div className="py-6 text-center space-y-2">
                <CheckCircle2 className="w-8 h-8 text-[#3D6B54] mx-auto" strokeWidth={1.5} />
                <h4 className="text-sm font-semibold text-[#1A1714] font-heading">Accounts connected</h4>
                <p className="text-xs text-[#6B645A]">
                  {accountsFound > 0
                    ? `${accountsFound} account${accountsFound > 1 ? 's' : ''} imported.`
                    : 'Connection established.'}
                </p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
