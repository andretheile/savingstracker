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
    <div className="min-h-screen bg-[#080c14] text-slate-100 flex flex-col font-sans relative">
      
      {/* Background ambient lighting */}
      <div className="ambient-glow-cyan top-0 left-1/4" />
      <div className="ambient-glow-purple top-1/3 right-10" />

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
        <div className="flex items-center gap-2 p-1.5 rounded-2xl glass-panel w-fit border border-slate-800/80">
          <button
            onClick={() => setActiveTab('overview')}
            className={`px-4 py-2 rounded-xl text-xs font-semibold transition ${
              activeTab === 'overview'
                ? 'bg-gradient-to-r from-cyan-500 to-teal-500 text-slate-950 shadow-md shadow-cyan-500/20'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            Overview & Balance
          </button>

          <button
            onClick={() => setActiveTab('simulator')}
            className={`px-4 py-2 rounded-xl text-xs font-semibold transition ${
              activeTab === 'simulator'
                ? 'bg-gradient-to-r from-cyan-500 to-teal-500 text-slate-950 shadow-md shadow-cyan-500/20'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            🔮 Savings Growth Simulator
          </button>

          <button
            onClick={() => setActiveTab('kpis')}
            className={`px-4 py-2 rounded-xl text-xs font-semibold transition ${
              activeTab === 'kpis'
                ? 'bg-gradient-to-r from-cyan-500 to-teal-500 text-slate-950 shadow-md shadow-cyan-500/20'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            📊 Custom KPI Studio
          </button>

          <button
            onClick={() => setActiveTab('banking')}
            className={`px-4 py-2 rounded-xl text-xs font-semibold transition ${
              activeTab === 'banking'
                ? 'bg-gradient-to-r from-cyan-500 to-teal-500 text-slate-950 shadow-md shadow-cyan-500/20'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            🏦 FinTS Bank Hub
          </button>

          <button
            onClick={() => setActiveTab('transactions')}
            className={`px-4 py-2 rounded-xl text-xs font-semibold transition ${
              activeTab === 'transactions'
                ? 'bg-gradient-to-r from-cyan-500 to-teal-500 text-slate-950 shadow-md shadow-cyan-500/20'
                : 'text-slate-400 hover:text-white'
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
      <footer className="border-t border-slate-800/80 py-6 text-center text-xs text-slate-500">
        <p>SavingsTracker v1.0 — Modular Financial Intelligence & Custom KPI Engine</p>
      </footer>
    </div>
  );
}

export default App;
