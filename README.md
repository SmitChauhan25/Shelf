# 📚 Shelf — Library Management System

A full-stack web application for managing a library's book catalog, user accounts, borrowing/returning transactions, and book requests. Built with **Flask**, **MySQL**, and **Jinja2** templates.

---

## 🧰 Tech Stack

| Layer      | Technology                          |
| ---------- | ----------------------------------- |
| Backend    | Python 3.10+, Flask 3.0             |
| Database   | MySQL 8.0+                          |
| ORM / DB   | PyMySQL (raw SQL, no ORM)           |
| Auth       | Flask-Login + Werkzeug password hashing |
| Frontend   | Jinja2 templates, vanilla CSS       |
| Fonts      | Google Fonts (Cormorant Garamond, IBM Plex Mono) |

---

## 📋 Requirements

### Software

| Requirement       | Minimum Version |
| ----------------- | --------------- |
| Python            | 3.10+           |
| MySQL Server      | 8.0+            |
| pip               | 21.0+           |
| Git *(optional)*  | Any             |

### Python Packages

Listed in `requirements.txt`:

```
Flask==3.0.0
Flask-Login==0.6.3
PyMySQL==1.1.0
Werkzeug==3.0.1
```

---

## 🚀 Local Setup (Step-by-Step)

### 1. Clone or Download the Project

```bash
git clone <repository-url>
cd lib-management
```

Or simply download and extract the ZIP into a folder.

### 2. Create a Virtual Environment

```bash
python -m venv venv
```

Activate it:

- **Windows (PowerShell):**
  ```powershell
  .\venv\Scripts\Activate.ps1
  ```
- **Windows (CMD):**
  ```cmd
  venv\Scripts\activate.bat
  ```
- **macOS / Linux:**
  ```bash
  source venv/bin/activate
  ```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure MySQL Credentials

Open `app.py` and update the database connection settings (lines 12–15) to match your local MySQL server:

```python
DB_HOST = 'localhost'
DB_USER = 'root'
DB_PASSWORD = 'YourPasswordHere'
DB_NAME = 'shelf_db'
```

Also update the same credentials in `init_db.py` (lines 6–8):

```python
host='localhost',
user='root',
password='YourPasswordHere',
```

### 5. Initialize the Database

Make sure your MySQL server is running, then execute:

```bash
python init_db.py
```

This will:
- Drop the existing `shelf_db` database (if it exists)
- Create a fresh `shelf_db` database
- Create all 4 tables (`users`, `books`, `transactions`, `book_requests`)
- Seed the database with 1 admin user and 151 books across 19 genres

### 6. Run the Application

```bash
python app.py
```

The app will start on **http://127.0.0.1:5000**

---

## 🔑 Default Credentials

| Role  | Email              | Password   |
| ----- | ------------------ | ---------- |
| Admin | `admin@shelf.com`  | `admin123` |

> New users can self-register via the **Sign Up** page. All new accounts are created with the `user` role by default.

---

## 📁 Folder Structure

```
lib-management/
├── app.py                  # Flask application (all routes & logic)
├── init_db.py              # Database initialization script
├── schema.sql              # Full SQL schema + seed data
├── requirements.txt        # Python dependencies
├── static/
│   ├── bg_hero_clean.png   # Hero background image
│   └── style.css           # Global stylesheet
├── templates/
│   ├── base.html           # Base layout (navbar, footer, flash messages)
│   ├── index.html          # Landing / home page
│   ├── login.html          # Login form
│   ├── signup.html         # Registration form
│   ├── browse.html         # Book catalog with genre filtering
│   ├── borrow.html         # Borrow confirmation page
│   ├── return.html         # Return confirmation page
│   ├── profile.html        # User profile & transaction history
│   ├── admin.html          # Admin dashboard (CRUD for all entities)
│   └── about.html          # About page
└── venv/                   # Python virtual environment (not committed)
```

---

## ✨ Features

### For Users
- **Browse Books** — View the full catalog with genre-based filtering
- **Borrow Books** — Request to borrow available books (14-day loan period)
- **Return Books** — Return borrowed books and view confirmation
- **Profile** — View borrowing history, pending/active/returned transactions
- **Request Books** — Submit requests for books not yet in the library

### For Admins
- **Manage Books** — Add, edit, and delete books from the catalog
- **Manage Users** — Add, edit roles, and delete user accounts
- **Approve/Reject Transactions** — Control the borrow approval workflow
- **Manage Book Requests** — Approve, reject, or delete user book requests

### System
- **Authentication** — Secure login/signup with hashed passwords (Werkzeug scrypt)
- **Role-Based Access** — Admin routes are protected; only `admin` role users can access the dashboard
- **Flash Messages** — User feedback for all actions (success, error, warnings)

---

## 🛑 Troubleshooting

| Problem                          | Solution                                                           |
| -------------------------------- | ------------------------------------------------------------------ |
| `ModuleNotFoundError: pymysql`   | Run `pip install -r requirements.txt` inside your virtual env      |
| `Access denied for user 'root'`  | Check `DB_PASSWORD` in `app.py` matches your MySQL root password   |
| `Unknown database 'shelf_db'`    | Run `python init_db.py` to create and seed the database            |
| App won't start on port 5000     | Check if another process is using port 5000, or change it in `app.py` |
| Admin login not working          | Re-run `python init_db.py` to reset the admin account              |

---

## 📄 License

This project is for educational / academic purposes.
