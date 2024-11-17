# app.py
from flask import Flask, render_template, redirect, url_for, flash, request, session
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from config import Config
from extensions import db
from models import User, Category, Product, Order, OrderItem, Cart, CartItem, Warehouse, Inventory
from forms import ProductForm, CategoryForm, RegistrationForm, LoginForm, UpdateCartForm, AdminUserForm

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)

# roles for users
ROLE_PERMISSIONS = {
    'super_admin': ['manage_products', 'manage_orders', 'manage_inventory', 'manage_categories', 'manage_users'],
    'product_manager': ['manage_products'],
    'order_manager': ['manage_orders'],
    'inventory_manager': ['manage_inventory'],  # Already defined
    'category_manager': ['manage_categories'],
    'user_manager': ['manage_users'],
}


from functools import wraps
from flask import abort, flash

def permission_required(permission):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not session.get('admin_logged_in'):
                return redirect(url_for('admin_login'))
            user = User.query.filter_by(username=session.get('admin_user')).first()
            if not user:
                session.clear()
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

with app.app_context():
    db.create_all()
    
    # Create admin user if it doesn't exist
    admin_user = User.query.filter_by(username='admin').first()
    '''    if not admin_user:
        admin_user = User(
            username='admin',
            email='admin@example.com',
            roles='super_admin'  # Assign the super_admin role
        )
        admin_user.set_password('Admin123!')  # Updated password
        db.session.add(admin_user)
        db.session.commit()
    else:
        # Ensure the admin has the super_admin role'''
    if 'super_admin' not in admin_user.roles.split(','):
        admin_user.roles += ',super_admin'
        db.session.commit()

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
        db.session.add_all(categories)  # Changed from bulk_save_objects to add_all
        db.session.commit()
    
    # Create a sample customer user if not exists
    customer_user = User.query.filter_by(username='customer').first()
    
    # Ensure there is at least one category
    sample_category = Category.query.first()
    if not sample_category:
        sample_category = Category(name='Sample Category')
        db.session.add(sample_category)
        db.session.commit()
    
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
        print(f"Sample Product ID: {sample_product.id}")  # Debugging statement

            
    # Seed Warehouses
    if Warehouse.query.count() == 0:
        warehouses = [
            Warehouse(name='Main Warehouse', location='Downtown'),
            Warehouse(name='Secondary Warehouse', location='Uptown'),
        ]
        db.session.add_all(warehouses)
        db.session.commit()

    # Seed Inventory
    if Inventory.query.count() == 0:
        products = Product.query.all()
        warehouses = Warehouse.query.all()
        for product in products:
            for warehouse in warehouses:
                inventory = Inventory(product_id=product.id, warehouse_id=warehouse.id, quantity=10)
                db.session.add(inventory)
        db.session.commit()
# Admin login required decorator
def admin_login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in') or not session.get('admin_user'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function


