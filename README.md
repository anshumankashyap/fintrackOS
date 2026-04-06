# Finance Data Processing and Access Control Backend

## Overview
Finance Data Processing and Access Control Backend is a backend system designed to manage financial transaction records while enforcing strict role-based access control. The system provides secure APIs to create, read, update, and delete financial records, along with analytical dashboard summaries.

This project demonstrates backend development skills including API design, authentication, authorization, data validation, database modeling, and business logic implementation.

The system is designed for financial analysts and administrators who need to process financial data efficiently while maintaining strict permission control.

---

## Key Features

### 1. Financial Transaction Management
The system allows authorized users to manage financial records such as income and expenses.

Each transaction includes:
- Title
- Category
- Amount
- Transaction Type (Income / Expense)
- Date
- Description (required for transactions above 10000)

Supported operations:
- Create transaction
- View transactions
- Update transaction
- Delete transaction

---

### 2. Role Based Access Control (RBAC)

The application implements three user roles:

#### Viewer
- Can view financial transactions
- Can view dashboard summaries
- Cannot create, update, or delete data

#### Analyst
- Can create transactions
- Can update transactions
- Can view financial reports
- Cannot delete transactions

#### Admin
- Full system access
- Create transactions
- Update transactions
- Delete transactions
- Manage all financial records

---

### 3. Financial Dashboard APIs

The backend provides analytics APIs that summarize financial data.

Supported summaries include:

- Total Income
- Total Expenses
- Net Balance
- Monthly Reports
- Annual Reports
- Category-wise expense breakdown

These endpoints allow frontends to display financial dashboards and charts.

---

### 4. Data Validation

The system ensures data integrity using validation rules:

- Amount must be a positive number
- Title is required
- Category must be valid
- Date must follow correct format
- Description required for transactions above 10000

Invalid requests return proper error messages.

---

### 5. Secure API Access

Authentication and authorization are implemented to ensure only permitted users can access sensitive financial data.

Security measures include:

- Role-based permission checks
- Protected API endpoints
- Controlled access to financial operations

---

## Technology Stack

Backend Framework:
- Python
- Django
- Django REST Framework

Database:
- SQLite (development)
- PostgreSQL (production ready)

Authentication:
- Token based authentication

Other Tools:
- Git
- Postman (API testing)

---

## Project Structure

```
finance_backend/
│
├── finance_backend/
│   ├── settings/
│   │   ├── base.py
│   │   ├── development.py
│   │   └── production.py
│   │
│   ├── urls.py
│   └── wsgi.py
│
├── transactions/
│   ├── models.py
│   ├── serializers.py
│   ├── views.py
│   ├── permissions.py
│   ├── urls.py
│   └── services.py
│
├── users/
│   ├── models.py
│   ├── views.py
│   ├── serializers.py
│   └── urls.py
│
├── dashboard/
│   ├── views.py
│   ├── services.py
│   └── urls.py
│
├── manage.py
└── requirements.txt
```

---

## API Endpoints

### Authentication

```
POST /api/auth/login
POST /api/auth/register
POST /api/auth/logout
```

---

### Transactions

Create Transaction

```
POST /api/transactions/
```

Get All Transactions

```
GET /api/transactions/
```

Update Transaction

```
PUT /api/transactions/{id}
```

Delete Transaction (Admin only)

```
DELETE /api/transactions/{id}
```

---

### Dashboard

Financial Summary

```
GET /api/dashboard/summary
```

Monthly Report

```
GET /api/dashboard/monthly
```

Annual Report

```
GET /api/dashboard/yearly
```

Category Breakdown

```
GET /api/dashboard/categories
```

---

## Installation Guide

### 1. Clone the Repository

```
git clone https://github.com/your-username/finance-data-backend.git
cd finance-data-backend
```

---

### 2. Create Virtual Environment

```
python -m venv venv
```

Activate environment

Windows:
```
venv\Scripts\activate
```

Mac/Linux:
```
source venv/bin/activate
```

---

### 3. Install Dependencies

```
pip install -r requirements.txt
```

---

### 4. Run Database Migrations

```
python manage.py makemigrations
python manage.py migrate
```

---

### 5. Create Superuser

```
python manage.py createsuperuser
```

---

### 6. Start Development Server

```
python manage.py runserver
```

Server will run at:

```
http://127.0.0.1:8000
```

---

## Example Transaction Data

Example financial records:

| Title | Category | Amount | Date | Type |
|------|------|------|------|------|
| Monthly Salary | Salary | 65000 | 2026-04-01 | Income |
| Freelance Web Development | Consulting | 12000 | 2026-04-02 | Income |
| Office Laptop Purchase | Equipment | 45000 | 2026-04-03 | Expense |
| Stock Investment Profit | Investment | 15000 | 2026-04-04 | Income |

---

## Error Handling

The API returns structured error responses.

Example:

```json
{
  "error": "Description is required for transactions above 10000"
}
```

---

## Future Improvements

Possible enhancements:

- Advanced financial analytics
- Data visualization dashboards
- Export reports (PDF / Excel)
- Multi-currency support
- Automated financial insights
- Audit logs for transactions

---

## Author

Ansuman Panda

Backend Developer

- Email: anshumaanpanda08@gmail.com
- LinkedIn: https://www.linkedin.com/in/ansumanpanda08/
- GitHub: https://www.github.com/anshumankashyap