import { useCallback, useEffect, useState } from 'react';
import { Header } from './components/Header';
import { MetricCards } from './components/MetricCards';
import { ProjectionSimulator } from './components/ProjectionSimulator';
import { KpiStudio } from './components/KpiStudio';
import { BalanceSheetView } from './components/BalanceSheetView';
import { BankingHub } from './components/BankingHub';
import { TransactionsTable } from './components/TransactionsTable';
import { TelegramStatusCard } from './components/TelegramStatusCard';
import { ChatView } from './components/ChatView';
import { HouseholdMembersCard } from './components/HouseholdMembersCard';
import { fetchJson, loadDashboard } from './api';
import type { Account, BalanceSheetData, KPISnapshot, Transaction } from './types';

const EMPTY_SHEET: BalanceSheetData = {
  period_name: '',
  total_income: 0,
  total_expense: 0,
  net_cashflow: 0,
  savings_rate_pct: 0,
  income_items: [],
  expense_items: [],
  account_balances: {},
};

const TABS = [
  { id: 'overview', label: 'Overview' },
  { id: 'chat', label: 'Chat' },
  { id: 'simulator', label: 'Projections' },
  { id: 'kpis', label: 'KPIs' },
  { id: 'banking', label: 'Banking' },
  { id: 'transactions', label: 'Transactions' },
] as const;

type TabId = (typeof TABS)[number]['id'] | 'settings';

function loginHref() {
  if (typeof window !== 'undefined' && window.location.hostname === 'localhost' && window.location.port !== '8000') {
    return 'http://localhost:8000/login';
  }
  return '/login';
}

function isUnauthorized(err: unknown) {
  return err instanceof Error && (err as Error & { status?: number }).status === 401;
}

