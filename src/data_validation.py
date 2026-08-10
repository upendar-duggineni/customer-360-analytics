def validate_data(customers,
                  orders,
                  order_items,
                  payments,
                  reviews,
                  products):

    print("=" * 60)
    print("CUSTOMERS")
    print(customers.info())
    print(customers.isnull().sum())

    print("=" * 60)
    print("ORDERS")
    print(orders.info())
    print(orders.isnull().sum())

    print("=" * 60)
    print("ORDER ITEMS")
    print(order_items.info())
    print(order_items.isnull().sum())

    print("=" * 60)
    print("PAYMENTS")
    print(payments.info())
    print(payments.isnull().sum())

    print("=" * 60)
    print("REVIEWS")
    print(reviews.info())
    print(reviews.isnull().sum())

    print("=" * 60)
    print("PRODUCTS")
    print(products.info())
    print(products.isnull().sum())