import os
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
import pymysql
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import date, timedelta
import threading
import time

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'shelf_secret_key_123')

# Dynamic DB Config
DB_HOST = os.environ.get('MYSQLHOST', 'localhost')
DB_USER = os.environ.get('MYSQLUSER', 'root')
DB_PASSWORD = os.environ.get('MYSQLPASSWORD', 'NewPassword123!')
DB_NAME = os.environ.get('MYSQL_DATABASE', 'shelf_db')

def get_db_connection():
    return pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        cursorclass=pymysql.cursors.DictCursor
    )

def check_and_apply_fines():
    """Scan all borrowed transactions past due date and apply fines once.
    Uses the fine_applied flag on transactions to prevent double-counting."""
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # Find overdue borrowed books that haven't been fined yet
            cursor.execute("""
                SELECT id, user_id FROM transactions
                WHERE status = 'borrowed'
                  AND due_date < CURDATE()
                  AND fine_applied = 0
            """)
            overdue = cursor.fetchall()
            for row in overdue:
                cursor.execute(
                    "UPDATE users SET fine_count = fine_count + 1 WHERE id = %s",
                    (row['user_id'],)
                )
                cursor.execute(
                    "UPDATE transactions SET fine_applied = 1 WHERE id = %s",
                    (row['id'],)
                )
            conn.commit()
    except Exception as e:
        print(f"Fine check error: {e}")
    finally:
        if 'conn' in locals() and conn.open:
            conn.close()

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'warning'

class User(UserMixin):
    def __init__(self, id, name, email, role):
        self.id = id
        self.name = name
        self.email = email
        self.role = role

@login_manager.user_loader
def load_user(user_id):
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
            user_data = cursor.fetchone()
            if user_data:
                return User(user_data['id'], user_data['name'], user_data['email'], user_data['role'])
    except Exception as e:
        print(f"Database error: {e}")
    finally:
        if 'conn' in locals() and conn.open:
            conn.close()
    return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        
        hashed_password = generate_password_hash(password)
        
        try:
            conn = get_db_connection()
            with conn.cursor() as cursor:
                cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
                if cursor.fetchone():
                    flash('Email already exists. Please login.', 'danger')
                    return redirect(url_for('signup'))
                
                cursor.execute(
                    "INSERT INTO users (name, email, password) VALUES (%s, %s, %s)",
                    (name, email, hashed_password)
                )
                conn.commit()
                flash('Account created successfully! Please login.', 'success')
                return redirect(url_for('login'))
        except Exception as e:
            flash(f'An error occurred: {e}', 'danger')
        finally:
            if 'conn' in locals() and conn.open:
                conn.close()
            
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        try:
            conn = get_db_connection()
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
                user_data = cursor.fetchone()
                
                if user_data and check_password_hash(user_data['password'], password):
                    user = User(user_data['id'], user_data['name'], user_data['email'], user_data['role'])
                    login_user(user)
                    flash('Logged in successfully!', 'success')
                    return redirect(url_for('browse'))
                else:
                    flash('Invalid email or password.', 'danger')
        except Exception as e:
            flash(f'An error occurred: {e}', 'danger')
        finally:
            if 'conn' in locals() and conn.open:
                conn.close()
            
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/browse')
def browse():
    books = []
    genres = []
    user_borrowed_books = []
    selected_genre = request.args.get('genre', '')
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT DISTINCT genre FROM books ORDER BY genre")
            genres = [row['genre'] for row in cursor.fetchall()]
            
            if selected_genre:
                cursor.execute("SELECT * FROM books WHERE genre = %s ORDER BY title", (selected_genre,))
            else:
                cursor.execute("SELECT * FROM books ORDER BY title")
            books = cursor.fetchall()
            
            if current_user.is_authenticated:
                cursor.execute(
                    "SELECT book_id, id as transaction_id, due_date FROM transactions WHERE user_id = %s AND status = 'borrowed'", 
                    (current_user.id,)
                )
                user_borrowed_books = {row['book_id']: row for row in cursor.fetchall()}
    except Exception as e:
        flash(f'An error occurred loading books: {e}', 'danger')
    finally:
        if 'conn' in locals() and conn.open:
            conn.close()
            
    return render_template('browse.html', books=books, user_borrowed_books=user_borrowed_books, genres=genres, selected_genre=selected_genre)

