# app.py
from flask import Flask, render_template, redirect, url_for, flash, request, session
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from config import Config
from extensions import db
from models import User, Category, Product, Order, OrderItem, Cart, CartItem, Warehouse, Inventory
from forms import ProductForm, CategoryForm, RegistrationForm, LoginForm, UpdateCartForm, AdminUserForm

import os
import logging
from logging.handlers import RotatingFileHandler
from sqlalchemy import event

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)

# Initialize SQLAlchemy
db.init_app(app)

# Ensure the logs directory exists
if not os.path.exists('MouneEcommerce/Moune/logs'):
    os.mkdir('MouneEcommerce/Moune/logs')

# Configure Main Logger
main_logger = logging.getLogger('main_logger')
main_logger.setLevel(logging.INFO)

main_handler = RotatingFileHandler('MouneEcommerce/Moune/logs/moune_ecommerce.log', maxBytes=10240, backupCount=10)
main_formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s')
main_handler.setFormatter(main_formatter)
main_logger.addHandler(main_handler)

# Configure Model Logger
model_logger = logging.getLogger('model_logger')
model_logger.setLevel(logging.INFO)

model_handler = RotatingFileHandler('MouneEcommerce/Moune/logs/models.log', maxBytes=10240, backupCount=10)
model_formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s')
model_handler.setFormatter(model_formatter)
model_logger.addHandler(model_handler)

# Logging Functions for All Models
def log_model_insert(mapper, connection, target):
    model_logger.info(f'Inserted {target.__class__.__name__}: {target}')

def log_model_update(mapper, connection, target):
    model_logger.info(f'Updated {target.__class__.__name__}: {target}')

def log_model_delete(mapper, connection, target):
    model_logger.info(f'Deleted {target.__class__.__name__}: {target}')

# List of all models to attach logging
models = [User, Category, Product, Order, OrderItem, Cart, CartItem, Warehouse, Inventory]

# Attach Event Listeners to All Models
for model in models:
    event.listen(model, 'after_insert', log_model_insert)
    event.listen(model, 'after_update', log_model_update)
    event.listen(model, 'after_delete', log_model_delete)

# Roles for users
ROLE_PERMISSIONS = {
    'super_admin': ['manage_products', 'manage_orders', 'manage_inventory', 'manage_categories', 'manage_users'],
    'product_manager': ['manage_products'],
    'order_manager': ['manage_orders'],
    'inventory_manager': ['manage_inventory'],
    'category_manager': ['manage_categories'],
    'user_manager': ['manage_users'],
}

ADMIN_ROLES = [
    'super_admin',
    'product_manager',
    'order_manager',
    'inventory_manager',
    'category_manager',
    'user_manager'
]

# Decorators

def customer_login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('customer_logged_in'):
            flash('Please log in first.', 'danger')
            return redirect(url_for('customer_login'))
        return f(*args, **kwargs)
    return decorated_function

def permission_required(permission):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not session.get('admin_logged_in'):
                flash('Please log in as admin first.', 'danger')
                return redirect(url_for('admin_login'))
            user = User.query.get(session['user_id'])
            if not user:
                session.clear()
                flash('User not found.', 'danger')
                return redirect(url_for('admin_login'))
            user_roles = user.roles.split(',')
            user_permissions = set()
            for role in user_roles:
                user_permissions.update(ROLE_PERMISSIONS.get(role, []))
            if 'super_admin' in user_roles or permission in user_permissions:
                return f(*args, **kwargs)
            else:
                flash('You do not have permission to access this page.', 'danger')
                return redirect(url_for('admin_dashboard'))
        return decorated_function
    return decorator

