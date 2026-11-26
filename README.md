Customer 360 Analytics Platform

An end-to-end e-commerce analytics platform built with Python, SQL, PostgreSQL, Pandas, Streamlit, and Plotly. The project transforms raw Olist e-commerce data into actionable customer, sales, product, payment, delivery, and seller insights.

🚀 Features

ETL Pipeline — Data loading, validation, cleaning, and PostgreSQL ingestion

Executive KPIs — Revenue, orders, customers, average order value, and ratings

RFM Analysis — Recency, Frequency, and Monetary scoring

Customer Segmentation — Champions, Loyal Customers, Potential Loyalists, At Risk, Hibernating, and Needs Attention

Sales Analytics — Revenue trends and state-level performance

Product Analytics — Category revenue, items sold, and category performance

Payment Analytics — Payment methods, transaction values, and installments

Delivery Analytics — Delivery time, late-delivery rate, and state-level performance

Customer 360 — Customer profile, RFM metrics, and purchase history

Order 360 — Order, product, seller, payment, review, and delivery details

Seller 360 — Seller profile and related orders, products, and customers

Universal Search — Search using Customer ID, Order ID, Product ID, or Seller ID

Interactive Dashboard — Date, state, customer segment, and payment filters

🛠️ Tech Stack

Python | SQL | PostgreSQL | Pandas | Streamlit | Plotly | SQLAlchemy | Git | GitHub

🏗️ Project Architecture

Olist CSV Data
      ↓
Data Loader
      ↓
Data Validation
      ↓
Data Cleaning
      ↓
PostgreSQL
      ↓
SQL Views & RFM Analysis
      ↓
Streamlit Dashboard
      ↓
Business Insights

🔗 Entity Relationships

Customer
   │
   └── Order
        ├── Product
        ├── Seller
        ├── Payment
        └── Review

The platform connects these entities to provide detailed customer, order, product, and seller analysis.

📊 RFM Analysis

RFM analysis evaluates customer behavior using:

Recency — How recently a customer purchased

Frequency — How frequently a customer purchased

Monetary — How much a customer spent

Customers are scored and grouped into:

Champions

Loyal Customers

Potential Loyalists

At Risk

Hibernating

Needs Attention

📁 Project Structure

customer-360-analytics/
│
├── dashboard/
│   ├── app.py
│   └── pages/
│       └── customer_details.py
│
├── src/
│   ├── data_loader.py
│   ├── data_cleaning.py
│   ├── data_validation.py
│   ├── db_connection.py
│   └── postgres_loader.py
│
├── sql/
│   ├── 01_core_kpis.sql
│   ├── 02_segment_kpis.sql
│   └── ...
│
├── main.py
├── requirements.txt
├── README.md
└── .gitignore

⚙️ Local Setup

1. Clone the repository

git clone <YOUR_GITHUB_REPOSITORY_URL>
cd customer-360-analytics

2. Install dependencies

pip install -r requirements.txt

3. Configure PostgreSQL

Create a PostgreSQL database and configure the required database credentials using environment variables or Streamlit Secrets.

Do not commit passwords, API keys, .env, or secrets.toml to GitHub.

4. Run the ETL pipeline

python main.py

5. Launch the Streamlit dashboard

streamlit run dashboard/app.py

💡 Business Questions Answered

Which customer segments generate the most revenue?

Which customers are at risk?

Which product categories perform best?

Which payment methods are most commonly used?

Which states generate the most revenue?

Which states have higher delivery times?

What orders belong to a particular customer?

Which products and sellers are associated with an order?

What customers and orders are connected to a seller?

What is the purchasing behavior of a specific customer?

🔍 Customer 360 Search

The Customer Detail page supports entity-based exploration:

Customer ID
     ↓
Customer 360
     ↓
Orders → Products → Sellers → Payments → Reviews

Order ID
     ↓
Order 360
     ↓
Customer + Products + Seller + Payment + Review

Product ID
     ↓
Related Orders
     ↓
Customer + Seller + Payment + Review

