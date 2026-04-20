# 🗄️ Shelf — MySQL Database Guide

A comprehensive guide to the **`shelf_db`** database powering the Shelf Library Management System.  
This document covers the schema design, table structures, relationships, constraints, and sample queries.

---

## 📊 Database Overview

| Property         | Value           |
| ---------------- | --------------- |
| Database Name    | `shelf_db`      |
| Engine           | InnoDB (MySQL)  |
| Character Set    | utf8mb4         |
| Total Tables     | 4               |
| Pre-seeded Books | 151             |
| Genres Covered   | 19              |

---

## 🏗️ Entity-Relationship Diagram

```
┌──────────────────────┐
│        users         │
├──────────────────────┤
│ PK  id          INT  │
│     name     VARCHAR │
│ UQ  email    VARCHAR │
│     password VARCHAR │
│     role       ENUM  │
└──────┬───────┬───────┘
       │       │
       │       │  1:N (One user → Many transactions)
       │       │
       │       ▼
       │  ┌──────────────────────────┐        ┌──────────────────────────┐
       │  │      transactions        │        │         books            │
       │  ├──────────────────────────┤        ├──────────────────────────┤
       │  │ PK  id            INT    │        │ PK  id            INT    │
       │  │ FK  user_id       INT  ──┼── ← ──┤     title       VARCHAR  │
       │  │ FK  book_id       INT  ──┼── → ──┤     author      VARCHAR  │
       │  │     borrow_date   DATE   │        │     genre       VARCHAR  │
       │  │     due_date      DATE   │        │     total_copies   INT   │
       │  │     return_date   DATE   │        │     available_copies INT │
       │  │     status        ENUM   │        └──────────────────────────┘
       │  └──────────────────────────┘
       │
       │  1:N (One user → Many book requests)
       │
       ▼
  ┌──────────────────────────┐
  │     book_requests        │
  ├──────────────────────────┤
  │ PK  id            INT    │
  │ FK  user_id       INT    │
  │     title       VARCHAR  │
  │     author      VARCHAR  │
  │     request_date  DATE   │
  │     status        ENUM   │
  └──────────────────────────┘
```

### Relationships Summary

| Relationship            | Type | Description                                      |
| ----------------------- | ---- | ------------------------------------------------ |
| `users` → `transactions`   | 1:N  | One user can have many borrow transactions       |
| `books` → `transactions`   | 1:N  | One book can appear in many transactions         |
| `users` → `book_requests`  | 1:N  | One user can submit many book requests           |

---

## 📑 Table Definitions

### 1. `users` — Stores all registered user accounts

| Column     | Type            | Constraints           | Description                              |
| ---------- | --------------- | --------------------- | ---------------------------------------- |
| `id`       | `INT`           | `PRIMARY KEY`, `AUTO_INCREMENT` | Unique user identifier          |
| `name`     | `VARCHAR(100)`  | —                     | User's display name                      |
| `email`    | `VARCHAR(150)`  | `UNIQUE`              | User's email (used for login)            |
| `password` | `VARCHAR(255)`  | —                     | Hashed password (Werkzeug scrypt)        |
| `role`     | `ENUM('user','admin')` | `DEFAULT 'user'` | Determines access level                  |

**Key Points:**
- Passwords are **never stored in plain text** — they use Werkzeug's `scrypt` hashing algorithm
- The `email` column has a `UNIQUE` constraint to prevent duplicate accounts
- Only two roles exist: `user` (default) and `admin`
- The seeded admin account is: `admin@shelf.com` / `admin123`

```sql
CREATE TABLE users (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(100),
  email VARCHAR(150) UNIQUE,
  password VARCHAR(255),
  role ENUM('user','admin') DEFAULT 'user'
);
```

---

### 2. `books` — Stores the library's book catalog

| Column             | Type           | Constraints           | Description                         |
| ------------------ | -------------- | --------------------- | ----------------------------------- |
| `id`               | `INT`          | `PRIMARY KEY`, `AUTO_INCREMENT` | Unique book identifier     |
| `title`            | `VARCHAR(200)` | —                     | Book title                          |
| `author`           | `VARCHAR(150)` | —                     | Author name                         |
| `genre`            | `VARCHAR(80)`  | —                     | Book genre/category                 |
| `total_copies`     | `INT`          | `DEFAULT 1`           | Total copies owned by the library   |
| `available_copies` | `INT`          | `DEFAULT 1`           | Currently available (not borrowed)  |

**Key Points:**
- `available_copies` is **decremented** when a book is borrowed and **incremented** when returned
- `total_copies` represents the library's total inventory for that title
- The availability badge shown on the UI is calculated as `available_copies / total_copies`
- 151 books are pre-seeded across 19 genres

```sql
CREATE TABLE books (
  id INT AUTO_INCREMENT PRIMARY KEY,
  title VARCHAR(200),
  author VARCHAR(150),
  genre VARCHAR(80),
  total_copies INT DEFAULT 1,
  available_copies INT DEFAULT 1
);
```