def admin_login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if the admin is logged in
        if not session.get('admin_logged_in'):
            flash('Please log in as admin first.', 'danger')
            return redirect(url_for('admin_login'))
        
        # Retrieve the user ID from the session
        user_id = session.get('user_id')
        if not user_id:
            flash('User ID missing in session.', 'danger')
            return redirect(url_for('admin_login'))
        
        # Fetch the user from the database
        user = User.query.get(user_id)
        if not user:
            flash('User not found.', 'danger')
            return redirect(url_for('admin_login'))
        
        # Check if the user has any admin roles
        user_roles = user.roles.split(',')
        if not any(role in ADMIN_ROLES for role in user_roles):
            flash('Admin access required.', 'danger')
            return redirect(url_for('admin_login'))
        
        return f(*args, **kwargs)
    return decorated_function

def superadmin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = session.get('user_id')
        if not user_id:
            flash('Please log in first.', 'danger')
            return redirect(url_for('admin_login'))
        user = User.query.get(user_id)
        if not user or 'super_admin' not in user.roles.split(','):
            flash('Superadmin access required.', 'danger')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

# Routes

@app.route('/')
def home():
    return render_template('home.html')  # Ensure you have a home.html template

@app.route('/register', methods=['GET', 'POST'])
def customer_register():
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            email=form.email.data,
            roles='customer'  # Use 'roles' instead of 'role'
        )
        try:
            user.set_password(form.password.data)
        except ValueError as e:
            flash(str(e), 'danger')  # Display the error message to the user
            main_logger.debug(f'Registration failed for {user.username}: {str(e)}')
            return render_template('customer_register.html', form=form)
        
        db.session.add(user)
        db.session.commit()
        flash('Registration successful! You can now log in.', 'success')
        main_logger.info(f'New customer registered: {user.username}')
        return redirect(url_for('customer_login'))
    return render_template('customer_register.html', form=form)

# Customer Login Route
@app.route('/login', methods=['GET', 'POST'])
def customer_login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and 'customer' in user.roles.split(',') and user.check_password(form.password.data):
            session['user_id'] = user.id
            session['customer_logged_in'] = True
            session['customer_user'] = user.username
            flash('Logged in successfully!', 'success')
            return redirect(url_for('customer_dashboard'))
        else:
            flash('Invalid credentials.', 'danger')
    return render_template('customer_login.html', form=form)

# Admin Login Route
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data
        user = User.query.filter_by(email=email).first()
        if user:
            main_logger.debug(f'Admin login attempt for user: {user.username}, Roles: {user.roles}')
        else:
            main_logger.debug('Admin login attempt with invalid email.')
        
        user_roles = user.roles.split(',') if user else []
        is_admin = any(role in ADMIN_ROLES for role in user_roles)
        
        if user and user.check_password(password) and is_admin:
            session['user_id'] = user.id
            session['admin_logged_in'] = True
            session['admin_user'] = user.username
            flash('Logged in as admin.', 'success')
            main_logger.info(f'Admin {user.username} logged in successfully.')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid credentials or not authorized.', 'danger')
            main_logger.debug(f'Failed admin login attempt for email: {email}')
    return render_template('admin_login.html', form=form)

# Admin Logout Route
@app.route('/admin/logout')
def admin_logout():
    user_id = session.pop('user_id', None)
    admin_logged_in = session.pop('admin_logged_in', None)
    admin_user = session.pop('admin_user', None)
    
    if user_id:
        user = User.query.get(user_id)
        if user:
            main_logger.info(f'Admin {user.username} logged out.')
    
    flash('You have been logged out.', 'info')
    return redirect(url_for('home'))

# Customer Logout Route
@app.route('/customer/logout')
@customer_login_required
def customer_logout():
    session.pop('user_id', None)
    session.pop('customer_logged_in', None)
    session.pop('customer_user', None)
    
    flash('You have been logged out.', 'info')
    return redirect(url_for('customer_login'))

# Customer Dashboard
@app.route('/customer/dashboard')
@customer_login_required
def customer_dashboard():
    user = User.query.filter_by(username=session['customer_user']).first()
    if not user or 'customer' not in user.roles.split(','):
        flash('Access denied.', 'danger')
        return redirect(url_for('home'))
    return render_template('customer_dashboard.html', user=user)

