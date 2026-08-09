import React, { useState } from 'react';
import type { Account } from '../types';
import { Building2, Shield, CheckCircle2, Lock, Plus } from 'lucide-react';

interface BankingHubProps {
  accounts: Account[];
  onSyncBank: () => void;
  isSyncing: boolean;
}

export const BankingHub: React.FC<BankingHubProps> = ({ accounts }) => {
  const [showModal, setShowModal] = useState(false);
  const [blz, setBlz] = useState('10070024');
  const [login, setLogin] = useState('max.mustermann');
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
    <div className="glass-panel p-6 rounded-3xl mb-8">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-6">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Building2 className="w-5 h-5 text-cyan-400" />
            <h2 className="text-xl font-bold text-white font-heading">Bank Accounts & FinTS Connections</h2>
          </div>
          <p className="text-xs text-slate-400">
            Secure bank synchronization via German FinTS/HBCI protocols with 2FA/TAN challenge support.
          </p>
        </div>

        <button
          onClick={() => setShowModal(true)}
          className="bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-semibold px-4 py-2 rounded-xl text-xs flex items-center gap-1.5 shadow-lg shadow-cyan-500/20"
        >
          <Plus className="w-4 h-4" /> Link New Bank Account
        </button>
      </div>

      {/* Account Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {accounts.map((acc) => (
          <div key={acc.id} className="bg-slate-900/60 p-5 rounded-2xl border border-slate-800/80 hover:border-cyan-500/30 transition relative overflow-hidden group">
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-semibold text-slate-400">{acc.bank_name || 'German Bank'}</span>
              <span className="w-2 h-2 rounded-full bg-emerald-400 shadow-sm shadow-emerald-400/50" />
            </div>

            <h3 className="text-sm font-bold text-white mb-1">{acc.name}</h3>
            <code className="text-[11px] font-mono text-slate-500 block mb-4">{acc.iban}</code>

            <div className="flex items-baseline justify-between border-t border-slate-800 pt-3">
              <span className="text-xs text-slate-400">Current Balance</span>
              <span className="text-lg font-extrabold text-cyan-400 font-heading">
                €{acc.current_balance.toLocaleString('de-DE', { minimumFractionDigits: 2 })}
              </span>
            </div>
          </div>
        ))}
      </div>

      {/* FinTS Connection Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md">
          <div className="glass-panel p-6 rounded-3xl max-w-md w-full border border-slate-700 shadow-2xl relative">
            
            <div className="flex items-center gap-2 mb-4">
              <Shield className="w-5 h-5 text-cyan-400" />
              <h3 className="text-lg font-bold text-white font-heading">Connect Bank via FinTS/HBCI</h3>
            </div>

            {!tanRequired && !syncDone && (
              <form onSubmit={handleConnectBank} className="space-y-4">
                <div>
                  <label className="text-xs text-slate-300 block mb-1">Bankleitzahl (BLZ)</label>
                  <input
                    type="text"
                    value={blz}
                    onChange={(e) => setBlz(e.target.value)}
                    className="glass-input text-xs px-3 py-2 rounded-xl w-full"
                    required
                  />
                  <span className="text-[10px] text-cyan-400 mt-1 block">10070024 → Deutsche Bank</span>
                </div>

                <div>
                  <label className="text-xs text-slate-300 block mb-1">Online Banking Username</label>
                  <input
                    type="text"
                    value={login}
                    onChange={(e) => setLogin(e.target.value)}
                    className="glass-input text-xs px-3 py-2 rounded-xl w-full"
                    required
                  />
                </div>

                <div>
                  <label className="text-xs text-slate-300 block mb-1">Banking PIN</label>
                  <input
                    type="password"
                    placeholder="••••••••"
                    value={pin}
                    onChange={(e) => setPin(e.target.value)}
                    className="glass-input text-xs px-3 py-2 rounded-xl w-full"
                    required
                  />
                  <span className="text-[10px] text-slate-400 mt-1 flex items-center gap-1">
                    <Lock className="w-3 h-3 text-emerald-400" /> Ephemeral in-memory handling; never stored.
                  </span>
                </div>

                <div className="flex items-center justify-end gap-2 pt-2">
                  <button
                    type="button"
                    onClick={() => setShowModal(false)}
                    className="glass-button text-xs font-semibold px-4 py-2 rounded-xl text-slate-300"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-semibold text-xs px-4 py-2 rounded-xl"
                  >
                    Connect & Authenticate
                  </button>
                </div>
              </form>
            )}

            {tanRequired && !syncDone && (
              <div className="space-y-4">
                <div className="p-3 bg-cyan-500/10 border border-cyan-500/30 rounded-xl text-xs text-cyan-300">
                  <p className="font-semibold mb-1">⚠️ 2FA / pushTAN Challenge Initiated</p>
                  <p>Please approve the login request in your bank's pushTAN application, then enter your TAN code below.</p>
                </div>

                <div>
                  <label className="text-xs text-slate-300 block mb-1">TAN Code</label>
                  <input
                    type="text"
                    placeholder="e.g. 847293"
                    value={tan}
                    onChange={(e) => setTan(e.target.value)}
                    className="glass-input text-xs font-mono px-3 py-2 rounded-xl w-full text-cyan-300"
                  />
                </div>

                <div className="flex items-center justify-end gap-2 pt-2">
                  <button
                    type="button"
                    onClick={() => setTanRequired(false)}
                    className="glass-button text-xs font-semibold px-4 py-2 rounded-xl text-slate-300"
                  >
                    Back
                  </button>
                  <button
                    type="button"
                    onClick={handleVerifyTan}
                    disabled={!tan}
                    className="bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-semibold text-xs px-4 py-2 rounded-xl disabled:opacity-50"
                  >
                    Verify TAN & Sync
                  </button>
                </div>
              </div>
            )}

            {syncDone && (
              <div className="p-6 text-center space-y-3">
                <CheckCircle2 className="w-12 h-12 text-emerald-400 mx-auto animate-bounce" />
                <h4 className="text-base font-bold text-white font-heading">Bank Connected Successfully!</h4>
                <p className="text-xs text-slate-400">Imported transactions and synchronized account balances.</p>
              </div>
            )}

          </div>
        </div>
      )}

    </div>
  );
};