Seller ID
     ↓
Seller 360
     ↓
Orders + Products + Customers

🔐 Data & Security

This project uses the public Olist Brazilian E-Commerce dataset for analytics and demonstration purposes.

Database credentials should be stored securely using environment variables during local development and deployment secrets when deployed.

🚀 Deployment

The dashboard is structured for deployment using Streamlit Community Cloud with a remotely accessible PostgreSQL database.

👨‍💻 Author

Upendar

Built as an end-to-end Data Analytics and Business Intelligence portfolio project.

---

## Customer 360 Platform Experience (New)

The repository now includes a platform entry point that separates the existing Olist demonstration from the planned business-data experience.

### Run the platform

```bash
streamlit run platform_app.py
```

The platform navigation provides:

- **Home** — choose between the Olist demo and business analytics.
- **Explore Olist Demo** — opens the existing Olist dashboard.
- **Customer 360 Explorer** — opens the existing entity-detail experience.
- **Analyze My Business** — introduces the business workspace and explains the planned onboarding flow.

### Run the original Olist dashboard directly

The original entry point remains available:

```bash
streamlit run dashboard/app.py
```

### Business workspace status

The business workspace is currently a foundation page only. It does not yet accept, store, or process company files. Authentication, team permissions, tenant isolation, validated CSV/Excel ingestion, and direct e-commerce integrations must be implemented and tested before real company data is used.

The Olist dataset remains the demonstration dataset. It is not presented as a live connection to a business.

## Business Workspace Persistence (Milestone 3)

The business-data experience now has a PostgreSQL-backed persistence layer in a dedicated `business_platform` schema. It is separate from the existing Olist tables and does not use the Olist full-refresh ETL loader.

### Workspace flow

1. Run `streamlit run platform_app.py`.
2. Open **Business analytics → Upload Business Data**.
3. Create an Individual or Company workspace.
4. Copy the generated workspace access key and keep it private.
5. Upload CSV or Excel datasets, map fields, preview and validate.
6. Save the approved dataset to PostgreSQL.
7. Open **My Business Dashboard** to view saved datasets and analytics.
8. On a later visit, reopen the workspace using its access key.

### Database requirements

The business workspace uses the same PostgreSQL connection variables as the existing project:

```env
DB_HOST=your-postgres-host
DB_PORT=5432
DB_NAME=your-database
DB_USER=your-database-user
DB_PASSWORD=your-database-password
```

The application creates the `business_platform` schema and its tables when the business workspace is opened. The equivalent SQL is available at `sql/schema/02_business_platform.sql`.

The database account needs permission to create schemas, tables, indexes, and insert/update/delete rows in the business schema. For production, prefer a dedicated database role with least-privilege grants rather than a superuser.

### Security and product limitations

- Workspace access currently uses a generated high-entropy bearer key. Anyone with that key can access the workspace. Treat it like a password.
- This is not full authentication: individual user accounts, team invitations, role-based access control, key rotation/recovery, audit logs, and production-grade tenant security are not implemented.
- Dataset rows are stored as JSONB records in PostgreSQL. Large-scale ingestion and query optimization are future work.
- Do not use regulated, highly sensitive, or production-critical data until security review, access controls, backups, retention/deletion workflows, and deployment secrets are configured.
- The Olist demo remains a separate, public sample-data experience.

### Original Olist ETL safety

The original `src/postgres_loader.py` performs a full refresh of the Olist tables. It must only be used for the Olist sample pipeline. Business workspace uploads use `src/business_storage.py` and must never call the Olist truncate-and-reload loader.

## Customer 360 Analytics Engine (Milestone 4)

The business dashboard now includes a reusable analytics engine in `src/business_analytics.py`. It calculates insights from normalized datasets saved in the active workspace, without reading or modifying the Olist demo tables.

### Available analytics

