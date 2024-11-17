Moune E-commerce
A Flask-based e-commerce platform with robust user authentication, admin management, bulk product uploads via CSV, and comprehensive logging.

Features
User Authentication

Customer registration and login
Admin login with role-based access
Admin Dashboard

Manage products, categories, orders, inventory, and users
Bulk upload products using CSV files
Product Management

Add, edit, delete products and categories
Assign inventory levels across multiple warehouses
Order Management

View and update order statuses
User Management

Manage admin users with different roles and permissions
Shopping Cart

Add, update, and remove products from the cart
Checkout process (placeholder)
Logging

Track significant events and model changes
Separate logs for main application and models
Technologies Used
Backend: Flask, SQLAlchemy
Frontend: HTML, CSS (with Bootstrap optional)
Database: SQLite (default) or PostgreSQL
Authentication: Flask-Login, Werkzeug Security
Environment Management: python-dotenv
Installation
Clone the Repository

bash
Copy code
git clone https://github.com/yourusername/moune_ecommerce.git
cd moune_ecommerce
Create a Virtual Environment

bash
Copy code
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
Install Dependencies

bash
Copy code
pip install -r requirements.txt
Set Up Environment Variables

Install python-dotenv:

bash
Copy code
pip install python-dotenv
Create a .env File:

In the project root directory, create a file named .env:

bash
Copy code
touch .env
Generate a Secret Key:

Create a script named generate_secret_key.py:

python
Copy code
# generate_secret_key.py
import secrets

def generate_secret_key(length=32):
    return secrets.token_urlsafe(length)

if __name__ == "__main__":
    secret_key = generate_secret_key()
    print(f"Your new secret key is:\n{secret_key}")
Run the script to generate a secret key:

bash
Copy code
python generate_secret_key.py
Copy the generated key and add it to the .env file:

env
Copy code
SECRET_KEY=your-generated-secret-key
DATABASE_URL=sqlite:///app.db  # Or your preferred database URI
Initialize the Database

bash
Copy code
flask db init
flask db migrate -m "Initial migration."
flask db upgrade
Create a Super Admin User

bash
Copy code
flask create_super_admin
Running the Application
Start the Flask development server:

bash
Copy code
flask run
Access the app at http://localhost:5000.

Admin Bulk Upload
Log in as Admin

Navigate to http://localhost:5000/admin/login and enter your admin credentials.

Navigate to Bulk Upload

Click on "Bulk Upload Products via CSV" in the admin dashboard.

Upload CSV File

Click "Choose File" and select your CSV file.
Click "Upload" to add multiple products simultaneously.
CSV Format:

Ensure your CSV has the following headers:

csv
Copy code
name,description,price,category
Example:

csv
Copy code
name,description,price,category
Apple iPhone 14,Latest model smartphone with advanced features,999.99,Electronics
Samsung Galaxy S22,High-end Android smartphone with sleek design,899.99,Electronics
Dell XPS 13,Compact and powerful laptop for professionals,1199.99,Computers
Logging
Main Logs: logs/moune_ecommerce.log
Model Logs: logs/models.log
Logs capture key events and changes for monitoring and debugging purposes.

Contributing
Contributions are welcome! Please fork the repository and submit a pull request.