# Admin Dashboard
@app.route('/admin/dashboard')
@admin_login_required
def admin_dashboard():
    user = User.query.get(session['user_id'])
    user_roles = user.roles.split(',')
    user_permissions = set()
    for role in user_roles:
        user_permissions.update(ROLE_PERMISSIONS.get(role, []))
    return render_template('admin_dashboard.html', username=user.username, roles=user_roles, permissions=user_permissions)

# Remove duplicate /logout route
# Commented out to avoid conflicts
# @app.route('/logout')
# @customer_login_required
# def customer_logout():
#     session.clear()
#     flash('You have been logged out.', 'info')
#     return redirect(url_for('customer_login'))

# Create Super Admin Route (should be removed after initial setup)
@app.route('/create_super_admin')
def create_super_admin():
    admin_email = 'admin@example.com'
    admin_username = 'admin'
    admin_password = 'Admin@123'  # Must meet password criteria

    admin_user = User.query.filter_by(email=admin_email).first()
    if not admin_user:
        admin_user = User(
            username=admin_username,
            email=admin_email,
            roles='super_admin'
        )
        try:
            admin_user.set_password(admin_password)
            db.session.add(admin_user)
            db.session.commit()
            flash('Super admin created successfully!', 'success')
            main_logger.info('Super admin user created.')
        except ValueError as e:
            flash(str(e), 'danger')
            main_logger.error(f'Failed to create super admin: {str(e)}')
    else:
        if 'super_admin' not in admin_user.roles.split(','):
            admin_user.roles += ',super_admin'
            try:
                admin_user.set_password(admin_password)
                db.session.commit()
                flash('Super admin role assigned and password updated successfully!', 'success')
                main_logger.info('Super admin role assigned and password updated.')
            except ValueError as e:
                flash(str(e), 'danger')
                main_logger.error(f'Failed to update super admin: {str(e)}')
        else:
            flash('Super admin already exists.', 'info')

    return redirect(url_for('admin_login'))

# View Logs Route
@app.route('/admin/view_logs')
@superadmin_required
def view_logs():
    try:
        with open('logs/models.log', 'r') as file:
            logs = file.read()
    except FileNotFoundError:
        logs = "No logs available."
    return render_template('view_logs.html', logs=logs)

# Admin Product Management Routes
@app.route('/admin/products')
@permission_required('manage_products')
def admin_products():
    products = Product.query.all()
    return render_template('admin_products.html', products=products)

@app.route('/admin/products/add', methods=['GET', 'POST'])
@permission_required('manage_products')
def admin_add_product():
    form = ProductForm()
    form.category_id.choices = [(c.id, c.name) for c in Category.query.order_by('name')]
    if form.validate_on_submit():
        product = Product(
            name=form.name.data,
            description=form.description.data,
            price=form.price.data,
            category_id=form.category_id.data
        )
        db.session.add(product)
        db.session.commit()
        
        flash('Product added successfully! Please assign inventory levels.', 'success')
        main_logger.info(f'Product added: {product.name} by Admin ID {session["user_id"]}')
        return redirect(url_for('admin_products'))
    return render_template('admin_product_form.html', form=form, action='Add')

@app.route('/admin/products/edit/<int:product_id>', methods=['GET', 'POST'])
@permission_required('manage_products')
def admin_edit_product(product_id):
    product = Product.query.get_or_404(product_id)
    form = ProductForm(obj=product)
    form.category_id.choices = [(c.id, c.name) for c in Category.query.order_by('name')]
    if form.validate_on_submit():
        form.populate_obj(product)
        db.session.commit()
        flash('Product updated successfully!', 'success')
        main_logger.info(f'Product updated: {product.name} by Admin ID {session["user_id"]}')
        return redirect(url_for('admin_products'))
    return render_template('admin_product_form.html', form=form, action='Edit')

