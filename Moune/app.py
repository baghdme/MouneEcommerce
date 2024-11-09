# app.py
from flask import Flask, render_template, redirect, url_for, flash, request, session
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from config import Config
from extensions import db
from models import User, Category, Product, Order, OrderItem
from forms import ProductForm, CategoryForm, RegistrationForm, LoginForm

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)

with app.app_context():
    db.create_all()
    
    # Create admin user if it doesn't exist
    admin_user = User.query.filter_by(username='admin').first()
    if not admin_user:
        admin_user = User(username='admin', email='admin@example.com', role='admin')
        admin_user.set_password('admin123')  # Use a secure password in production
        db.session.add(admin_user)
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
        db.session.bulk_save_objects(categories)
        db.session.commit()
    
    # Create a sample customer user if not exists
    customer_user = User.query.filter_by(username='customer').first()
    if not customer_user:
        customer_user = User(username='customer', email='customer@example.com', role='customer')
        customer_user.set_password('customer123')
        db.session.add(customer_user)
        db.session.commit()
    
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
            inventory_count=100,
            category_id=sample_category.id
        )
        db.session.add(sample_product)
        db.session.commit()
    
    # Create a sample order if none exists
    if Order.query.count() == 0:
        sample_order = Order(
            user_id=customer_user.id,
            status='Pending',
            total_amount=sample_product.price * 2
        )
        db.session.add(sample_order)
        db.session.commit()
    
        # Create order items
        order_item = OrderItem(
            order_id=sample_order.id,
            product_id=sample_product.id,
            quantity=2,
            unit_price=sample_product.price
        )
        db.session.add(order_item)
        db.session.commit()

# Admin login required decorator
def admin_login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in'):
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

# Admin Authentication Routes
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()

        if user and user.role == 'admin' and user.check_password(password):
            session['admin_logged_in'] = True
            session['admin_user'] = user.username
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid credentials or not authorized.', 'danger')
            return redirect(url_for('admin_login'))
    return render_template('admin_login.html')

@app.route('/admin/logout')
@admin_login_required
def admin_logout():
    session.clear()
    return redirect(url_for('admin_login'))

@app.route('/admin/dashboard')
@admin_login_required
def admin_dashboard():
    return render_template('admin_dashboard.html', username=session['admin_user'])

# Admin Product Management Routes
@app.route('/admin/products')
@admin_login_required
def admin_products():
    products = Product.query.all()
    return render_template('admin_products.html', products=products)

@app.route('/admin/products/add', methods=['GET', 'POST'])
@admin_login_required
def admin_add_product():
    form = ProductForm()
    form.category_id.choices = [(c.id, c.name) for c in Category.query.order_by('name')]
    if form.validate_on_submit():
        product = Product(
            name=form.name.data,
            description=form.description.data,
            price=form.price.data,
            inventory_count=form.inventory_count.data,
            category_id=form.category_id.data
        )
        db.session.add(product)
        db.session.commit()
        flash('Product added successfully!', 'success')
        return redirect(url_for('admin_products'))
    return render_template('admin_product_form.html', form=form, action='Add')

@app.route('/admin/products/edit/<int:product_id>', methods=['GET', 'POST'])
@admin_login_required
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
def admin_delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    db.session.delete(product)
    db.session.commit()
    flash('Product deleted successfully!', 'success')
    return redirect(url_for('admin_products'))

# Admin Category Management Routes
@app.route('/admin/categories')
@admin_login_required
def admin_categories():
    categories = Category.query.order_by('name').all()
    return render_template('admin_categories.html', categories=categories)

@app.route('/admin/categories/add', methods=['GET', 'POST'])
@admin_login_required
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
def admin_delete_category(category_id):
    category = Category.query.get_or_404(category_id)
    db.session.delete(category)
    db.session.commit()
    flash('Category deleted successfully!', 'success')
    return redirect(url_for('admin_categories'))

# Admin Order Management Routes
@app.route('/admin/orders')
@admin_login_required
def admin_orders():
    orders = Order.query.order_by(Order.order_date.desc()).all()
    return render_template('admin_orders.html', orders=orders)

@app.route('/admin/orders/<int:order_id>')
@admin_login_required
def admin_order_detail(order_id):
    order = Order.query.get_or_404(order_id)
    return render_template('admin_order_detail.html', order=order)

@app.route('/admin/orders/<int:order_id>/update', methods=['POST'])
@admin_login_required
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
def admin_users():
    users = User.query.all()
    return render_template('admin_users.html', users=users)

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

if __name__ == '__main__':
    app.run(debug=True)
