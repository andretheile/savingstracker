import React from 'react';
import { Send, CheckCircle2, Clock, BellRing } from 'lucide-react';

export const TelegramStatusCard: React.FC = () => {
  return (
    <div className="glass-panel p-6 rounded-3xl mb-8 relative overflow-hidden">
      <div className="ambient-glow-cyan -bottom-32 -left-32" />

      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
        
        <div className="flex items-start gap-4">
          <div className="w-12 h-12 rounded-2xl bg-indigo-500/10 border border-indigo-500/30 flex items-center justify-center text-indigo-400 shrink-0 shadow-lg shadow-indigo-500/10">
            <Send className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center gap-2 mb-1">
              <h3 className="text-lg font-bold text-white font-heading">Telegram Chatbot Interface</h3>
              <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 rounded-full">
                <CheckCircle2 className="w-3 h-3" /> Active & Connected
              </span>
            </div>
            <p className="text-xs text-slate-400 max-w-2xl">
              Celery Beat scheduler automatically generates and delivers your monthly balance sheet, KPI snapshots, and MSCI World compound growth report on the 1st of every month at 8:00 AM.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-4 bg-slate-900/60 p-3.5 rounded-2xl border border-slate-800 shrink-0">
          <div className="text-right">
            <span className="text-[10px] text-slate-500 uppercase tracking-wider block">Next Scheduled Digest</span>
            <span className="text-xs font-bold text-cyan-400 font-heading flex items-center gap-1 justify-end">
              <Clock className="w-3.5 h-3.5" /> September 1, 2026 @ 08:00
            </span>
          </div>
          <div className="w-9 h-9 rounded-xl bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-400">
            <BellRing className="w-4 h-4" />
          </div>
        </div>

      </div>
    </div>
  );
};