# Customer login required decorator
def customer_login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('customer_logged_in'):
            return redirect(url_for('customer_login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def home():
    return render_template('home.html')  # Ensure you have a home.html template

def is_admin(user):
    admin_roles = ROLE_PERMISSIONS.keys()
    user_roles = user.roles.split(',')
    return any(role in admin_roles for role in user_roles)

# Admin Authentication Routes
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password) and is_admin(user):
            session['admin_logged_in'] = True
            session['admin_user'] = user.username
            session['admin_roles'] = user.roles  # Store roles in session
            flash('Logged in as admin.', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid credentials or not authorized.', 'danger')
            return redirect(url_for('admin_login'))
    return render_template('admin_login.html')

@app.route('/admin/logout')
@admin_login_required
def admin_logout():
    session.pop('admin_logged_in', None)
    session.pop('admin_user', None)
    session.pop('admin_roles', None)
    flash('Admin logged out.', 'info')
    return redirect(url_for('admin_login'))
    
@app.route('/admin/dashboard')
@admin_login_required
def admin_dashboard():
    user = User.query.filter_by(username=session['admin_user']).first()
    user_roles = user.roles.split(',')
    user_permissions = set()
    for role in user_roles:
        user_permissions.update(ROLE_PERMISSIONS.get(role, []))
    return render_template('admin_dashboard.html', username=user.username, roles=user_roles, permissions=user_permissions)

# Admin Product Management Routes
@app.route('/admin/products')
@admin_login_required
@permission_required('manage_products')
def admin_products():
    products = Product.query.all()
    return render_template('admin_products.html', products=products)


@app.route('/admin/products/add', methods=['GET', 'POST'])
@admin_login_required
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
        return redirect(url_for('admin_products'))
    return render_template('admin_product_form.html', form=form, action='Add')


@app.route('/admin/products/edit/<int:product_id>', methods=['GET', 'POST'])
@admin_login_required
@permission_required('manage_products')
def admin_edit_product(product_id):
    product = Product.query.get_or_404(product_id)
    form = ProductForm(obj=product)
    form.category_id.choices = [(c.id, c.name) for c in Category.query.order_by('name')]
    if form.validate_on_submit():
        form.populate_obj(product)
        db.session.commit()
        flash('Product updated successfully!', 'success')
        return redirect(url_for('admin_products'))
    return render_template('admin_product_form.html', form=form, action='Edit')

@app.route('/admin/products/delete/<int:product_id>', methods=['POST'])
@admin_login_required
@permission_required('manage_products')
def admin_delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    db.session.delete(product)
    db.session.commit()
    flash('Product deleted successfully!', 'success')
    return redirect(url_for('admin_products'))

# Admin Category Management Routes
@app.route('/admin/categories')
@admin_login_required
@permission_required('manage_categories')
def admin_categories():
    categories = Category.query.order_by('name').all()
    return render_template('admin_categories.html', categories=categories)

@app.route('/admin/categories/add', methods=['GET', 'POST'])
@admin_login_required
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
        return redirect(url_for('admin_categories'))
    return render_template('admin_category_form.html', form=form, action='Add')

@app.route('/admin/categories/edit/<int:category_id>', methods=['GET', 'POST'])
@admin_login_required
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
        return redirect(url_for('admin_categories'))
    return render_template('admin_category_form.html', form=form, action='Edit')

@app.route('/admin/categories/delete/<int:category_id>', methods=['POST'])
@admin_login_required
@permission_required('manage_categories')
def admin_delete_category(category_id):
    category = Category.query.get_or_404(category_id)
    db.session.delete(category)
    db.session.commit()
    flash('Category deleted successfully!', 'success')
    return redirect(url_for('admin_categories'))

# Admin Order Management Routes
@app.route('/admin/orders')
@admin_login_required
@permission_required('manage_orders')
def admin_orders():
    orders = Order.query.order_by(Order.order_date.desc()).all()
    return render_template('admin_orders.html', orders=orders)

@app.route('/admin/orders/<int:order_id>')
@admin_login_required
@permission_required('manage_orders')
def admin_order_detail(order_id):
    order = Order.query.get_or_404(order_id)
    return render_template('admin_order_detail.html', order=order)

@app.route('/admin/orders/<int:order_id>/update', methods=['POST'])
@admin_login_required
@permission_required('manage_orders')
def admin_update_order_status(order_id):
    order = Order.query.get_or_404(order_id)
    new_status = request.form.get('status')
    if new_status in ['Pending', 'Processing', 'Shipped', 'Delivered', 'Cancelled']:
        order.status = new_status
        db.session.commit()
        flash('Order status updated successfully!', 'success')
    else:
        flash('Invalid status selected.', 'danger')
    return redirect(url_for('admin_order_detail', order_id=order_id))

# Admin User Management Routes
@app.route('/admin/users')
@admin_login_required
@permission_required('manage_users')
def admin_users():
    users = User.query.all()
    return render_template('admin_users.html', users=users)


@app.route('/admin/users/add', methods=['GET', 'POST'])
@admin_login_required
@permission_required('manage_users')
def admin_add_user():
    form = AdminUserForm()
    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            email=form.email.data,
            roles=','.join(form.roles.data)
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Admin user added successfully!', 'success')
        return redirect(url_for('admin_users'))
    return render_template('admin_user_form.html', form=form, action='Add')

# Customer Registration Routes
@app.route('/register', methods=['GET', 'POST'])
def customer_register():
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            email=form.email.data,
            role='customer'
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Registration successful! You can now log in.', 'success')
        return redirect(url_for('customer_login'))
    return render_template('customer_register.html', form=form)

# Customer Login Routes
@app.route('/login', methods=['GET', 'POST'])
def customer_login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data, role='customer').first()
        if user and user.check_password(form.password.data):
            session['customer_logged_in'] = True
            session['customer_user'] = user.username
            flash('Logged in successfully!', 'success')
            return redirect(url_for('customer_dashboard'))
        else:
            flash('Invalid credentials.', 'danger')
    return render_template('customer_login.html', form=form)

@app.route('/logout')
@customer_login_required
def customer_logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('customer_login'))

@app.route('/customer/dashboard')
@customer_login_required
def customer_dashboard():
    user = User.query.filter_by(username=session['customer_user']).first()
    return render_template('customer_dashboard.html', user=user)

# **Shopping Cart Functionality**

@app.route('/add_to_cart/<int:product_id>', methods=['POST'])
@customer_login_required
def add_to_cart(product_id):
    product = Product.query.get_or_404(product_id)
    user = User.query.filter_by(username=session['customer_user']).first()

    # Get the quantity from the form
    quantity = int(request.form.get('quantity', 1))
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
@customer_login_required
def update_cart_item(item_id):
    user = User.query.filter_by(username=session['customer_user']).first()
    cart_item = CartItem.query.get_or_404(item_id)

    if cart_item.cart.user_id != user.id:
        flash('Unauthorized action.', 'danger')
        return redirect(url_for('view_cart'))

    form = UpdateCartForm(request.form)
    if form.validate():
        new_quantity = form.quantity.data
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
@customer_login_required
def remove_cart_item(item_id):
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

# app.py

@app.route('/cart')
@customer_login_required
def view_cart():
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

# **Checkout Route (To Be Implemented in Next Steps)**
@app.route('/checkout', methods=['GET', 'POST'])
@customer_login_required
def checkout():
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
# Removed /list_routes endpoint for security reasons

LOW_STOCK_THRESHOLD = 5

@app.route('/admin/inventory')
@admin_login_required
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
@admin_login_required
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
        return redirect(url_for('admin_inventory'))

    warehouses = Warehouse.query.all()
    products = Product.query.all()
    return render_template('admin_update_inventory.html', warehouses=warehouses, products=products)


if __name__ == '__main__':
    app.run(debug=True)
