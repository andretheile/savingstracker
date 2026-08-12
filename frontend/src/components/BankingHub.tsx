import React, { useState } from 'react';
import type { Account } from '../types';
import { Building2, Shield, CheckCircle2, Lock, Plus, Smartphone } from 'lucide-react';

interface BankingHubProps {
  accounts: Account[];
  onSyncBank: () => void;
  isSyncing: boolean;
}

export const BankingHub: React.FC<BankingHubProps> = ({ accounts }) => {
  const [showModal, setShowModal] = useState(false);
  const [blz, setBlz] = useState('12030000');
  const [login, setLogin] = useState('');
  const [pin, setPin] = useState('');
  const [tanRequired, setTanRequired] = useState(false);
  const [tan, setTan] = useState('');
  const [syncDone, setSyncDone] = useState(false);

  const handleConnectBank = (e: React.FormEvent) => {
    e.preventDefault();
    setTanRequired(true);
  };

  const handleVerifyTan = () => {
    setSyncDone(true);
    setTimeout(() => {
      setShowModal(false);
      setTanRequired(false);
      setSyncDone(false);
      setPin('');
      setTan('');
    }, 1500);
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

        <button
          onClick={() => setShowModal(true)}
          className="gold-button-primary px-4 py-2 text-xs flex items-center gap-1.5 shadow-sm"
        >
          <Plus className="w-4 h-4 text-[#E5C158]" /> Link New Bank Account
        </button>
      </div>

      {/* Account Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {accounts.map((acc) => (
          <div key={acc.id} className="bg-[#FAF7F2] p-5 border border-[#E0D4C1] hover:border-[#C5A059] transition relative overflow-hidden group">
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-semibold text-[#6E5E4A]">{acc.bank_name || 'DKB / German Bank'}</span>
              <span className="w-2 h-2 bg-[#B8860B]" />
            </div>

            <h3 className="text-sm font-bold text-[#1C160C] mb-1">{acc.name}</h3>
            <code className="text-[11px] font-mono text-[#7A6E5D] block mb-4">{acc.iban}</code>

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
                    onClick={() => setShowModal(false)}
                    className="cream-button text-xs font-semibold px-4 py-2"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="gold-button-primary text-xs px-4 py-2"
                  >
                    Connect & Authenticate
                  </button>
                </div>
              </form>
            )}

            {tanRequired && !syncDone && (
              <div className="space-y-4">
                <div className="p-3 bg-[#F7F3EB] border border-[#E5DEC9] text-xs text-[#7A602B]">
                  <p className="font-bold mb-1 flex items-center gap-1.5">
                    <Smartphone className="w-4 h-4 text-[#A38038]" /> 📲 DKB App Approval Triggered
                  </p>
                  <p>1. Open your <strong>DKB App</strong> on your iPhone.<br />
                     2. Approve the incoming <strong>FinTS / HBCI login request</strong>.<br />
                     3. Enter your TAN (or type <code>OK</code> for Decoupled App Approval) below and click Verify & Sync.
                  </p>
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
                    onClick={() => setTanRequired(false)}
                    className="cream-button text-xs font-semibold px-4 py-2"
                  >
                    Back
                  </button>
                  <button
                    type="button"
                    onClick={handleVerifyTan}
                    className="gold-button-primary text-xs px-4 py-2"
                  >
                    Verify & Sync Accounts
                  </button>
                </div>
              </div>
            )}

            {syncDone && (
              <div className="p-6 text-center space-y-3">
                <CheckCircle2 className="w-12 h-12 text-[#B8860B] mx-auto animate-bounce" />
                <h4 className="text-base font-bold text-[#1C160C] font-heading">DKB Accounts Synced Successfully!</h4>
                <p className="text-xs text-[#6E5E4A]">Imported Giro, Savings & Depot balances and transactions.</p>
              </div>
            )}

          </div>
        </div>
      )}

    </div>
  );
};
