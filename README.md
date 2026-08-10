# customer-360-analytics
Customer 360 Analytics Platform — End-to-end e-commerce analytics using Python, SQL, PostgreSQL, Streamlit &amp; Plotly. Includes ETL, RFM segmentation, KPIs, sales, product, payment, delivery, Customer 360, Order 360 and Seller 360 analytics.
Customer 360 Analytics Platform

An end-to-end e-commerce analytics platform built with Python, PostgreSQL, SQL, Streamlit, Pandas, and Plotly. The project transforms raw Olist e-commerce data into actionable customer, product, seller, sales, payment, and delivery insights.

🚀 Features
ETL Pipeline — Data loading, validation, cleaning, and PostgreSQL ingestion
Executive KPIs — Revenue, orders, customers, average order value, and ratings
RFM Analysis — Recency, Frequency, and Monetary scoring
Customer Segmentation — Champions, Loyal Customers, Potential Loyalists, At Risk, Hibernating, and Needs Attention
Sales Analytics — Revenue trends and state-level performance
Product Analytics — Category revenue, items sold, and category performance
Payment Analytics — Payment methods, transaction values, and installments
Delivery Analytics — Delivery time, late-delivery rate, and state-level performance
Customer 360 — Customer-level profile and purchase history
Order 360 — Order, product, seller, payment, review, and delivery details
Seller 360 — Seller profile, orders, products, customers, and seller performance
Universal Search — Search using Customer ID, Order ID, Product ID, or Seller ID
Interactive Dashboard — Date, state, segment, and payment filters
🛠️ Tech Stack
Category	Technologies
Programming	Python
Database	PostgreSQL
Data Processing	Pandas
Analytics	SQL, RFM Analysis, KPI Analysis
Visualization	Plotly
Dashboard	Streamlit
Version Control	Git, GitLab
🏗️ Project Architecture
Raw Olist CSV Data
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
📊 Customer 360 Relationships
Customer
   │
   └── Order
        ├── Product
        ├── Seller
        ├── Payment
        └── Review

The dashboard allows users to drill down from a customer or directly search for an order, product, or seller and explore its connected entities.

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
⚙️ Setup
1. Clone the repository
git clone <your-gitlab-repository-url>
cd customer-360-analytics
2. Install dependencies
pip install -r requirements.txt
3. Configure PostgreSQL

Create a PostgreSQL database and configure the required database credentials using environment variables or Streamlit Secrets.

Never commit passwords, API keys, .env, or secrets.toml to GitLab.

4. Run the ETL pipeline
python main.py
5. Launch the dashboard
streamlit run dashboard/app.py
📈 Key Analytical Areas
RFM Segmentation

Customers are scored using:

Recency — How recently the customer purchased
Frequency — How frequently the customer purchased
Monetary — How much the customer spent

These scores are combined to classify customers into actionable segments.

Business Questions Answered
Which customer segments generate the most revenue?
Which products and categories perform best?
Which payment methods are most commonly used?
Which states have higher delivery times?
Which customers are at risk?
What orders belong to a particular customer?
Which products and sellers are associated with an order?
What customers and orders are connected to a seller?
🔐 Data & Security

This project uses the public Olist Brazilian E-Commerce dataset for analytics and demonstration purposes.

Sensitive credentials should be stored outside the repository using environment variables or deployment secrets.

👨‍💻 Author

Upendar

Built as an end-to-end data analytics and business intelligence portfolio project.
