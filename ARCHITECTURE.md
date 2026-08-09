# 📐 SavingsTracker — Architecture Specification

This document details the software design, database ER schema, data flow pipelines, and security architecture of SavingsTracker.

---

## 🏢 System Design & Layers

SavingsTracker is structured as a **modular domain-driven application** in Python 3.12. Each domain module (`accounts`, `banking`, `transactions`, `classification`, `kpis`, `projections`, `balance_sheets`, `users`, `scheduler`) encapsulates its own models, Pydantic schemas, business services, and API routers.

```
src/
├── core/                # Shared DB session, caching, security, base models
├── users/               # User identification & Telegram mapping
├── accounts/            # Bank account balance tracking
├── banking/             # FinTS/HBCI adapters & sync pipelines
├── transactions/        # Transaction storage, deduplication, filtering
├── classification/      # Category taxonomy & pattern-matching rule engine
├── kpis/                # Safe asteval formula evaluation & snapshot storage
├── projections/         # Compound interest growth math & scenario analysis
├── balance_sheets/      # Income vs Expense statement formatting
├── scheduler/           # Celery async tasks & monthly report builder
└── telegram_bot/        # python-telegram-bot conversational handlers
```

---

## 🗄️ Database ER Diagram

```mermaid
erDiagram
    users {
        uuid id PK
        bigint telegram_id UK
        varchar name
        varchar timezone "Europe/Berlin"
        jsonb preferences
        boolean is_active
        timestamp created_at
    }

    accounts {
        uuid id PK
        uuid user_id FK
        varchar name
        varchar iban
        varchar currency "EUR"
        numeric initial_balance
        boolean is_active
        timestamp created_at
    }

    bank_connections {
        uuid id PK
        uuid user_id FK
        varchar bank_blz
        varchar bank_name
        varchar fints_url
        varchar login_name "encrypted"
        varchar adapter_type "fints"
        timestamp last_synced_at
        varchar sync_status "idle | syncing | error"
        text last_error
        boolean is_active
        timestamp created_at
    }

    categories {
        uuid id PK
        uuid user_id FK "null = system default"
        uuid parent_id FK "self-reference"
        varchar name
        varchar icon
        varchar direction "income | expense | transfer"
        integer sort_order
    }

    classification_rules {
        uuid id PK
        uuid user_id FK
        uuid category_id FK
        varchar field "description | counterparty | amount"
        varchar operator "contains | equals | regex | gt | lt"
        varchar value
        integer priority
        boolean is_active
    }

    transactions {
        uuid id PK
        uuid account_id FK
        uuid category_id FK
        uuid bank_connection_id FK
        date transaction_date
        date value_date
        numeric amount "positive=income, negative=expense"
        text description
        varchar counterparty
        varchar reference
        varchar import_hash UK "SHA256 dedup"
        boolean is_manually_classified
    }

    kpi_definitions {
        uuid id PK
        uuid user_id FK "null = built-in"
        varchar name
        text description
        text formula "e.g. pct(net_cashflow, total_income)"
        varchar unit "% | €"
        varchar period "monthly"
        jsonb required_variables
        boolean is_active
    }

    kpi_snapshots {
        uuid id PK
        uuid kpi_id FK
        uuid user_id FK
        date period_start
        date period_end
        numeric value
        jsonb variable_values
        timestamp computed_at
    }

    projection_configs {
        uuid id PK
        uuid user_id FK
        varchar name
        numeric annual_return_pct "default 7.0 MSCI World"
        numeric inflation_pct "default 2.0"
        integer horizon_years "default 20"
        numeric monthly_contribution
        boolean use_actual_savings
        boolean is_active
    }

    projection_snapshots {
        uuid id PK
        uuid projection_id FK
        uuid user_id FK
        date computed_for_month
        numeric current_savings_rate
        numeric monthly_contribution
        numeric projected_value_nominal
        numeric projected_value_real "inflation-adjusted"
        jsonb scenarios
        timestamp computed_at
    }

    monthly_reports {
        uuid id PK
        uuid user_id FK
        date report_month
        jsonb report_data
        boolean sent_via_telegram
        timestamp sent_at
        timestamp computed_at
    }

    users ||--o{ accounts : "owns"
    users ||--o{ bank_connections : "configures"
    users ||--o{ categories : "custom"
    users ||--o{ classification_rules : "defines"
    users ||--o{ kpi_definitions : "custom"
    users ||--o{ projection_configs : "configures"
    accounts ||--o{ transactions : "contains"
    bank_connections ||--o{ transactions : "imported via"
    categories ||--o{ transactions : "classified as"
    categories ||--o{ classification_rules : "assigns to"
    categories ||--o{ categories : "parent/child"
    kpi_definitions ||--o{ kpi_snapshots : "computed from"
    projection_configs ||--o{ projection_snapshots : "computed from"
    users ||--o{ monthly_reports : "receives"
```