@app.route('/admin/products/delete/<int:product_id>', methods=['POST'])
@permission_required('manage_products')
def admin_delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    db.session.delete(product)
    db.session.commit()
    flash('Product deleted successfully!', 'success')
    main_logger.info(f'Product deleted: {product.name} by Admin ID {session["user_id"]}')
    return redirect(url_for('admin_products'))

import csv
from io import TextIOWrapper
from forms import BulkUploadForm

@app.route('/admin/products/bulk_upload', methods=['GET', 'POST'])
@permission_required('manage_products')
def admin_bulk_upload():
    form = BulkUploadForm()
    if form.validate_on_submit():
        file = form.csv_file.data
        if not file:
            flash('No file uploaded.', 'danger')
            return redirect(request.url)
        
        try:
            stream = TextIOWrapper(file.stream, encoding='utf-8')
            csv_reader = csv.DictReader(stream)
            products_added = 0
            for row in csv_reader:
                # Expected CSV columns: name, description, price, category
                name = row.get('name')
                description = row.get('description')
                price = row.get('price')
                category_name = row.get('category')
                
                if not name or not description or not price or not category_name:
                    main_logger.warning(f'Skipping row with missing data: {row}')
                    continue
                
                try:
                    price = float(price)
                except ValueError:
                    main_logger.warning(f'Invalid price for product "{name}": {price}')
                    continue
                
                category = Category.query.filter_by(name=category_name).first()
                if not category:
                    # Optionally, create the category if it doesn't exist
                    category = Category(name=category_name)
                    db.session.add(category)
                    db.session.commit()
                    main_logger.info(f'Created new category "{category_name}"')
                
                # Check if the product already exists to avoid duplicates
                existing_product = Product.query.filter_by(name=name, category_id=category.id).first()
                if existing_product:
                    main_logger.warning(f'Product "{name}" in category "{category_name}" already exists. Skipping.')
                    continue
                
                product = Product(
                    name=name,
                    description=description,
                    price=price,
                    category_id=category.id
                )
                db.session.add(product)
                products_added += 1
            
            db.session.commit()
            flash(f'Successfully added {products_added} products.', 'success')
            main_logger.info(f'Bulk uploaded {products_added} products via CSV by Admin ID {session["user_id"]}')
            return redirect(url_for('admin_products'))
        
        except Exception as e:
            main_logger.error(f'Error processing CSV upload: {str(e)}')
            flash('An error occurred while processing the file.', 'danger')
            return redirect(request.url)
    
    return render_template('admin_bulk_upload.html', form=form)
# Admin Category Management Routes
@app.route('/admin/categories')
@permission_required('manage_categories')
def admin_categories():
    categories = Category.query.order_by('name').all()
    return render_template('admin_categories.html', categories=categories)

@app.route('/admin/categories/add', methods=['GET', 'POST'])
@permission_required('manage_categories')
def admin_add_category():
    form = CategoryForm()
    form.parent_id.choices = [(0, 'None')] + [(c.id, c.name) for c in Category.query.order_by('name')]
    if form.validate_on_submit():
        parent_id = form.parent_id.data if form.parent_id.data != 0 else None
        category = Category(
            name=form.name.data,
            parent_id=parent_id
        )
        db.session.add(category)
        db.session.commit()
        flash('Category added successfully!', 'success')
        main_logger.info(f'Category added: {category.name} by Admin ID {session["user_id"]}')
        return redirect(url_for('admin_categories'))
    return render_template('admin_category_form.html', form=form, action='Add')

@app.route('/admin/categories/edit/<int:category_id>', methods=['GET', 'POST'])
@permission_required('manage_categories')
def admin_edit_category(category_id):
    category = Category.query.get_or_404(category_id)
    form = CategoryForm(obj=category)
    form.parent_id.choices = [(0, 'None')] + [(c.id, c.name) for c in Category.query.order_by('name') if c.id != category.id]
    if form.validate_on_submit():
        category.name = form.name.data
        category.parent_id = form.parent_id.data if form.parent_id.data != 0 else None
        db.session.commit()
        flash('Category updated successfully!', 'success')
        main_logger.info(f'Category updated: {category.name} by Admin ID {session["user_id"]}')
        return redirect(url_for('admin_categories'))
    return render_template('admin_category_form.html', form=form, action='Edit')

