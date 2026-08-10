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