- Customer-level order frequency and first/last purchase dates.
- Historical observed customer revenue when Payments or Order items data is available.
- Repeat-customer count and repeat-purchase rate.
- RFM scoring and descriptive customer segments when order dates and revenue are available.
- Monthly order and customer trends.
- Cohort retention based on customers active in each month after their first purchase.
- A configurable inactivity flag (default 90 days) for operational review.
- Customer 360 result table and CSV exports.
- Standalone customer-master analytics without requiring Orders or Payments.
- Customer-only descriptive segments by signup-month cohort and profile completeness.
- Geographic customer summaries by city and country.
- Downloadable customer segment assignments; duplicate IDs remain visible in the source profile while segment counts use one representative record per valid ID.
- Customer-only segmentation is descriptive profile grouping, not behavioural or predictive segmentation. Purchase-behaviour segments require compatible order history.

### Metric definitions and limitations

- Revenue uses summed `Payments.payment_value` per order when available; otherwise it uses summed `Order items.price`. The currency is not inferred.
- Historical observed customer revenue is not predictive Customer Lifetime Value (CLV).
- The inactivity flag is a configurable recency rule, not a machine-learning churn prediction.
- RFM scores are relative quintile-style scores within the uploaded dataset; segment names are descriptive groupings, not universal customer labels.
- Cohort retention is the share of each first-purchase cohort with at least one order in each subsequent calendar month.
- Duplicate order IDs are reported as a limitation; the first row per order ID is used for order-level customer metrics.
- Missing required source fields disable the dependent metric rather than inventing values.

### Run analytics tests

```bash
pip install pytest
pytest -q
```

Tests for core business analytics are in `tests/test_business_analytics.py`.

The analytics dashboard remains a prototype. Review metric definitions, source data quality, workspace access controls and privacy/security requirements before using outputs for business-critical decisions.

## Universal E-commerce Data Translation (Architecture update)

The business upload centre now profiles files before mapping and translates user-confirmed fields into a fixed canonical e-commerce model. The existing Olist demo remains separate.

### Current implementation

- CSV and Excel workbook inspection, including listing and selecting multiple sheets.
- Header-row detection for exports with title/metadata rows above the column headers.
- Candidate trailing total/subtotal row detection and exclusion from the data preview.
- Per-column profiling: inferred type, null percentage, uniqueness, and sample values.
- Deterministic mapping suggestions using multilingual/alternate header aliases and value-pattern evidence.
- Human confirmation of mappings before import.
- Ambiguous date-format choice when dates can be interpreted day-first or month-first.
- Explicit source order-status assignment to canonical status categories.
- Amount normalization for common INR, BRL and plain numeric formats.
- Indian phone-number normalization while retaining identifiers as text.
- Original source columns retained as `source__*` fields after translation.
- Accepted and rejected rows saved separately, with rejection reasons.
- Confirmed mapping profiles saved per workspace and reused for matching sheet/table/header structures.

### Canonical e-commerce entities

Customers, Orders, Order items, Products, Payments and Reviews. A sheet is assigned to one canonical entity at a time. Multiple sheets in a workbook can be processed sequentially.

### Mapping confidence and LLM policy

Mapping confidence is a heuristic evidence score, not a statistical probability. Header aliases and content profiling provide local deterministic suggestions. The interface includes an explicit LLM opt-in control, but no external LLM provider is connected in this version; no uploaded data or samples are sent to an AI provider. A future provider integration must transmit only masked/minimized samples after consent and must never approve mappings automatically.

### Current limitations

- Multi-sheet workbooks are supported by selecting and processing each sheet sequentially; automatic relationship discovery across sheets is not yet implemented.
- Header-row and total-row detection are heuristic. Users must review the detected structure.
- Date parsing, status assignments, currency selection and mapping remain user-confirmed.
- Currency is recorded as a code but no FX conversion is performed.
- Rejected rows are retained as a separate workspace dataset; review and correction/re-import workflows can be expanded.
- The fixed model is for e-commerce. Other industries require separate canonical model packs.

### Tests

```bash
pip install pytest numpy pandas openpyxl
pytest -q tests/test_data_translation.py tests/test_business_analytics.py
```
