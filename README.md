```markdown
# Moune E-commerce

A Flask-based e-commerce platform with robust user authentication, admin management, bulk product uploads via CSV, and comprehensive logging.

## Features

- **User Authentication**
  - Customer registration and login
  - Admin login with role-based access

- **Admin Dashboard**
  - Manage products, categories, orders, inventory, and users
  - Bulk upload products using CSV files

- **Product Management**
  - Add, edit, delete products and categories
  - Assign inventory levels across multiple warehouses

- **Order Management**
  - View and update order statuses

- **User Management**
  - Manage admin users with different roles and permissions

- **Shopping Cart**
  - Add, update, and remove products from the cart
  - Checkout process (placeholder)

- **Logging**
  - Track significant events and model changes
  - Separate logs for main application and models

## Technologies Used

- **Backend:** Flask, SQLAlchemy
- **Frontend:** HTML, CSS (with Bootstrap optional)
- **Database:** SQLite (default) or PostgreSQL
- **Authentication:** Flask-Login, Werkzeug Security
- **Environment Management:** python-dotenv

## Installation

1. **Clone the Repository**

   ```bash
   git clone https://github.com/yourusername/moune_ecommerce.git
   cd moune_ecommerce
   ```

2. **Create a Virtual Environment**

   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Set Up Environment Variables**

   - **Install `python-dotenv`:**

     ```bash
     pip install python-dotenv
     ```

   - **Create a `.env` File:**

     In the project root directory, create a file named `.env`:

     ```bash
     touch .env
     ```

   - **Generate a Secret Key:**

     Create a script named `generate_secret_key.py`:

     ```python
     # generate_secret_key.py
     import secrets

     def generate_secret_key(length=32):
         return secrets.token_urlsafe(length)

     if __name__ == "__main__":
         secret_key = generate_secret_key()
         print(f"Your new secret key is:\n{secret_key}")
     ```

     Run the script to generate a secret key:

     ```bash
     python generate_secret_key.py
     ```

     Copy the generated key and add it to the `.env` file:

     ```env
     SECRET_KEY=your-generated-secret-key
     DATABASE_URL=sqlite:///app.db  # Or your preferred database URI
     ```

5. **Initialize the Database**

   ```bash
   flask db init
   flask db migrate -m "Initial migration."
   flask db upgrade
   ```

6. **Create a Super Admin User**

   ```bash
   flask create_super_admin
   ```

## Running the Application

Start the Flask development server:

```bash
flask run
```

Access the app at [http://localhost:5000](http://localhost:5000).

## Admin Bulk Upload

1. **Log in as Admin**

   Navigate to [http://localhost:5000/admin/login](http://localhost:5000/admin/login) and enter your admin credentials.

2. **Navigate to Bulk Upload**

   Click on "Bulk Upload Products via CSV" in the admin dashboard.

3. **Upload CSV File**

   - Click "Choose File" and select your CSV file.
   - Click "Upload" to add multiple products simultaneously.

   **CSV Format:**

   Ensure your CSV has the following headers:

   ```csv
   name,description,price,category
   ```

   **Example:**

   ```csv
   name,description,price,category
   Apple iPhone 14,Latest model smartphone with advanced features,999.99,Electronics
   Samsung Galaxy S22,High-end Android smartphone with sleek design,899.99,Electronics
   Dell XPS 13,Compact and powerful laptop for professionals,1199.99,Computers
   Sony WH-1000XM4,Noise-cancelling wireless headphones,349.99,Audio
   Instant Pot Duo,Multi-use pressure cooker for easy meals,89.99,Kitchen Appliances
   Nike Air Max 270,Comfortable and stylish sneakers,149.99,Footwear
   Levi's 501 Original Jeans,Classic straight fit denim jeans,59.99,Apparel
   Canon EOS Rebel T7,Beginner-friendly DSLR camera,449.99,Photography
   Fitbit Charge 5,Advanced fitness and health tracker,129.99,Wearables
   Kindle Paperwhite,Waterproof e-reader with high-resolution display,129.99,Electronics
   ```

## Logging

- **Main Logs:** `logs/moune_ecommerce.log`
- **Model Logs:** `logs/models.log`

Logs capture key events and changes for monitoring and debugging purposes.

## Contributing

Contributions are welcome! Please fork the repository and submit a pull request.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Contact

For any inquiries or support, please contact [your-email@example.com](mailto:your-email@example.com).

---
**Note:** Replace `yourusername`, `your-generated-secret-key`, and `your-email@example.com` with your actual GitHub username, generated secret key, and contact email respectively.
```