@app.route('/admin/categories/delete/<int:category_id>', methods=['POST'])
@permission_required('manage_categories')
def admin_delete_category(category_id):
    category = Category.query.get_or_404(category_id)
    db.session.delete(category)
    db.session.commit()
    flash('Category deleted successfully!', 'success')
    main_logger.info(f'Category deleted: {category.name} by Admin ID {session["user_id"]}')
    return redirect(url_for('admin_categories'))

# Admin Order Management Routes
@app.route('/admin/orders')
@permission_required('manage_orders')
def admin_orders():
    orders = Order.query.order_by(Order.order_date.desc()).all()
    return render_template('admin_orders.html', orders=orders)

@app.route('/admin/orders/<int:order_id>')
@permission_required('manage_orders')
def admin_order_detail(order_id):
    order = Order.query.get_or_404(order_id)
    return render_template('admin_order_detail.html', order=order)

@app.route('/admin/orders/<int:order_id>/update', methods=['POST'])
@permission_required('manage_orders')
def admin_update_order_status(order_id):
    order = Order.query.get_or_404(order_id)
    new_status = request.form.get('status')
    if new_status in ['Pending', 'Processing', 'Shipped', 'Delivered', 'Cancelled']:
        order.status = new_status
        db.session.commit()
        flash('Order status updated successfully!', 'success')
        main_logger.info(f'Order {order.id} status updated to {new_status} by Admin ID {session["user_id"]}')
    else:
        flash('Invalid status selected.', 'danger')
    return redirect(url_for('admin_order_detail', order_id=order_id))

# Admin User Management Routes
@app.route('/admin/users')
@superadmin_required
@permission_required('manage_users')
def admin_users():
    users = User.query.all()
    return render_template('admin_users.html', users=users)

@app.route('/admin/users/add', methods=['GET', 'POST'])
@superadmin_required
@permission_required('manage_users')
def admin_add_user():
    form = AdminUserForm()
    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            email=form.email.data,
            roles=','.join(form.roles.data)
        )
        try:
            user.set_password(form.password.data)
        except ValueError as e:
            flash(str(e), 'danger')
            main_logger.debug(f'Failed to add user {user.username}: {str(e)}')
            return render_template('admin_user_form.html', form=form, action='Add')
        db.session.add(user)
        db.session.commit()
        flash('Admin user added successfully!', 'success')
        main_logger.info(f'Admin user added: {user.username} by Admin ID {session["user_id"]}')
        return redirect(url_for('admin_users'))
    return render_template('admin_user_form.html', form=form, action='Add')

@app.route('/admin/users/delete/<int:user_id>', methods=['POST'])
@superadmin_required
@permission_required('manage_users')
def admin_delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.username == 'admin':
        flash('Cannot delete the primary admin user.', 'danger')
        return redirect(url_for('admin_users'))
    db.session.delete(user)
    db.session.commit()
    flash('User deleted successfully!', 'success')
    main_logger.info(f'User deleted: {user.username} by Admin ID {session["user_id"]}')
    return redirect(url_for('admin_users'))

# Shopping Cart Functionality

