import React from 'react';
import { Send, CheckCircle2, Clock, BellRing } from 'lucide-react';

export const TelegramStatusCard: React.FC = () => {
  return (
    <div className="cream-panel p-6 mb-8 relative overflow-hidden">
      <div className="ambient-glow-gold -bottom-32 -left-32" />

      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
        
        <div className="flex items-start gap-4">
          <div className="w-12 h-12 bg-[#F4EFE6] border border-[#D5C7B0] flex items-center justify-center text-[#B8860B] shrink-0 shadow-sm">
            <Send className="w-6 h-6 text-[#B8860B]" />
          </div>
          <div>
            <div className="flex items-center gap-2 mb-1">
              <h3 className="text-lg font-bold text-[#1C160C] font-heading">Telegram Chatbot Interface</h3>
              <span className="inline-flex items-center gap-1 text-[10px] font-bold text-[#8C6D23] bg-[#F4EFE6] border border-[#D5C7B0] px-2 py-0.5 uppercase tracking-wider">
                <CheckCircle2 className="w-3 h-3 text-[#B8860B]" /> Active & Connected
              </span>
            </div>
            <p className="text-xs text-[#6E5E4A] max-w-2xl">
              Celery Beat scheduler automatically generates and delivers your monthly balance sheet, KPI snapshots, and MSCI World compound growth report on the 1st of every month at 8:00 AM.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-4 bg-[#FAF7F2] p-3.5 border border-[#E0D4C1] shrink-0">
          <div className="text-right">
            <span className="text-[10px] text-[#7A6E5D] uppercase tracking-widest block font-semibold">Next Scheduled Digest</span>
            <span className="text-xs font-bold text-[#B8860B] font-heading flex items-center gap-1 justify-end">
              <Clock className="w-3.5 h-3.5 text-[#B8860B]" /> September 1, 2026 @ 08:00
            </span>
          </div>
          <div className="w-9 h-9 bg-[#F4EFE6] border border-[#D5C7B0] flex items-center justify-center text-[#B8860B]">
            <BellRing className="w-4 h-4 text-[#B8860B]" />
          </div>
        </div>

      </div>
    </div>
  );
};