@app.route('/borrow/<int:book_id>')
@login_required
def borrow(book_id):
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # Check if available
            cursor.execute("SELECT * FROM books WHERE id = %s", (book_id,))
            book = cursor.fetchone()
            
            if book and book['available_copies'] > 0:
                # Check if user already borrowed this book
                cursor.execute(
                    "SELECT id FROM transactions WHERE user_id = %s AND book_id = %s AND status = 'borrowed'",
                    (current_user.id, book_id)
                )
                if cursor.fetchone():
                    flash('You have already borrowed this book.', 'warning')
                    return redirect(url_for('browse'))
                
                # Borrow logic
                borrow_date = date.today()
                due_date = borrow_date + timedelta(days=14)
                
                cursor.execute(
                    "INSERT INTO transactions (user_id, book_id, borrow_date, due_date, status) VALUES (%s, %s, %s, %s, 'pending')",
                    (current_user.id, book_id, borrow_date, due_date)
                )
                cursor.execute(
                    "UPDATE books SET available_copies = available_copies - 1 WHERE id = %s",
                    (book_id,)
                )
                conn.commit()
                flash(f'Successfully requested to borrow "{book["title"]}". Awaiting admin approval.', 'success')
                return redirect(url_for('profile'))
            else:
                flash('This book is currently unavailable.', 'danger')
                return redirect(url_for('browse'))
    except Exception as e:
        flash(f'An error occurred: {e}', 'danger')
        return redirect(url_for('browse'))
    finally:
        if 'conn' in locals() and conn.open:
            conn.close()

