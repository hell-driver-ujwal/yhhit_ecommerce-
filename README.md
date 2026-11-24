# Mini E-commerce REST API

A Django REST Framework backend for a marketplace. Sellers publish products, buyers check out their carts, and each seller fulfills their own orders. SQLite stores the data locally. Swagger UI lets you try the full workflow in a browser.

## Run locally

You need Git and Python 3.14. Run these commands in a terminal.

1. **Clone the repository and enter the project folder.**

   ```sh
   git clone https://github.com/hell-driver-ujwal/yhhit_ecommerce-.git marketplace-api
   cd marketplace-api
   ```

2. **Create and activate a virtual environment.**

   ```sh
   python3 -m venv .venv
   source .venv/bin/activate
   ```

   On Windows PowerShell, use `py -3.14 -m venv .venv` and then `.venv\Scripts\Activate.ps1`.

3. **Install the dependencies.**

   ```sh
   python -m pip install -r requirements.txt
   ```

4. **Create a local JWT signing key once.** Django uses this private file to sign login tokens. Git ignores it. You can also supply a persistent secret through the `JWT_SIGNING_KEY` environment variable.

   ```sh
   python -c "import secrets; from pathlib import Path; p = Path('.jwt-signing-key'); p.exists() or p.write_text(secrets.token_urlsafe(64))"
   ```

5. **Create the database and an administrator account.** Enter your preferred email and password when prompted.

   ```sh
   python manage.py migrate
   python manage.py createsuperuser
   ```

6. **Start the development server.** Leave this terminal running.

   ```sh
   python manage.py runserver
   ```

   Open [Swagger UI](http://127.0.0.1:8000/api/docs/) to try the API, [Django admin](http://127.0.0.1:8000/admin/) to manage categories, or the [OpenAPI schema](http://127.0.0.1:8000/api/schema/?format=json) for the machine-readable specification.

## Features

- **Accounts.** Register as a buyer or seller, log in with email and password, refresh JWTs, log out, and view or update your profile.
- **Catalog.** Anyone can browse products and categories. Product search matches text anywhere in the name or description and ignores case. Combine search with a category slug to narrow the results.
- **Seller inventory.** Sellers create products in admin-defined categories, list their own products, and edit or delete products they own.
- **Shopping cart.** Buyers add products, increase or decrease quantities, remove items, and view their own cart. The API checks stock and calculates a 2% tax.
- **Orders.** Checkout records prices, deducts stock, and clears the cart together. A mixed cart creates one order per seller. Buyers see their purchases and sellers see their sales.
- **Fulfillment.** Orders start as pending. The owning seller can move an order to processing and then completed. The purchasing buyer can cancel a pending or processing order, which restores stock.

## Try a purchase in Swagger

A fresh database starts with an empty catalog. Use **Try it out** and then **Execute** for each request.

1. In Django admin, add a category such as **Kitchenware** with slug `kitchenware`. Use the public category list to find its ID.
2. In Swagger, call `POST /accounts/api/register/` twice to create a seller and a buyer. Send `email`, `password`, `confirm_password`, and `user_type` (`seller` or `buyer`). Register both before logging in.
3. Call `POST /accounts/api/login/` with the seller's email and password. Copy `data.access` into Swagger's **Authorize** dialog under JWT. Create a product with `POST /products/api/products/`, using the category ID from step 1.

   ```json
   {"name": "Ceramic Mug", "description": "Blue stoneware", "price": 500, "stock": 8, "category": 1}
   ```

4. Try `GET /products/api/products/?search=stoneware&category=kitchenware`. Copy the product ID from the response.
5. Call `POST /accounts/api/logout/` with `{}`, then clear the seller token in **Authorize**. Log in as the buyer and authorize with the buyer's access token.
6. Call `POST /cart/api/items/` with `{"product": 1, "quantity": 2}`, substituting the product ID from step 4. Call `GET /cart/api/` to check the cart. Two units priced at 500 give a subtotal of 1,000 and a total of 1,020 including tax.
7. Call `POST /orders/api/` with an empty body to check out. Read the new order ID from `data.orders`. Use `GET /orders/api/` to view your history.

## Endpoint reference

| Operation | Method and path |
|---|---|
| Register, log in, log out | `POST /accounts/api/register/`, `POST /accounts/api/login/`, `POST /accounts/api/logout/` |
| Refresh access token | `POST /accounts/api/token/refresh/` |
| Read or edit profile | `GET`, `PATCH /accounts/api/profile/` |
| List or create categories | `GET`, `POST /products/api/category/` |
| Read, update, or delete a category | `GET`, `PUT`, `PATCH`, `DELETE /products/api/category/{id}/` |
| Search, list, or create products | `GET`, `POST /products/api/products/` |
| Read, update, or delete a product | `GET`, `PUT`, `PATCH`, `DELETE /products/api/products/{id}/` |
| List the signed-in seller's products | `GET /products/api/products/my-products/` |
| View cart or add items | `GET /cart/api/`, `POST /cart/api/items/` |
| Decrease quantity or remove item | `POST /cart/api/items/{id}/decrease/`, `DELETE /cart/api/items/{id}/` |
| Place an order or list history | `POST`, `GET /orders/api/` |
| View an order or change status | `GET /orders/api/{id}/`, `PATCH /orders/api/{id}/status/` |

For API clients, send the access token in `Authorization: Bearer <access-token>`. JSON responses put successful results in `data` and error details in `error`. HTTP 204 responses have an empty body. Swagger includes the request fields and response formats for each operation.