@app.route('/add_to_cart/<int:product_id>', methods=['POST'])
def add_to_cart(product_id):
    if not session.get('customer_logged_in'):
        flash('Please log in to add items to your cart.', 'danger')
        return redirect(url_for('customer_login'))
    product = Product.query.get_or_404(product_id)
    user = User.query.filter_by(username=session['customer_user']).first()

    # Get the quantity from the form
    try:
        quantity = int(request.form.get('quantity', 1))
    except ValueError:
        quantity = 1
    if quantity < 1:
        quantity = 1

    # Get total quantity already in cart
    cart = user.cart
    existing_cart_item = None
    existing_quantity = 0
    if cart:
        existing_cart_item = CartItem.query.filter_by(cart_id=cart.id, product_id=product.id).first()
        if existing_cart_item:
            existing_quantity = existing_cart_item.quantity

    # Get total available inventory
    available_inventory = product.get_total_inventory()

    # Check if requested quantity exceeds available inventory
    if existing_quantity + quantity > available_inventory:
        max_addable = available_inventory - existing_quantity
        if max_addable > 0:
            flash(f'Cannot add {quantity} units. Only {max_addable} more units can be added to your cart.', 'warning')
        else:
            flash('You have already added the maximum available quantity of this product to your cart.', 'warning')
        return redirect(url_for('view_product_detail', product_id=product.id))

    # Proceed to add to cart
    if not cart:
        cart = Cart(user_id=user.id)
        db.session.add(cart)
        db.session.commit()

    if existing_cart_item:
        existing_cart_item.quantity += quantity
    else:
        cart_item = CartItem(cart_id=cart.id, product_id=product.id, quantity=quantity)
        db.session.add(cart_item)

    db.session.commit()
    flash(f'Added {quantity} units of {product.name} to your cart.', 'success')
    return redirect(url_for('view_cart'))

@app.route('/update_cart_item/<int:item_id>', methods=['POST'])
def update_cart_item(item_id):
    if not session.get('customer_logged_in'):
        flash('Please log in first.', 'danger')
        return redirect(url_for('customer_login'))
    user = User.query.filter_by(username=session['customer_user']).first()
    cart_item = CartItem.query.get_or_404(item_id)

    if cart_item.cart.user_id != user.id:
        flash('Unauthorized action.', 'danger')
        return redirect(url_for('view_cart'))

    form = UpdateCartForm(request.form)
    if form.validate():
        new_quantity = form.quantity.data
        try:
            new_quantity = int(new_quantity)
        except ValueError:
            flash('Invalid quantity.', 'danger')
            return redirect(url_for('view_cart'))
        if new_quantity < 1:
            flash('Quantity must be at least 1.', 'danger')
            return redirect(url_for('view_cart'))

        # Get total available inventory
        available_inventory = cart_item.product.get_total_inventory()

        # Check if new quantity exceeds available inventory
        if new_quantity > available_inventory:
            flash(f'Cannot update quantity to {new_quantity}. Only {available_inventory} units are available.', 'warning')
            return redirect(url_for('view_cart'))

        cart_item.quantity = new_quantity
        db.session.commit()
        flash(f'Updated quantity for {cart_item.product.name}.', 'success')
    else:
        flash('Invalid quantity.', 'danger')
    return redirect(url_for('view_cart'))

@app.route('/remove_cart_item/<int:item_id>', methods=['POST'])
def remove_cart_item(item_id):
    if not session.get('customer_logged_in'):
        flash('Please log in first.', 'danger')
        return redirect(url_for('customer_login'))
    user = User.query.filter_by(username=session['customer_user']).first()
    cart_item = CartItem.query.get_or_404(item_id)
    
    # Verify that the cart item belongs to the current user
    if cart_item.cart.user_id != user.id:
        flash('Unauthorized action.', 'danger')
        return redirect(url_for('view_cart'))

    # Retrieve product name before deleting the cart item
    product_name = cart_item.product.name

    db.session.delete(cart_item)
    db.session.commit()
    flash(f'Removed {product_name} from your cart.', 'success')
    return redirect(url_for('view_cart'))

@app.route('/cart')
def view_cart():
    if not session.get('customer_logged_in'):
        flash('Please log in first.', 'danger')
        return redirect(url_for('customer_login'))
    user = User.query.filter_by(username=session['customer_user']).first()
    cart = user.cart
    if not cart or not cart.items:
        return render_template('cart.html', cart=None)

    forms = {}
    for item in cart.items:
        form = UpdateCartForm(prefix=str(item.id))
        form.quantity.data = item.quantity
        forms[item.id] = form

    total = sum(item.product.price * item.quantity for item in cart.items)
    return render_template('cart.html', cart=cart, forms=forms, total=total)