---

## 🔗 Bank Sync & Deduplication Pipeline

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant Bot as Telegram Bot / API
    participant BankSvc as Banking Service
    participant Adapter as FinTS Adapter
    participant Bank as German Bank (HBCI)
    participant Classifier as Rule Classifier
    participant DB as PostgreSQL DB

    User->>Bot: /connect (BLZ, Login, PIN)
    Bot->>BankSvc: initiate_sync()
    BankSvc->>Adapter: connect()
    Adapter->>Bank: FinTS Dialog Start
    alt TAN Required (2FA)
        Bank-->>Adapter: Challenge (pushTAN)
        Adapter-->>Bot: Challenge Prompt
        Bot-->>User: "Please approve in pushTAN app & send TAN"
        User->>Bot: 847293 (TAN)
        Bot->>Adapter: handle_tan(847293)
        Adapter->>Bank: Submit TAN
    end
    Adapter->>Bank: fetch_accounts() & fetch_transactions()
    Bank-->>Adapter: MT940 Transaction Data
    loop For Each Raw Transaction
        BankSvc->>BankSvc: Generate SHA256 import_hash
        alt Hash Exists in DB
            BankSvc->>BankSvc: Skip (Deduplicated)
        else New Transaction
            BankSvc->>Classifier: classify_transaction()
            Classifier-->>BankSvc: Assigned Category ID
            BankSvc->>DB: Save Transaction
        end
    end
    BankSvc-->>Bot: Sync Complete
    Bot-->>User: "✅ Imported X transactions"
```

---

## ⏰ Monthly Async Task Pipeline (Celery)

```mermaid
graph TD
    BEAT["Celery Beat Scheduler<br/>(1st of Month, 8:00 AM)"]
    REDIS[("Redis Task Queue")]
    MASTER["generate_all_monthly_reports Task"]
    WORKER1["Worker 1: User A Report"]
    WORKER2["Worker 2: User B Report"]
    SYNC["Sync Bank Transactions"]
    KPI["Compute KPI Snapshots"]
    BAL["Generate Balance Sheet"]
    PROJ["Calculate Growth Projections"]
    TG["Telegram API"]

    BEAT -->|Enqueue Master Job| REDIS
    REDIS --> MASTER
    MASTER -->|Fan-Out Per User| REDIS
    REDIS --> WORKER1 & WORKER2
    WORKER1 --> SYNC --> KPI --> BAL --> PROJ --> TG
```

---

## 🔒 Security Architecture

1. **At-Rest Encryption**: Sensitive bank login names and tokens are encrypted using **Fernet (AES-128 in CBC mode with HMAC)** before being written to PostgreSQL.
2. **Ephemeral PIN Handling**: Banking PINs are passed in-memory during sync calls and are never stored in the database. When entered via Telegram, the bot deletes the PIN message immediately.
3. **Safe Formula Parsing**: User-defined KPI formulas are evaluated using AST parsing (`asteval`), completely isolated from system builtins, standard library functions, or shell execution.
4. **Rate Limiting**: Bank sync operations are restricted to **1 sync per hour per connection** via Redis sliding window rate-limiters to prevent account locks or API spam.
