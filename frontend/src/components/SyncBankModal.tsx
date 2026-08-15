import { Loader2, RefreshCw } from 'lucide-react';

export interface SyncResult {
  status: string;
  message?: string;
  bank?: string | null;
  connections?: SyncResult[];
}

interface SyncBankModalProps {
  result: SyncResult;
  confirming: boolean;
  onConfirm: () => void;
  onClose: () => void;
  onOpenBanking: () => void;
}

export function syncResultCopy(result: SyncResult): string {
  if (result.status === 'multi' && result.connections?.length) {
    return result.connections.map((row) => row.message || row.status).join('\n');
  }
  return result.message || result.status;
}

export const SyncBankModal: React.FC<SyncBankModalProps> = ({
  result,
  confirming,
  onConfirm,
  onClose,
  onOpenBanking,
}) => {
  const needsApproval = result.status === 'needs_approval';
  const needsBanking = result.status === 'no_connection' || result.status === 'missing_pin';
  const title = needsApproval ? 'Approve bank login' : 'Bank sync';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-[#1A1714]/40 backdrop-blur-[2px]">
      <div className="cream-panel p-6 max-w-md w-full relative bg-[#FFFFFF]">
        <div className="flex items-center gap-2 mb-4">
          <RefreshCw className="w-4 h-4 text-[#8F7848]" strokeWidth={1.6} />
          <h3 className="text-base font-semibold text-[#1A1714] font-heading">{title}</h3>
        </div>
        <p className="text-xs text-[#6B645A] whitespace-pre-wrap">{syncResultCopy(result)}</p>
        <div className="flex justify-end gap-2 mt-5">
          <button type="button" onClick={onClose} className="cream-button text-xs font-medium px-4 py-2">
            {needsApproval ? 'Later' : 'Close'}
          </button>
          {needsBanking && (
            <button type="button" onClick={onOpenBanking} className="gold-button-primary text-xs px-4 py-2">
              Open Banking
            </button>
          )}
          {needsApproval && (
            <button
              type="button"
              onClick={onConfirm}
              disabled={confirming}
              className="gold-button-primary text-xs px-4 py-2 inline-flex items-center gap-1.5"
            >
              {confirming ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : null}
              {confirming ? 'Importing…' : 'I approved it'}
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
