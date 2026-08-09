# 📊 SavingsTracker — KPI Engine & Formula Specification

SavingsTracker features a **user-definable KPI Engine**. Instead of relying on static reporting dashboards, users can write pythonic math expressions to define metrics tailored to their spending habits.

Formulas are parsed safely into an Abstract Syntax Tree (AST) using `asteval`, eliminating the security risks of arbitrary `eval()`.

---

## 📐 Formula Syntax & Built-in Functions

Formulas support standard arithmetic operators (`+`, `-`, `*`, `/`, `**`, `%`) and registered helper functions:

| Function | Signature | Description |
|:--|:--|:--|
| `pct` | `pct(part, whole)` | Percentage calculation `(part / whole) * 100`. Returns `0.0` if `whole == 0`. |
| `change` | `change(current, previous)` | Percentage change `((current - previous) / previous) * 100`. |
| `abs` | `abs(x)` | Absolute value. |
| `min` | `min(a, b)` | Minimum of two values. |
| `max` | `max(a, b)` | Maximum of two values. |
| `round` | `round(x, n)` | Round number `x` to `n` decimal places. |

---

## 🔑 Available Formula Variables

When a KPI is evaluated for a given period (e.g. monthly), SavingsTracker computes transaction aggregates and injects them into the formula namespace:

### 1. General Financial Aggregates

| Variable Name | Type | Description |
|:--|:--|:--|
| `total_income` | `float` | Sum of all positive transactions in the period (€) |
| `total_expense` | `float` | Sum of all negative transactions in the period (absolute value €) |
| `net_cashflow` | `float` | `total_income - total_expense` (€) |
| `tx_count` | `int` | Total number of transactions in the period |
| `avg_expense` | `float` | Average expense per transaction (€) |
| `max_expense` | `float` | Largest single expense transaction (€) |
| `days_in_period` | `int` | Number of days in the period (e.g. 30, 31) |

### 2. Historical & Trend Variables (Month-over-Month)

| Variable Name | Type | Description |
|:--|:--|:--|
| `prev_total_income` | `float` | Previous period's total income (€) |
| `prev_total_expense` | `float` | Previous period's total expense (€) |
| `prev_net_cashflow` | `float` | Previous period's net cashflow (€) |

### 3. Category Aggregates

Categories are dynamically exposed as variables using snake_case naming conventions:
- `category_<category_name>_total`: Total spending for that category in the period (€)
- `category_<category_name>_count`: Number of transactions in that category

*Examples:*
- `category_groceries_total`
- `category_dining_out_total`
- `category_rent_and_housing_total`
- `category_subscriptions_total`

---

## 💡 Example KPI Formulas

### 1. Savings Rate (%)
```python
pct(net_cashflow, total_income)
```

### 2. Daily Burn Rate (€/day)
```python
total_expense / days_in_period
```

### 3. Groceries Share of Spending (%)
```python
pct(category_groceries_total, total_expense)
```

### 4. Combined Leisure Spending Ratio (%)
```python
pct(category_dining_out_total + category_entertainment_total, total_income)
```

### 5. Month-over-Month Expense Growth (%)
```python
change(total_expense, prev_total_expense)
```

### 6. Housing Concentration Ratio (%)
```python
pct(category_rent_and_housing_total, total_income)
```

---

## 🛡️ Creating KPIs via Telegram or REST API

### Via Telegram Chatbot:
```text
/newkpi Leisure_Share pct(category_dining_out_total + category_entertainment_total, total_expense)
```

### Via REST API (`POST /kpis/`):
```json
{
  "user_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "name": "Leisure Share",
  "description": "Dining out and entertainment as % of total spending",
  "formula": "pct(category_dining_out_total + category_entertainment_total, total_expense)",
  "unit": "%",
  "period": "monthly"
}
```

### Validating Formulas (`POST /kpis/validate`):
```json
{
  "formula": "pct(net_cashflow, total_income)"
}
```
*Response:*
```json
{
  "is_valid": true,
  "variables": ["net_cashflow", "total_income"],
  "errors": []
}
```
