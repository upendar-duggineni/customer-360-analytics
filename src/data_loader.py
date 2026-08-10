import pandas as pd

def load_data():

    customers = pd.read_csv("data/olist_customers_dataset.csv")

    orders = pd.read_csv("data/olist_orders_dataset.csv")

    order_items = pd.read_csv("data/olist_order_items_dataset.csv")

    payments = pd.read_csv("data/olist_order_payments_dataset.csv")

    reviews = pd.read_csv("data/olist_order_reviews_dataset.csv")

    products = pd.read_csv("data/olist_products_dataset.csv")

    sellers = pd.read_csv("data/olist_sellers_dataset.csv")

    geolocation = pd.read_csv("data/olist_geolocation_dataset.csv")

    category_translation = pd.read_csv("data/product_category_name_translation.csv")

    return (
        customers,
        orders,
        order_items,
        payments,
        reviews,
        products,
        sellers,
        geolocation,
        category_translation
    )