# Checkout Route (Placeholder)
@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    if not session.get('customer_logged_in'):
        flash('Please log in first.', 'danger')
        return redirect(url_for('customer_login'))
    # Placeholder for checkout functionality
    flash('Checkout functionality to be implemented.', 'info')
    return redirect(url_for('view_cart'))

# Customer-Facing Product Browsing Routes
@app.route('/products')
def view_products():
    category_id = request.args.get('category', type=int)
    page = request.args.get('page', 1, type=int)
    per_page = 10  # Number of products per page
    sort = request.args.get('sort', 'name')  # Default sort by name
    sort_options = {
        'name': Product.name.asc(),
        'price_asc': Product.price.asc(),
        'price_desc': Product.price.desc(),
        # Add more sort options as needed
    }
    sort_order = sort_options.get(sort, Product.name.asc())
    
    if category_id:
        selected_category = Category.query.get(category_id)
        products_pagination = Product.query.filter_by(category_id=category_id).order_by(sort_order).paginate(page=page, per_page=per_page, error_out=False)
    else:
        selected_category = None
        products_pagination = Product.query.order_by(sort_order).paginate(page=page, per_page=per_page, error_out=False)
    
    categories = Category.query.order_by(Category.name).all()
    return render_template('view_products.html', 
                           products=products_pagination.items, 
                           categories=categories, 
                           selected_category=selected_category,  # Pass the Category object
                           pagination=products_pagination, 
                           sort=sort)

@app.route('/products/<int:product_id>')
def view_product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    return render_template('view_product_detail.html', product=product)

@app.route('/search', methods=['GET'])
def search_products():
    query = request.args.get('q', '')
    if query:
        # Perform case-insensitive search using ilike
        products = Product.query.filter(Product.name.ilike(f'%{query}%')).all()
        flash(f'Search results for "{query}":', 'info')
    else:
        products = []
        flash('Please enter a search term.', 'danger')
    
    categories = Category.query.order_by(Category.name).all()
    return render_template('view_products.html', 
                           products=products, 
                           categories=categories, 
                           selected_category=None, 
                           search_query=query, 
                           pagination=None, 
                           sort=None)

# Inventory Management Routes
LOW_STOCK_THRESHOLD = 5

@app.route('/admin/inventory')
@permission_required('manage_inventory')
def admin_inventory():
    warehouses = Warehouse.query.all()
    low_stock_items = []
    for warehouse in warehouses:
        for inventory in warehouse.inventories:
            if inventory.quantity <= LOW_STOCK_THRESHOLD:
                low_stock_items.append(inventory)
    return render_template('admin_inventory.html', warehouses=warehouses, low_stock_items=low_stock_items)

@app.route('/admin/inventory/update', methods=['GET', 'POST'])
@permission_required('manage_inventory')
def admin_update_inventory():
    if request.method == 'POST':
        warehouse_id = request.form.get('warehouse_id', type=int)
        product_id = request.form.get('product_id', type=int)
        quantity = request.form.get('quantity', type=int)

        inventory = Inventory.query.filter_by(warehouse_id=warehouse_id, product_id=product_id).first()
        if inventory:
            inventory.quantity = quantity
        else:
            inventory = Inventory(warehouse_id=warehouse_id, product_id=product_id, quantity=quantity)
            db.session.add(inventory)
        db.session.commit()
        flash('Inventory updated successfully!', 'success')
        main_logger.info(f'Inventory updated: Product ID {product_id} in Warehouse ID {warehouse_id} set to {quantity} by Admin ID {session["user_id"]}')
        return redirect(url_for('admin_inventory'))

    warehouses = Warehouse.query.all()
    products = Product.query.all()
    return render_template('admin_update_inventory.html', warehouses=warehouses, products=products)

# Error Handlers
@app.errorhandler(400)
def bad_request_error(error):
    return render_template('errors/400.html'), 400