**Genre Distribution (Seeded Data):**

| Genre               | Titles | Total Copies |
| ------------------- | ------ | ------------ |
| Sci-Fi              | 21     | 76           |
| Fantasy             | 20     | 81           |
| Technology          | 20     | 69           |
| Historical Fiction  | 16     | 57           |
| Classic             | 15     | 51           |
| Philosophy          | 12     | 33           |
| Psychology          | 12     | 50           |
| Fiction             | 8      | 37           |
| Thriller            | 7      | 30           |
| Mystery             | 7      | 30           |
| Dystopian           | 4      | 16           |
| Epic                | 2      | 4            |
| Romance             | 1      | 3            |
| Horror              | 1      | 3            |
| Adventure           | 1      | 4            |
| Philosophical Fiction | 1   | 4            |
| Non-Fiction         | 1      | 6            |
| True Crime          | 1      | 3            |
| Magical Realism     | 1      | 4            |

---

### 3. `transactions` — Tracks book borrow/return activity

| Column        | Type                                          | Constraints           | Description                                |
| ------------- | --------------------------------------------- | --------------------- | ------------------------------------------ |
| `id`          | `INT`                                         | `PRIMARY KEY`, `AUTO_INCREMENT` | Unique transaction ID             |
| `user_id`     | `INT`                                         | `FOREIGN KEY → users(id)` | The borrowing user                     |
| `book_id`     | `INT`                                         | `FOREIGN KEY → books(id)` | The borrowed book                      |
| `borrow_date` | `DATE`                                        | —                     | Date the borrow was initiated              |
| `due_date`    | `DATE`                                        | —                     | Deadline for return (borrow_date + 14 days)|
| `return_date` | `DATE`                                        | —                     | Actual return date (`NULL` until returned) |
| `status`      | `ENUM('pending','borrowed','returned','rejected')` | `DEFAULT 'pending'` | Current state of the transaction      |

**Key Points:**
- When a user borrows a book, the transaction starts with status `'pending'`
- An admin must **approve** the transaction (status → `'borrowed'`) before the user can return it
- If rejected, the admin sets status → `'rejected'` and the book's `available_copies` is restored
- `return_date` remains `NULL` until the book is returned
- Both foreign keys use `ON DELETE CASCADE` — deleting a user or book removes associated transactions

```sql
CREATE TABLE transactions (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT,
  book_id INT,
  borrow_date DATE,
  due_date DATE,
  return_date DATE,
  status ENUM('pending','borrowed','returned','rejected') DEFAULT 'pending',
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
);
```

**Transaction Status Flow:**

```
  ┌─────────┐     Admin Approves     ┌──────────┐     User Returns     ┌──────────┐
  │ PENDING │ ──────────────────────► │ BORROWED │ ───────────────────► │ RETURNED │
  └─────────┘                         └──────────┘                      └──────────┘
       │
       │  Admin Rejects
       ▼
  ┌──────────┐
  │ REJECTED │  (available_copies restored)
  └──────────┘
```

---

### 4. `book_requests` — User-submitted requests for new books

| Column         | Type                                     | Constraints           | Description                             |
| -------------- | ---------------------------------------- | --------------------- | --------------------------------------- |
| `id`           | `INT`                                    | `PRIMARY KEY`, `AUTO_INCREMENT` | Unique request ID              |
| `user_id`      | `INT`                                    | `FOREIGN KEY → users(id)` | The requesting user                 |
| `title`        | `VARCHAR(200)`                           | `NOT NULL`            | Requested book title                    |
| `author`       | `VARCHAR(150)`                           | —                     | Requested book author (optional)        |
| `request_date` | `DATE`                                   | —                     | Date the request was submitted          |
| `status`       | `ENUM('pending','approved','rejected')`  | `DEFAULT 'pending'`   | Admin decision on the request           |

**Key Points:**
- Users can request books that aren't in the library yet
- Admins can **approve**, **reject**, or **delete** requests from the admin dashboard
- The `title` column is the only `NOT NULL` field (author is optional)
- Uses `ON DELETE CASCADE` with `users` — if a user is deleted, their requests are also removed

```sql
CREATE TABLE book_requests (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT,
  title VARCHAR(200) NOT NULL,
  author VARCHAR(150),
  request_date DATE,
  status ENUM('pending','approved','rejected') DEFAULT 'pending',
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
```

---

## 🔗 Foreign Key Constraints

| Constraint Name         | Table            | Column     | References        | On Delete  |
| ----------------------- | ---------------- | ---------- | ----------------- | ---------- |
| `transactions_ibfk_1`   | `transactions`   | `user_id`  | `users(id)`       | `CASCADE`  |
| `transactions_ibfk_2`   | `transactions`   | `book_id`  | `books(id)`       | `CASCADE`  |
| `book_requests_ibfk_1`  | `book_requests`  | `user_id`  | `users(id)`       | `CASCADE`  |