@app.route('/return/<int:transaction_id>')
@login_required
def return_book(transaction_id):
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT t.*, b.title FROM transactions t JOIN books b ON t.book_id = b.id WHERE t.id = %s AND t.user_id = %s",
                (transaction_id, current_user.id)
            )
            trans = cursor.fetchone()
            
            if trans and trans['status'] == 'borrowed':
                return_date = date.today()
                cursor.execute(
                    "UPDATE transactions SET status = 'returned', return_date = %s WHERE id = %s",
                    (return_date, transaction_id)
                )
                cursor.execute(
                    "UPDATE books SET available_copies = available_copies + 1 WHERE id = %s",
                    (trans['book_id'],)
                )
                conn.commit()
                flash(f'Successfully returned "{trans["title"]}".', 'success')
                return render_template('return.html', title=trans['title'], return_date=return_date)
            else:
                flash('Invalid transaction or book already returned.', 'danger')
                return redirect(url_for('browse'))
    except Exception as e:
        flash(f'An error occurred: {e}', 'danger')
        return redirect(url_for('browse'))
    finally:
        if 'conn' in locals() and conn.open:
            conn.close()

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/profile')
@login_required
def profile():
    # Auto-detect fines on profile load
    check_and_apply_fines()
    
    user_transactions = []
    user_requests = []
    fine_count = 0
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT t.id, t.book_id, b.title, t.borrow_date, t.due_date, t.return_date, t.status
                FROM transactions t
                JOIN books b ON t.book_id = b.id
                WHERE t.user_id = %s
                ORDER BY t.borrow_date DESC
            """, (current_user.id,))
            user_transactions = cursor.fetchall()
            
            cursor.execute("SELECT * FROM book_requests WHERE user_id = %s ORDER BY request_date DESC", (current_user.id,))
            user_requests = cursor.fetchall()
            
            cursor.execute("SELECT fine_count FROM users WHERE id = %s", (current_user.id,))
            row = cursor.fetchone()
            if row:
                fine_count = row['fine_count']
            
    except Exception as e:
        flash(f'An error occurred loading profile: {e}', 'danger')
    finally:
        if 'conn' in locals() and conn.open:
            conn.close()
            
    return render_template('profile.html', transactions=user_transactions, requests=user_requests, fine_count=fine_count)

@app.route('/admin')
@login_required
def admin():
    if current_user.role != 'admin':
        flash('Unauthorized access. Admin privileges required.', 'danger')
        return redirect(url_for('browse'))
    
    # Auto-detect fines on admin load
    check_and_apply_fines()
        
    users, books, transactions, book_requests = [], [], [], []
    today = date.today()
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM users")
            users = cursor.fetchall()
            
            cursor.execute("SELECT * FROM books")
            books = cursor.fetchall()
            
            cursor.execute("""
                SELECT t.id, u.name as user_name, b.title as book_title, 
                       t.borrow_date, t.due_date, t.return_date, t.status 
                FROM transactions t
                JOIN users u ON t.user_id = u.id
                JOIN books b ON t.book_id = b.id
                ORDER BY t.borrow_date DESC
            """)
            transactions = cursor.fetchall()
            # Mark overdue for template display
            for t in transactions:
                t['is_overdue'] = (t['status'] == 'borrowed' and t['due_date'] and t['due_date'] < today)

            cursor.execute("""
                SELECT r.id, u.name as user_name, u.email as user_email, r.title, r.author, r.request_date, r.status
                FROM book_requests r JOIN users u ON r.user_id = u.id ORDER BY r.request_date DESC
            """)
            book_requests = cursor.fetchall()
    except Exception as e:
        flash(f'Database error loading admin dashboard: {e}', 'danger')
    finally:
        if 'conn' in locals() and conn.open:
            conn.close()
        
    return render_template('admin.html', users=users, books=books, transactions=transactions, book_requests=book_requests, today=today)

# --- ADMIN CRUD ROUTES & NEW USER ROUTES --- #
@app.route('/request_book', methods=['POST'])
@login_required
def request_book():
    title = request.form.get('title')
    author = request.form.get('author')
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("INSERT INTO book_requests (user_id, title, author, request_date) VALUES (%s, %s, %s, %s)", (current_user.id, title, author, date.today()))
            conn.commit()
            flash('Book request submitted successfully.', 'success')
    except Exception as e:
        flash(f'Error submitting request: {e}', 'danger')
    finally:
        if 'conn' in locals() and conn.open: conn.close()
    return redirect(url_for('profile'))

@app.route('/admin/book/add', methods=['POST'])
@login_required
def admin_add_book():
    if current_user.role != 'admin': return redirect(url_for('browse'))
    title = request.form.get('title')
    author = request.form.get('author')
    genre = request.form.get('genre')
    copies = int(request.form.get('copies', 1))
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("INSERT INTO books (title, author, genre, total_copies, available_copies) VALUES (%s, %s, %s, %s, %s)", (title, author, genre, copies, copies))
            conn.commit()
            flash('Book added successfully.', 'success')
    except Exception as e:
        flash(f'Error adding book: {e}', 'danger')
    finally:
        if 'conn' in locals() and conn.open: conn.close()
    return redirect(url_for('admin'))

@app.route('/admin/book/delete/<int:book_id>', methods=['POST'])
@login_required
def admin_delete_book(book_id):
    if current_user.role != 'admin': return redirect(url_for('browse'))
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM books WHERE id = %s", (book_id,))
            conn.commit()
            flash('Book deleted successfully.', 'success')
    except Exception as e:
        flash(f'Error deleting book: {e}', 'danger')
    finally:
        if 'conn' in locals() and conn.open: conn.close()
    return redirect(url_for('admin'))

@app.route('/admin/book/update/<int:book_id>', methods=['POST'])
@login_required
def admin_update_book(book_id):
    if current_user.role != 'admin': return redirect(url_for('browse'))
    title = request.form.get('title')
    author = request.form.get('author')
    genre = request.form.get('genre')
    copies = int(request.form.get('copies', 1))
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("UPDATE books SET title=%s, author=%s, genre=%s, available_copies=%s WHERE id=%s", (title, author, genre, copies, book_id))
            conn.commit()
            flash('Book updated successfully.', 'success')
    except Exception as e:
        flash(f'Error updating book: {e}', 'danger')
    finally:
        if 'conn' in locals() and conn.open: conn.close()
    return redirect(url_for('admin'))

@app.route('/admin/user/add', methods=['POST'])
@login_required
def admin_add_user():
    if current_user.role != 'admin': return redirect(url_for('browse'))
    name = request.form.get('name')
    email = request.form.get('email')
    password = request.form.get('password')
    role = request.form.get('role', 'user')
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            hashed = generate_password_hash(password)
            cursor.execute("INSERT INTO users (name, email, password, role) VALUES (%s, %s, %s, %s)", (name, email, hashed, role))
            conn.commit()
            flash('User created successfully.', 'success')
    except Exception as e:
        flash(f'Error creating user: {e}', 'danger')
    finally:
        if 'conn' in locals() and conn.open: conn.close()
    return redirect(url_for('admin'))

@app.route('/admin/user/update/<int:user_id>', methods=['POST'])
@login_required
def admin_update_user(user_id):
    if current_user.role != 'admin': return redirect(url_for('browse'))
    name = request.form.get('name')
    email = request.form.get('email')
    role = request.form.get('role')
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("UPDATE users SET name=%s, email=%s, role=%s WHERE id=%s", (name, email, role, user_id))
            conn.commit()
            flash('User updated successfully.', 'success')
    except Exception as e:
        flash(f'Error updating user: {e}', 'danger')
    finally:
        if 'conn' in locals() and conn.open: conn.close()
    return redirect(url_for('admin'))

@app.route('/admin/user/delete/<int:user_id>', methods=['POST'])
@login_required
def admin_delete_user(user_id):
    if current_user.role != 'admin': return redirect(url_for('browse'))
    if user_id == current_user.id:
        flash("You cannot delete yourself.", "danger")
        return redirect(url_for('admin'))
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM users WHERE id=%s", (user_id,))
            conn.commit()
            flash('User deleted successfully.', 'success')
    except Exception as e:
        flash(f'Error deleting user: {e}', 'danger')
    finally:
        if 'conn' in locals() and conn.open: conn.close()
    return redirect(url_for('admin'))

@app.route('/admin/transaction/approve/<int:trans_id>', methods=['POST'])
@login_required
def admin_approve_transaction(trans_id):
    if current_user.role != 'admin': return redirect(url_for('browse'))
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("UPDATE transactions SET status='borrowed' WHERE id=%s", (trans_id,))
            conn.commit()
            flash('Transaction approved! Book is now borrowed.', 'success')
    except Exception as e:
        flash(f'Error approving: {e}', 'danger')
    finally:
        if 'conn' in locals() and conn.open: conn.close()
    return redirect(url_for('admin'))

@app.route('/admin/transaction/reject/<int:trans_id>', methods=['POST'])
@login_required
def admin_reject_transaction(trans_id):
    if current_user.role != 'admin': return redirect(url_for('browse'))
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT book_id FROM transactions WHERE id=%s AND status='pending'", (trans_id,))
            trans = cursor.fetchone()
            if trans:
                cursor.execute("UPDATE transactions SET status='rejected' WHERE id=%s", (trans_id,))
                cursor.execute("UPDATE books SET available_copies = available_copies + 1 WHERE id=%s", (trans['book_id'],))
                conn.commit()
                flash('Transaction rejected & inventory restored.', 'success')
    except Exception as e:
        flash(f'Error rejecting: {e}', 'danger')
    finally:
        if 'conn' in locals() and conn.open: conn.close()
    return redirect(url_for('admin'))

@app.route('/admin/request/approve/<int:req_id>', methods=['POST'])
@login_required
def admin_approve_request(req_id):
    if current_user.role != 'admin': return redirect(url_for('browse'))
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("UPDATE book_requests SET status='approved' WHERE id=%s", (req_id,))
            conn.commit()
            flash('User request marked as approved.', 'success')
    except Exception as e:
        pass
    finally:
        if 'conn' in locals() and conn.open: conn.close()
    return redirect(url_for('admin'))

@app.route('/admin/request/reject/<int:req_id>', methods=['POST'])
@login_required
def admin_reject_request(req_id):
    if current_user.role != 'admin': return redirect(url_for('browse'))
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("UPDATE book_requests SET status='rejected' WHERE id=%s", (req_id,))
            conn.commit()
            flash('User request rejected.', 'warning')
    except Exception as e:
        pass
    finally:
        if 'conn' in locals() and conn.open: conn.close()
    return redirect(url_for('admin'))

@app.route('/admin/request/delete/<int:req_id>', methods=['POST'])
@login_required
def admin_delete_request(req_id):
    if current_user.role != 'admin': return redirect(url_for('browse'))
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM book_requests WHERE id=%s", (req_id,))
            conn.commit()
            flash('User request deleted.', 'warning')
    except Exception as e:
        pass
    finally:
        if 'conn' in locals() and conn.open: conn.close()
    return redirect(url_for('admin'))

# --- FINE MANAGEMENT ROUTES --- #
@app.route('/admin/fine/waive/<int:user_id>', methods=['POST'])
@login_required
def admin_waive_fine(user_id):
    if current_user.role != 'admin': return redirect(url_for('browse'))
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("UPDATE users SET fine_count = 0 WHERE id = %s", (user_id,))
            conn.commit()
            flash('All fines waived for this user.', 'success')
    except Exception as e:
        flash(f'Error waiving fine: {e}', 'danger')
    finally:
        if 'conn' in locals() and conn.open: conn.close()
    return redirect(url_for('admin'))

@app.route('/admin/fine/increase/<int:user_id>', methods=['POST'])
@login_required
def admin_increase_fine(user_id):
    if current_user.role != 'admin': return redirect(url_for('browse'))
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("UPDATE users SET fine_count = fine_count + 1 WHERE id = %s", (user_id,))
            conn.commit()
            flash('Fine increased by 1.', 'warning')
    except Exception as e:
        flash(f'Error increasing fine: {e}', 'danger')
    finally:
        if 'conn' in locals() and conn.open: conn.close()
    return redirect(url_for('admin'))

@app.route('/admin/fine/decrease/<int:user_id>', methods=['POST'])
@login_required
def admin_decrease_fine(user_id):
    if current_user.role != 'admin': return redirect(url_for('browse'))
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("UPDATE users SET fine_count = GREATEST(fine_count - 1, 0) WHERE id = %s", (user_id,))
            conn.commit()
            flash('Fine decreased by 1.', 'success')
    except Exception as e:
        flash(f'Error decreasing fine: {e}', 'danger')
    finally:
        if 'conn' in locals() and conn.open: conn.close()
    return redirect(url_for('admin'))

@app.route('/admin/fine/set/<int:user_id>', methods=['POST'])
@login_required
def admin_set_fine(user_id):
    if current_user.role != 'admin': return redirect(url_for('browse'))
    amount = int(request.form.get('fine_amount', 0))
    if amount < 0: amount = 0
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("UPDATE users SET fine_count = %s WHERE id = %s", (amount, user_id))
            conn.commit()
            flash(f'Fine set to {amount}.', 'success')
    except Exception as e:
        flash(f'Error setting fine: {e}', 'danger')
    finally:
        if 'conn' in locals() and conn.open: conn.close()
    return redirect(url_for('admin'))


if __name__ == '__main__':
    app.run(debug=True, port=5000)