@app.errorhandler(401)
def unauthorized_error(error):
    main_logger.warning(f'401 Unauthorized access: {request.url}')
    return render_template('errors/401.html'), 401

@app.errorhandler(403)
def forbidden_error(error):
    main_logger.warning(f'403 Forbidden access: {request.url}')
    return render_template('errors/403.html'), 403

@app.errorhandler(404)
def page_not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_server_error(error):
    main_logger.error(f'500 Internal Server Error: {error}, Route: {request.url}')
    return render_template('errors/500.html'), 500

with app.app_context():
    db.create_all()
    
    # Create or update admin user
    admin_email = 'admin@example.com'
    admin_username = 'admin'
    admin_password = 'Admin@123'  # Must meet password criteria

    admin_user = User.query.filter_by(email=admin_email).first()
    if not admin_user:
        admin_user = User(
            username=admin_username,
            email=admin_email,
            roles='super_admin'
        )
        try:
            admin_user.set_password(admin_password)
            db.session.add(admin_user)
            db.session.commit()
            main_logger.info('Super admin user created.')
        except ValueError as e:
            main_logger.error(f'Failed to create super admin user: {str(e)}')
    else:
        if 'super_admin' not in admin_user.roles.split(','):
            admin_user.roles += ',super_admin'
            try:
                admin_user.set_password(admin_password)
                db.session.commit()
                main_logger.info('Super admin role assigned and password updated.')
            except ValueError as e:
                main_logger.error(f'Failed to update super admin user: {str(e)}')
    
    # Create a sample customer user if not exists
    customer_user = User.query.filter_by(username='customer').first()
    if not customer_user:
        customer_user = User(
            username='customer',
            email='customer@example.com',
            roles='customer'
        )
        try:
            customer_user.set_password('Customer@123')  # Must meet criteria
            db.session.add(customer_user)
            db.session.commit()
            main_logger.info('Customer user created.')
        except ValueError as e:
            main_logger.error(f'Failed to create customer user: {str(e)}')
    
    # Add sample categories if none exist
    if Category.query.count() == 0:
        categories = [
            Category(name='Beverages'),
            Category(name='Fresh Produce'),
            Category(name='Pantry Staples'),
            Category(name='Frozen Goods'),
            Category(name='Cleaning Supplies'),
            Category(name='Personal Care'),
            Category(name='Snacks'),
            Category(name='Dairy Products'),
            Category(name='Meat and Poultry'),
            Category(name='Bakery'),
        ]
        db.session.add_all(categories)
        db.session.commit()
        main_logger.info('Sample categories added.')

    # Ensure there is at least one category
    sample_category = Category.query.first()
    if not sample_category:
        sample_category = Category(name='Sample Category')
        db.session.add(sample_category)
        db.session.commit()
        main_logger.info('Sample Category created.')

    # Create a sample product if none exists
    sample_product = Product.query.first()
    if not sample_product:
        sample_product = Product(
            name='Sample Product',
            description='This is a sample product.',
            price=9.99,
            category_id=sample_category.id
        )
        db.session.add(sample_product)
        db.session.commit()
        main_logger.info(f'Sample Product created: {sample_product.name} (ID: {sample_product.id})')

    # Seed Warehouses
    if Warehouse.query.count() == 0:
        warehouses = [
            Warehouse(name='Main Warehouse', location='Downtown'),
            Warehouse(name='Secondary Warehouse', location='Uptown'),
        ]
        db.session.add_all(warehouses)
        db.session.commit()
        main_logger.info('Warehouses seeded.')

    # Seed Inventory
    if Inventory.query.count() == 0:
        products = Product.query.all()
        warehouses = Warehouse.query.all()
        for product in products:
            for warehouse in warehouses:
                inventory = Inventory(product_id=product.id, warehouse_id=warehouse.id, quantity=10)
                db.session.add(inventory)
        db.session.commit()
        main_logger.info('Inventory seeded.')

# Run the Flask application
if __name__ == '__main__':
    app.run(debug=True)
