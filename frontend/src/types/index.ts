export interface Account {
  id: string;
  name: string;
  iban?: string;
  currency: string;
  initial_balance: number;
  current_balance: number;
  bank_name?: string;
  is_active: boolean;
  include_in_household?: boolean;
}

export interface Category {
  id: string;
  name: string;
  icon: string;
  direction: 'income' | 'expense' | 'transfer';
  sort_order: number;
}

export interface Transaction {
  id: string;
  account_id: string;
  account_name?: string;
  category_id?: string;
  category_name?: string;
  category_icon?: string;
  transaction_date: string;
  amount: number;
  description: string;
  counterparty: string;
  reference: string;
  is_manually_classified: boolean;
  exclude_from_totals?: boolean;
  category_direction?: 'income' | 'expense' | 'transfer';
}

export interface KPISnapshot {
  id: string;
  kpi_id: string;
  name: string;
  formula: string;
  unit: string;
  value: number;
  trend?: number;
  description?: string;
}

export interface ScenarioResult {
  label: string;
  description: string;
  monthly_contribution: number;
  real_fv: number;
  nominal_fv: number;
  delta_vs_baseline_real: number;
}

export interface ProjectionData {
  current_balance: number;
  monthly_contribution: number;
  annual_return_pct: number;
  inflation_pct: number;
  horizon_years: number;
  projected_nominal: number;
  projected_real: number;
  total_contributed: number;
  total_growth: number;
  scenarios: ScenarioResult[];
}

export interface LineItem {
  category_name: string;
  icon: string;
  amount: number;
  percentage: number;
}

export interface BalanceSheetData {
  period_name: string;
  total_income: number;
  total_expense: number;
  net_cashflow: number;
  savings_rate_pct: number;
  income_items: LineItem[];
  expense_items: LineItem[];
  account_balances: Record<string, number>;
}
