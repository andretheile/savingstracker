import { useState } from 'react';
import { Header } from './components/Header';
import { MetricCards } from './components/MetricCards';
import { ProjectionSimulator } from './components/ProjectionSimulator';
import { KpiStudio } from './components/KpiStudio';
import { BalanceSheetView } from './components/BalanceSheetView';
import { BankingHub } from './components/BankingHub';
import { TransactionsTable } from './components/TransactionsTable';
import { TelegramStatusCard } from './components/TelegramStatusCard';

import {
  INITIAL_ACCOUNTS,
  INITIAL_KPIS,
  INITIAL_TRANSACTIONS,
  MOCK_BALANCE_SHEET,
} from './data/mockData';
import type { Account, KPISnapshot, Transaction } from './types';

export function App() {
  const [accounts] = useState<Account[]>(INITIAL_ACCOUNTS);
  const [kpis, setKpis] = useState<KPISnapshot[]>(INITIAL_KPIS);
  const [transactions, setTransactions] = useState<Transaction[]>(INITIAL_TRANSACTIONS);
  const [searchQuery, setSearchQuery] = useState('');
  const [isSyncing, setIsSyncing] = useState(false);
  const [activeTab, setActiveTab] = useState<'overview' | 'simulator' | 'kpis' | 'banking' | 'transactions'>('overview');

  const handleSyncBank = () => {
    setIsSyncing(true);
    setTimeout(() => {
      setIsSyncing(false);
    }, 2000);
  };

  const handleAddKpi = (newKpi: KPISnapshot) => {
    setKpis([newKpi, ...kpis]);
  };

  const handleClassifyTx = (txId: string, catName: string, catIcon: string) => {
    setTransactions(
      transactions.map((tx) =>
        tx.id === txId
          ? {
              ...tx,
              category_name: catName,
              category_icon: catIcon,
              is_manually_classified: true,
            }
          : tx
      )
    );
  };

  return (
    <div className="min-h-screen bg-[#F9F7F2] text-[#1A150E] flex flex-col font-sans relative">
      
      {/* Background ambient lighting */}
      <div className="ambient-glow-gold top-0 left-1/4" />

      {/* Header */}
      <Header
        onSyncBank={handleSyncBank}
        onOpenNewTx={() => setActiveTab('transactions')}
        onOpenNewKpi={() => setActiveTab('kpis')}
        searchQuery={searchQuery}
        setSearchQuery={setSearchQuery}
        isSyncing={isSyncing}
      />

      {/* Navigation Tabs */}
      <nav className="max-w-7xl mx-auto w-full px-6 pt-6">
        <div className="flex flex-wrap items-center gap-1.5 p-1.5 cream-panel w-fit border border-[#E5DEC9]">
          <button
            onClick={() => setActiveTab('overview')}
            className={`px-4 py-2 text-xs font-semibold uppercase tracking-wider transition ${
              activeTab === 'overview'
                ? 'bg-[#1A150E] text-[#F4E5C2] border border-[#C5A059]'
                : 'bg-[#F7F3EB] text-[#594E3F] hover:bg-[#EFEADF] hover:text-[#1A150E] border border-[#E5DEC9]'
            }`}
          >
            Overview & Balance
          </button>

          <button
            onClick={() => setActiveTab('simulator')}
            className={`px-4 py-2 text-xs font-semibold uppercase tracking-wider transition ${
              activeTab === 'simulator'
                ? 'bg-[#1A150E] text-[#F4E5C2] border border-[#C5A059]'
                : 'bg-[#F7F3EB] text-[#594E3F] hover:bg-[#EFEADF] hover:text-[#1A150E] border border-[#E5DEC9]'
            }`}
          >
            ⚜️ Savings Growth Simulator
          </button>

          <button
            onClick={() => setActiveTab('kpis')}
            className={`px-4 py-2 text-xs font-semibold uppercase tracking-wider transition ${
              activeTab === 'kpis'
                ? 'bg-[#1A150E] text-[#F4E5C2] border border-[#C5A059]'
                : 'bg-[#F7F3EB] text-[#594E3F] hover:bg-[#EFEADF] hover:text-[#1A150E] border border-[#E5DEC9]'
            }`}
          >
            📊 Custom KPI Studio
          </button>

          <button
            onClick={() => setActiveTab('banking')}
            className={`px-4 py-2 text-xs font-semibold uppercase tracking-wider transition ${
              activeTab === 'banking'
                ? 'bg-[#1A150E] text-[#F4E5C2] border border-[#C5A059]'
                : 'bg-[#F7F3EB] text-[#594E3F] hover:bg-[#EFEADF] hover:text-[#1A150E] border border-[#E5DEC9]'
            }`}
          >
            🏦 FinTS Bank Hub
          </button>

          <button
            onClick={() => setActiveTab('transactions')}
            className={`px-4 py-2 text-xs font-semibold uppercase tracking-wider transition ${
              activeTab === 'transactions'
                ? 'bg-[#1A150E] text-[#F4E5C2] border border-[#C5A059]'
                : 'bg-[#F7F3EB] text-[#594E3F] hover:bg-[#EFEADF] hover:text-[#1A150E] border border-[#E5DEC9]'
            }`}
          >
            💸 Transactions Feed
          </button>
        </div>
      </nav>

      {/* Main Content Area */}
      <main className="max-w-7xl mx-auto w-full px-6 py-6 flex-1">
        
        {/* Top Metric Cards */}
        <MetricCards
          kpis={kpis}
          totalIncome={MOCK_BALANCE_SHEET.total_income}
          totalExpense={MOCK_BALANCE_SHEET.total_expense}
          netCashflow={MOCK_BALANCE_SHEET.net_cashflow}
        />

        {/* Tab Views */}
        {activeTab === 'overview' && (
          <>
            <TelegramStatusCard />
            <BalanceSheetView balanceSheet={MOCK_BALANCE_SHEET} />
            <ProjectionSimulator />
          </>
        )}

        {activeTab === 'simulator' && <ProjectionSimulator />}

        {activeTab === 'kpis' && <KpiStudio kpis={kpis} onAddKpi={handleAddKpi} />}

        {activeTab === 'banking' && (
          <BankingHub accounts={accounts} onSyncBank={handleSyncBank} isSyncing={isSyncing} />
        )}

        {activeTab === 'transactions' && (
          <TransactionsTable
            transactions={transactions}
            searchQuery={searchQuery}
            onClassifyTx={handleClassifyTx}
          />
        )}

      </main>

      {/* Footer */}
      <footer className="border-t border-[#E5DEC9] py-6 text-center text-xs text-[#7A6E5D] bg-[#F9F7F2]">
        <p className="font-semibold uppercase tracking-widest text-[10px] text-[#A38038]">SavingsTracker v1.0 — Minimalist Financial Intelligence & Custom KPI Engine</p>
      </footer>
    </div>
  );
}

export default App;
