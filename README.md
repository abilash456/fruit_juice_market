# Fruit Juice Market

A beginner-friendly MVC-style fruit juice shop built with Python 3.14, FastAPI,
SQLModel, SQLite, Jinja2, HTML, CSS and JavaScript.

## Features included
- Customer registration, login and logout (Argon2 password hashing)
- Product catalogue, search, category filtering and product details
- Session-based cart, quantity updates and checkout (Cash on Delivery)
- Customer order history and order status
- Wishlist
- Customer support ticket submission and history
- Admin dashboard, product creation and order status management
- Sample products seeded automatically on first run

## Requirements
- Python 3.14
- PyCharm (or another Python IDE)

## Run in PyCharm (Windows)
1. Extract the ZIP and open the `fruit_juice_market` folder in PyCharm.
2. Open **View > Tool Windows > Terminal**.
3. Create a virtual environment:
   `py -3.14 -m venv .venv`
4. Activate it:
   `.venv\\Scripts\\activate`
5. Upgrade pip:
   `python -m pip install --upgrade pip`
6. Install dependencies:
   `python -m pip install -r requirements.txt`
7. Start the server:
   `python -m uvicorn main:app --reload`
8. Open `http://127.0.0.1:8000` in Chrome.

If `py -3.14` is not recognised, create the virtual environment using the Python
3.14 interpreter selected in PyCharm instead.

## Demo admin
On first run, the app creates:
- Email: `admin@fruitjuice.local`
- Password: `Admin123!`

Change this password and set a strong SECRET_KEY before using the app outside
your local machine. The demo credentials are for local learning only.

## Important scope and production notes
This is a runnable learning/portfolio MVP, not a production payment platform.
Checkout supports Cash on Delivery only. UPI and payment gateway processing,
email-based password reset, image upload workflow, CSRF tokens, migrations,
advanced reporting and production deployment hardening still need to be added
before real-world use. Do not collect or store card details.
