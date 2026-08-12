import React, { useState, useEffect, useCallback } from 'react';
import type { Account } from '../types';
import { Building2, Shield, CheckCircle2, Lock, Plus, Smartphone, AlertCircle, Loader2, RefreshCw } from 'lucide-react';

const API_BASE = '/api';

interface BankingHubProps {
  accounts: Account[];
  onSyncBank: () => void;
  isSyncing: boolean;
}

interface BankAccount {
  id: string;
  name: string;
  iban: string | null;
  currency: string;
  current_balance: number;
}

export const BankingHub: React.FC<BankingHubProps> = () => {
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
      const resp = await fetch(`${API_BASE}/banking/accounts`);
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
      const resp = await fetch(`${API_BASE}/banking/connect`, {
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
      const resp = await fetch(`${API_BASE}/banking/tan`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          tan: tan || 'OK',
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
          <div className="flex items-center gap-2 mb-1">
            <Building2 className="w-5 h-5 text-[#B8860B]" />
            <h2 className="text-xl font-bold text-[#1C160C] font-heading">Bank Accounts & FinTS Connections</h2>
          </div>
          <p className="text-xs text-[#6E5E4A]">
            Secure bank synchronization via German FinTS/HBCI protocols with 2FA App Approval support (DKB, Sparkasse, Deutsche Bank, ING).
          </p>
        </div>

        <div className="flex gap-2">
          <button
            onClick={fetchAccounts}
            disabled={isLoadingAccounts}
            className="cream-button px-3 py-2 text-xs flex items-center gap-1.5"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoadingAccounts ? 'animate-spin' : ''}`} /> Refresh
          </button>
          <button
            onClick={() => setShowModal(true)}
            className="gold-button-primary px-4 py-2 text-xs flex items-center gap-1.5 shadow-sm"
          >
            <Plus className="w-4 h-4 text-[#E5C158]" /> Link New Bank Account
          </button>
        </div>
      </div>

      {/* Account Cards Grid */}
      {bankAccounts.length === 0 && !isLoadingAccounts && (
        <div className="p-8 text-center border border-dashed border-[#D5C7B0] bg-[#FAF7F2]">
          <Building2 className="w-10 h-10 text-[#C5A059] mx-auto mb-3 opacity-50" />
          <p className="text-sm text-[#6E5E4A] font-semibold mb-1">No bank accounts linked yet</p>
          <p className="text-xs text-[#9A8E7A]">Click "Link New Bank Account" to connect your DKB or other German bank via FinTS.</p>
        </div>
      )}

      {isLoadingAccounts && bankAccounts.length === 0 && (
        <div className="p-8 text-center">
          <Loader2 className="w-8 h-8 text-[#B8860B] mx-auto mb-2 animate-spin" />
          <p className="text-xs text-[#6E5E4A]">Loading accounts...</p>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {bankAccounts.map((acc) => (
          <div key={acc.id} className="bg-[#FAF7F2] p-5 border border-[#E0D4C1] hover:border-[#C5A059] transition relative overflow-hidden group">
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-semibold text-[#6E5E4A]">DKB / FinTS</span>
              <span className="w-2 h-2 bg-[#4CAF50]" title="Connected" />
            </div>

            <h3 className="text-sm font-bold text-[#1C160C] mb-1">{acc.name}</h3>
            <code className="text-[11px] font-mono text-[#7A6E5D] block mb-4">{acc.iban || 'No IBAN'}</code>

            <div className="flex items-baseline justify-between border-t border-[#E0D4C1] pt-3">
              <span className="text-xs text-[#6E5E4A]">Current Balance</span>
              <span className="text-lg font-extrabold text-[#B8860B] font-heading">
                €{acc.current_balance.toLocaleString('de-DE', { minimumFractionDigits: 2 })}
              </span>
            </div>
          </div>
        ))}
      </div>

      {/* FinTS Connection Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-[#1C160C]/60 backdrop-blur-sm">
          <div className="cream-panel p-6 max-w-md w-full border border-[#C5A059] shadow-2xl relative bg-[#FFFFFF]">
            
            <div className="flex items-center gap-2 mb-4">
              <Shield className="w-5 h-5 text-[#B8860B]" />
              <h3 className="text-lg font-bold text-[#1C160C] font-heading">Connect Bank via FinTS/HBCI</h3>
            </div>

            {/* Error message */}
            {errorMsg && (
              <div className="p-3 mb-4 bg-[#FFF3E0] border border-[#E0A030] text-xs text-[#7A4A00] flex items-start gap-2">
                <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
                <div>
                  <p className="font-bold mb-0.5">Connection Error</p>
                  <p>{errorMsg}</p>
                </div>
              </div>
            )}

            {/* Step 1: Credentials */}
            {!tanRequired && !syncDone && (
              <form onSubmit={handleConnectBank} className="space-y-4">
                <div>
                  <label className="text-xs text-[#4A3E2C] font-semibold block mb-1">Bankleitzahl (BLZ)</label>
                  <input
                    type="text"
                    value={blz}
                    onChange={(e) => setBlz(e.target.value)}
                    className="cream-input text-xs px-3 py-2 w-full font-mono"
                    placeholder="12030000"
                    required
                  />
                  <span className="text-[10px] text-[#B8860B] mt-1 block font-semibold">12030000 → DKB (Deutsche Kreditbank)</span>
                </div>

                <div>
                  <label className="text-xs text-[#4A3E2C] font-semibold block mb-1">Online Banking Username / Anmeldename</label>
                  <input
                    type="text"
                    placeholder="e.g. max.mustermann or Kontonummer"
                    value={login}
                    onChange={(e) => setLogin(e.target.value)}
                    className="cream-input text-xs px-3 py-2 w-full"
                    required
                  />
                </div>

                <div>
                  <label className="text-xs text-[#4A3E2C] font-semibold block mb-1">Banking PIN</label>
                  <input
                    type="password"
                    placeholder="••••••••"
                    value={pin}
                    onChange={(e) => setPin(e.target.value)}
                    className="cream-input text-xs px-3 py-2 w-full"
                    required
                  />
                  <span className="text-[10px] text-[#6E5E4A] mt-1 flex items-center gap-1">
                    <Lock className="w-3 h-3 text-[#B8860B]" /> Ephemeral in-memory handling; encrypted with Fernet 256.
                  </span>
                </div>

                <div className="flex items-center justify-end gap-2 pt-2">
                  <button
                    type="button"
                    onClick={resetModal}
                    className="cream-button text-xs font-semibold px-4 py-2"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={isConnecting}
                    className="gold-button-primary text-xs px-4 py-2 flex items-center gap-1.5"
                  >
                    {isConnecting ? (
                      <><Loader2 className="w-3.5 h-3.5 animate-spin" /> Connecting...</>
                    ) : (
                      'Connect & Authenticate'
                    )}
                  </button>
                </div>
              </form>
            )}

            {/* Step 2: TAN / App Approval */}
            {tanRequired && !syncDone && (
              <div className="space-y-4">
                <div className="p-3 bg-[#F7F3EB] border border-[#E5DEC9] text-xs text-[#7A602B]">
                  <p className="font-bold mb-1 flex items-center gap-1.5">
                    <Smartphone className="w-4 h-4 text-[#A38038]" /> 📲 Bank App Approval Required
                  </p>
                  <p className="whitespace-pre-line">{tanChallenge || 'Please approve the login request in your banking app on your phone.'}</p>
                  <div className="mt-2 pt-2 border-t border-[#E5DEC9]">
                    <p>1. Open your <strong>DKB App</strong> on your iPhone.<br />
                       2. Approve the incoming <strong>FinTS/HBCI login request</strong>.<br />
                       3. Enter the TAN below (or type <code className="bg-[#EDE7DA] px-1">OK</code> for Decoupled App Approval).
                    </p>
                  </div>
                </div>

                <div>
                  <label className="text-xs text-[#4A3E2C] font-semibold block mb-1">TAN Code / Decoupled Status</label>
                  <input
                    type="text"
                    placeholder="e.g. OK or 6-digit TAN code"
                    value={tan}
                    onChange={(e) => setTan(e.target.value)}
                    className="cream-input text-xs font-mono px-3 py-2 w-full text-[#7A602B]"
                  />
                </div>

                <div className="flex items-center justify-end gap-2 pt-2">
                  <button
                    type="button"
                    onClick={() => { setTanRequired(false); setErrorMsg(''); }}
                    className="cream-button text-xs font-semibold px-4 py-2"
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
                      <><Loader2 className="w-3.5 h-3.5 animate-spin" /> Verifying...</>
                    ) : (
                      'Verify & Sync Accounts'
                    )}
                  </button>
                </div>
              </div>
            )}

            {/* Step 3: Success */}
            {syncDone && (
              <div className="p-6 text-center space-y-3">
                <CheckCircle2 className="w-12 h-12 text-[#4CAF50] mx-auto" />
                <h4 className="text-base font-bold text-[#1C160C] font-heading">Bank Accounts Synced!</h4>
                <p className="text-xs text-[#6E5E4A]">
                  {accountsFound > 0
                    ? `Found and imported ${accountsFound} account${accountsFound > 1 ? 's' : ''}.`
                    : 'Connection established. Accounts are being processed.'}
                </p>
              </div>
            )}

          </div>
        </div>
      )}

    </div>
  );
};