export function App() {
  const [authEmail, setAuthEmail] = useState<string | null>(null);
  const [authReady, setAuthReady] = useState(false);
  const [userId, setUserId] = useState<string | null>(null);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [kpis, setKpis] = useState<KPISnapshot[]>([]);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [balanceSheet, setBalanceSheet] = useState<BalanceSheetData>(EMPTY_SHEET);
  const [periodDays, setPeriodDays] = useState(30);
  const [searchQuery, setSearchQuery] = useState('');
  const [isSyncing, setIsSyncing] = useState(false);
  const [activeTab, setActiveTab] = useState<TabId>('overview');

  const refresh = useCallback(async () => {
    const me = await fetchJson<{ email: string }>('/auth/me');
    setAuthEmail(me.email);
    const data = await loadDashboard();
    setUserId(data.userId);
    setAccounts(data.accounts);
    setTransactions(data.transactions);
    setBalanceSheet(data.balanceSheet);
    setKpis(data.kpis);
    setPeriodDays(data.period.days);
  }, []);

  useEffect(() => {
    refresh()
      .catch((err) => {
        if (isUnauthorized(err)) {
          setAuthEmail(null);
        } else {
          console.error('Failed to load dashboard', err);
        }
      })
      .finally(() => setAuthReady(true));
  }, [refresh]);

  const handleLogout = async () => {
    try {
      await fetchJson('/auth/logout', { method: 'POST' });
    } catch {
      /* still show the login screen */
    }
    setAuthEmail(null);
    setUserId(null);
  };

  const handleSyncBank = async () => {
    setIsSyncing(true);
    try {
      await refresh();
    } finally {
      setIsSyncing(false);
    }
  };

  const handleAddKpi = async (newKpi: KPISnapshot) => {
    if (!userId) return;
    await fetchJson('/kpis/', {
      method: 'POST',
      body: JSON.stringify({
        user_id: userId,
        name: newKpi.name,
        formula: newKpi.formula,
        unit: newKpi.unit,
        description: newKpi.description || '',
      }),
    });
    await refresh();
  };

  const handleExcludeTx = async (txId: string, exclude: boolean) => {
    setTransactions((prev) =>
      prev.map((tx) => (tx.id === txId ? { ...tx, exclude_from_totals: exclude } : tx))
    );
    try {
      await fetchJson(`/transactions/${txId}/exclude`, {
        method: 'PATCH',
        body: JSON.stringify({ exclude_from_totals: exclude }),
      });
      await refresh();
    } catch (err) {
      console.error('Failed to update exclude flag', err);
    }
  };

  const handleClassifyTx = async (txId: string, catName: string, catIcon: string) => {
    setTransactions((prev) =>
      prev.map((tx) =>
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
    try {
      await fetchJson(`/transactions/${txId}/category`, {
        method: 'PATCH',
        body: JSON.stringify({ category_name: catName }),
      });
      await refresh();
    } catch (err) {
      console.error('Failed to save category', err);
    }
  };

  const householdAccounts = accounts.filter((acc) => acc.include_in_household !== false);
  const totalBalance = householdAccounts.reduce((sum, acc) => sum + acc.current_balance, 0);
  const monthlyIncome = balanceSheet.total_income;
  const monthlySavings = Math.max(0, balanceSheet.net_cashflow);

  if (!authReady) {
    return (
      <div className="min-h-screen bg-[#F6F4EF] text-[#1A1714] flex items-center justify-center font-sans">
        <p className="text-xs text-[#8A8278]">Loading…</p>
      </div>
    );
  }

  if (!authEmail) {
    return (
      <div className="min-h-screen bg-[#F6F4EF] text-[#1A1714] flex items-center justify-center font-sans px-6">
        <div className="cream-panel max-w-md w-full p-8 text-center">
          <h1 className="text-xl font-semibold font-heading">SavingsTracker</h1>
          <p className="text-xs text-[#6B645A] mt-2">
            Sign in with Google to open your household dashboard. A new account starts empty;
            an invite from Settings joins an existing household.
          </p>
          <a href={loginHref()} className="gold-button-primary inline-flex mt-6 text-sm px-5 py-2.5">
            Continue with Google
          </a>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#F6F4EF] text-[#1A1714] flex flex-col font-sans">
      <div className="sticky top-0 z-40 bg-[#F6F4EF]/90 backdrop-blur-md border-b border-[#E5DFD4]">
        <div className="page-shell">
          <Header
            onSyncBank={handleSyncBank}
            onOpenNewTx={() => setActiveTab('transactions')}
            onOpenNewKpi={() => setActiveTab('kpis')}
            onOpenSettings={() => setActiveTab('settings')}
            onLogout={handleLogout}
            settingsActive={activeTab === 'settings'}
            searchQuery={searchQuery}
            setSearchQuery={setSearchQuery}
            isSyncing={isSyncing}
            userEmail={authEmail}
          />

          <nav className="nav-scroll flex items-center gap-7">
            {TABS.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`nav-tab ${activeTab === tab.id ? 'nav-tab-active' : ''}`}
              >
                {tab.label}
              </button>
            ))}
          </nav>
        </div>
      </div>

      <main className="page-shell py-8 flex-1">
        {activeTab !== 'chat' && activeTab !== 'settings' && (
          <MetricCards
            totalIncome={balanceSheet.total_income}
            totalExpense={balanceSheet.total_expense}
            netCashflow={balanceSheet.net_cashflow}
            daysInPeriod={periodDays}
          />
        )}

        {activeTab === 'overview' && (
          <>
            <BalanceSheetView balanceSheet={balanceSheet} />
            <ProjectionSimulator
              currentBalance={totalBalance}
              monthlyIncome={monthlyIncome}
              initialMonthlySavings={monthlySavings}
            />
          </>
        )}

        {activeTab === 'settings' && (
          <div>
            <div className="mb-5">
              <h2 className="text-lg font-semibold text-[#1A1714] font-heading">Settings</h2>
              <p className="text-xs text-[#6B645A] mt-0.5">
                Household members, Telegram bot, and OpenRouter key for this dashboard.
              </p>
            </div>
            <HouseholdMembersCard />
            <TelegramStatusCard />
          </div>
        )}

        {activeTab === 'chat' && (
          <ChatView onDataChanged={refresh} onOpenSettings={() => setActiveTab('settings')} />
        )}

        {activeTab === 'simulator' && (
          <ProjectionSimulator
            currentBalance={totalBalance}
            monthlyIncome={monthlyIncome}
            initialMonthlySavings={monthlySavings}
          />
        )}

        {activeTab === 'kpis' && userId && (
          <KpiStudio userId={userId} kpis={kpis} onAddKpi={handleAddKpi} />
        )}

        {activeTab === 'banking' && (
          <BankingHub accounts={accounts} onSyncBank={handleSyncBank} isSyncing={isSyncing} onDataChanged={refresh} />
        )}

        {activeTab === 'transactions' && (
          <TransactionsTable
            transactions={transactions}
            accounts={accounts}
            householdAccountIds={householdAccounts.map((acc) => acc.id)}
            searchQuery={searchQuery}
            onClassifyTx={handleClassifyTx}
            onExcludeTx={handleExcludeTx}
          />
        )}
      </main>

      <footer className="border-t border-[#E5DFD4] py-5 text-center text-[11px] text-[#8A8278]">
        SavingsTracker
      </footer>
    </div>
  );
}

export default App;