**CASCADE behavior:** When a parent row is deleted (e.g., a user or book), all child rows referencing it are automatically deleted. This prevents orphaned records.

---

## 🔄 Transaction Lifecycle (How Borrowing Works)

Below is the step-by-step flow of a borrow-return cycle and what happens in the database at each stage:

### Step 1 — User Requests to Borrow
```sql
-- A new transaction is created with 'pending' status
INSERT INTO transactions (user_id, book_id, borrow_date, due_date, status)
VALUES (3, 42, '2026-04-20', '2026-05-04', 'pending');

-- The book's available copies are decremented immediately
UPDATE books SET available_copies = available_copies - 1 WHERE id = 42;
```

### Step 2 — Admin Approves
```sql
-- Status changes from 'pending' to 'borrowed'
UPDATE transactions SET status = 'borrowed' WHERE id = 1;
```

### Step 3 — User Returns the Book
```sql
-- Status changes to 'returned' and return_date is recorded
UPDATE transactions SET status = 'returned', return_date = '2026-05-01' WHERE id = 1;

-- The book's available copies are restored
UPDATE books SET available_copies = available_copies + 1 WHERE id = 42;
```

### Alternative — Admin Rejects
```sql
-- Status changes to 'rejected'
UPDATE transactions SET status = 'rejected' WHERE id = 1;

-- The book's available copies are restored (since they were decremented at request time)
UPDATE books SET available_copies = available_copies + 1 WHERE id = 42;
```

---

## 📝 Useful Sample Queries

### View all books with their availability
```sql
SELECT id, title, author, genre,
       available_copies, total_copies,
       CONCAT(available_copies, '/', total_copies) AS availability
FROM books
ORDER BY title;
```

### View all active borrows (not yet returned)
```sql
SELECT t.id AS transaction_id,
       u.name AS borrower,
       b.title AS book,
       t.borrow_date,
       t.due_date,
       t.status
FROM transactions t
JOIN users u ON t.user_id = u.id
JOIN books b ON t.book_id = b.id
WHERE t.status IN ('pending', 'borrowed')
ORDER BY t.borrow_date DESC;
```

### View overdue books
```sql
SELECT u.name, u.email, b.title,
       t.due_date,
       DATEDIFF(CURDATE(), t.due_date) AS days_overdue
FROM transactions t
JOIN users u ON t.user_id = u.id
JOIN books b ON t.book_id = b.id
WHERE t.status = 'borrowed'
  AND t.due_date < CURDATE();
```

### Count books by genre
```sql
SELECT genre,
       COUNT(*) AS titles,
       SUM(total_copies) AS total_copies,
       SUM(available_copies) AS available_copies
FROM books
GROUP BY genre
ORDER BY titles DESC;
```

### View all pending book requests
```sql
SELECT r.id, u.name, u.email,
       r.title, r.author,
       r.request_date, r.status
FROM book_requests r
JOIN users u ON r.user_id = u.id
WHERE r.status = 'pending'
ORDER BY r.request_date DESC;
```

### Find a user's complete borrowing history
```sql
SELECT b.title, b.author,
       t.borrow_date, t.due_date, t.return_date, t.status
FROM transactions t
JOIN books b ON t.book_id = b.id
WHERE t.user_id = 1
ORDER BY t.borrow_date DESC;
```

---

## 🗃️ Resetting the Database

To completely reset the database (drop all data, recreate tables, and re-seed):

```bash
python init_db.py
```

Or manually via MySQL:

```sql
SOURCE schema.sql;
```

> ⚠️ **Warning:** This will destroy all existing data including user accounts and transaction history.

---

## 📐 Schema Design Decisions

| Decision                                | Rationale                                                         |
| --------------------------------------- | ----------------------------------------------------------------- |
| `ENUM` for status fields                | Restricts values to a known set, prevents invalid states          |
| `ON DELETE CASCADE` on all foreign keys | Ensures referential integrity — no orphaned transactions/requests |
| `UNIQUE` on `users.email`               | Prevents duplicate registrations with the same email              |
| Separate `total_copies` and `available_copies` | Allows tracking inventory vs. current availability          |
| `book_requests` as a separate table     | Decouples user requests from the actual book catalog              |
| No ORM (raw SQL via PyMySQL)            | Keeps queries explicit and easy to understand for academic use    |
| `VARCHAR` for `genre` (not ENUM)        | Allows flexible genre additions without schema migration          |

---

## 🔒 Security Notes

- Passwords are hashed using **Werkzeug's `scrypt`** algorithm — never stored in plain text
- SQL queries use **parameterized statements** (`%s` placeholders) to prevent SQL injection
- Admin routes are protected with role checks (`current_user.role != 'admin'`)
- Sessions are managed by **Flask-Login** with a server-side secret key
