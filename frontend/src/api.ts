import type { Account, BalanceSheetData, KPISnapshot, Transaction } from './types';

export function getApiBase() {
  if (typeof window !== 'undefined' && window.location.hostname === 'localhost' && window.location.port !== '8000') {
    return 'http://localhost:8000/api';
  }
  return '/api';
}

export function currentMonthRange() {
  const now = new Date();
  const y = now.getFullYear();
  const m = now.getMonth();
  const lastDay = new Date(y, m + 1, 0).getDate();
  const pad = (n: number) => String(n).padStart(2, '0');
  return {
    start: `${y}-${pad(m + 1)}-01`,
    end: `${y}-${pad(m + 1)}-${pad(lastDay)}`,
    label: new Date(y, m, 1).toLocaleString('en-GB', { month: 'long', year: 'numeric' }),
    days: lastDay,
  };
}

export async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(`${getApiBase()}${path}`, {
    ...init,
    credentials: 'include',
    headers: { 'Content-Type': 'application/json', ...(init?.headers || {}) },
  });
  if (resp.status === 401) {
    const err = new Error('Not authenticated');
    (err as Error & { status?: number }).status = 401;
    throw err;
  }
  if (!resp.ok) {
    let detail = `${resp.status} ${path}`;
    try {
      const body = (await resp.json()) as { detail?: unknown };
      if (typeof body.detail === 'string') detail = body.detail;
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  return resp.json();
}

export type ChatStreamEvent = {
  type: string;
  content?: string;
  name?: string;
  label?: string;
  arguments?: Record<string, unknown>;
  summary?: string;
  status?: string;
  detail?: string;
};

export async function streamChat(
  message: string,
  onEvent: (event: ChatStreamEvent) => void,
): Promise<void> {
  const resp = await fetch(`${getApiBase()}/llm/chat`, {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message }),
  });
  if (resp.status === 401) {
    const err = new Error('Not authenticated');
    (err as Error & { status?: number }).status = 401;
    throw err;
  }
  if (!resp.ok) {
    let detail = `${resp.status} /llm/chat`;
    try {
      const body = (await resp.json()) as { detail?: unknown };
      if (typeof body.detail === 'string') detail = body.detail;
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  if (!resp.body) {
    throw new Error('Chat stream was empty');
  }

  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const chunks = buffer.split('\n\n');
    buffer = chunks.pop() ?? '';
    for (const chunk of chunks) {
      const line = chunk.split('\n').find((row) => row.startsWith('data: '));
      if (!line) continue;
      try {
        onEvent(JSON.parse(line.slice(6)) as ChatStreamEvent);
      } catch {
        /* ignore malformed events */
      }
    }
  }
}

const num = (v: unknown) => Number(v ?? 0);

export async function loadDashboard() {
  const period = currentMonthRange();
  const me = await fetchJson<{ id: string }>('/users/me');

  const [bankAccounts, rawTxs, rawSheet, rawKpis] = await Promise.all([
    fetchJson<Array<{ id: string; name: string; iban: string | null; currency: string; current_balance: number; include_in_household?: boolean; is_depot?: boolean }>>(
      '/banking/accounts'
    ),
    fetchJson<Array<Record<string, unknown>>>(`/transactions/?limit=500`),
    fetchJson<Record<string, unknown>>(
      `/balance-sheets/${me.id}?period_start=${period.start}&period_end=${period.end}`
    ),
    fetchJson<KPISnapshot[]>(
      `/kpis/${me.id}?period_start=${period.start}&period_end=${period.end}`
    ).catch(() => [] as KPISnapshot[]),
  ]);

  const accounts: Account[] = bankAccounts.map((acc) => ({
    id: acc.id,
    name: acc.name,
    iban: acc.iban ?? undefined,
    currency: acc.currency,
    initial_balance: 0,
    current_balance: num(acc.current_balance),
    is_active: true,
    include_in_household: acc.include_in_household !== false,
    is_depot: acc.is_depot === true,
  }));

  const accountNameById = Object.fromEntries(accounts.map((a) => [a.id, a.name]));

  const transactions: Transaction[] = rawTxs.map((tx) => ({
    id: String(tx.id),
    account_id: String(tx.account_id),
    account_name: String(tx.account_name || accountNameById[String(tx.account_id)] || ''),
    category_id: tx.category_id ? String(tx.category_id) : undefined,
    category_name: tx.category_name ? String(tx.category_name) : undefined,
    category_icon: tx.category_icon ? String(tx.category_icon) : undefined,
    transaction_date: String(tx.transaction_date),
    amount: num(tx.amount),
    description: String(tx.description || ''),
    counterparty: String(tx.counterparty || ''),
    reference: String(tx.reference || ''),
    is_manually_classified: Boolean(tx.is_manually_classified),
    exclude_from_totals: Boolean(tx.exclude_from_totals),
    category_direction: tx.category_direction
      ? (String(tx.category_direction) as Transaction['category_direction'])
      : undefined,
  }));

  const totalIncome = num(rawSheet.total_income);
  const totalExpense = num(rawSheet.total_expense);
  const incomeItems = (rawSheet.income_items as Array<Record<string, unknown>> | undefined) ?? [];
  const expenseItems = (rawSheet.expense_items as Array<Record<string, unknown>> | undefined) ?? [];
  const rawBalances = (rawSheet.account_balances as Record<string, unknown> | undefined) ?? {};

  const balanceSheet: BalanceSheetData = {
    period_name: period.label,
    total_income: totalIncome,
    total_expense: totalExpense,
    net_cashflow: num(rawSheet.net_cashflow),
    savings_rate_pct: num(rawSheet.savings_rate_pct),
    income_items: incomeItems.map((item) => {
      const amount = num(item.amount);
      return {
        category_name: String(item.category_name || 'Uncategorized'),
        icon: String(item.icon || ''),
        amount,
        percentage: totalIncome > 0 ? (amount / totalIncome) * 100 : 0,
      };
    }),
    expense_items: expenseItems.map((item) => {
      const amount = num(item.amount);
      return {
        category_name: String(item.category_name || 'Uncategorized'),
        icon: String(item.icon || ''),
        amount,
        percentage: totalExpense > 0 ? (amount / totalExpense) * 100 : 0,
      };
    }),
    account_balances: Object.fromEntries(
      Object.entries(rawBalances).map(([name, bal]) => [name, num(bal)])
    ),
  };

  if (Object.keys(balanceSheet.account_balances).length === 0) {
    for (const acc of accounts) {
      balanceSheet.account_balances[acc.name] = acc.current_balance;
    }
  }

  return {
    userId: me.id,
    period,
    accounts,
    transactions,
    balanceSheet,
    kpis: rawKpis.map((k) => ({
      ...k,
      value: num(k.value),
    })),
  };
}
