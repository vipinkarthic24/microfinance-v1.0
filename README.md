# SV Fincloud - Microfinance ERP System

A complete, working microfinance ERP software for loan management with multi-role access control.

## 🎯 Features

### Multi-Role System (5 Roles)
- **Customer**: Apply for loans, view status, check EMI schedules
- **Collection Agent**: View assigned customers, collect EMI payments
- **Finance Officer**: Approve loans, approve payments, manage workflow
- **Admin**: User management, branch management, system configuration
- **Auditor**: Read-only access to all records and audit logs

### Loan Types
1. **Personal Loan** - Interest based on CIBIL score
   - CIBIL ≥ 750: 12% interest
   - CIBIL 700-749: 15% interest
   - CIBIL < 700: Rejected

2. **Vehicle Loan** - Interest based on vehicle age
   - ≤ 3 years: 11% interest
   - 4-6 years: 13% interest
   - > 6 years: 15% interest

3. **Gold Loan** - 10% flat interest
   - Loan amount: 70% of gold value
   - Gold rate configurable by admin

### Business Logic
- Flat interest EMI calculation
- Processing fee: 5% (deducted from disbursed amount)
- EMI = (Principal + Flat Interest) / Tenure
- Automatic EMI schedule generation on loan approval
- Outstanding balance auto-updates after payment approval

## 🚀 Technology Stack

- **Backend**: Python FastAPI
- **Database**: SQLite
- **Frontend**: React + Tailwind CSS
- **Authentication**: JWT tokens with bcrypt password hashing

## 📦 Database Schema

Tables created automatically on first run:
- `users` - User accounts with role-based access
- `customers` - Customer profiles with CIBIL scores
- `loans` - Loan applications and details
- `emi_schedule` - EMI payment schedules
- `payments` - Payment records and approvals
- `branches` - SV Fincloud branch locations
- `loan_types` - Available loan products
- `interest_rates` - Configurable interest rates
- `gold_rate` - Daily gold rate for gold loans
- `penalties` - Penalty records for missed EMIs
- `audit_logs` - Complete audit trail

## 🔐 Test Accounts

All accounts are pre-configured for immediate testing:

| Username | Password | Role |
|----------|----------|------|
| admin | admin123 | Admin |
| finance_officer | officer123 | Finance Officer |
| collection_agent | agent123 | Collection Agent |
| customer | customer123 | Customer |
| auditor | auditor123 | Auditor |

## 🎬 Getting Started

The system is already running! Simply:

1. **Access the application**: Open your browser to the frontend URL
2. **Login**: Use any of the test accounts above
3. **Navigate**: Based on your role, you'll see a different dashboard

## 📋 Complete Workflow

### 1. Customer applies for loan
- Login as **customer**
- Click "Apply for New Loan"
- Select loan type and enter details
- Submit application

### 2. Finance Officer approves loan
- Login as **finance_officer**
- Go to "Loan Applications"
- Review application details
- Click "Approve" (EMI schedule auto-generated)

### 3. Collection Agent collects payment
- Login as **collection_agent**
- View "Assigned Customers"
- Click customer's "View EMIs"
- Click "Collect Payment" for pending EMI
- Enter amount and submit (status: PENDING)

### 4. Finance Officer approves payment
- Login as **finance_officer**
- Go to "Pending Payments"
- Review payment details
- Click "Approve" (outstanding balance auto-updates)

### 5. Customer views payment
- Login as **customer**
- View loan details
- Check EMI schedule (status: PAID)
- View payment history

## 👨‍💼 Admin Features

### User Management
- Create users for all roles
- For customers: capture name, email, phone, CIBIL score
- Automatic password hashing with bcrypt

### Branch Management
- Create and manage SV Fincloud branches
- Multi-tenancy support with tenant_id

### Configuration
- **Interest Rates**: Update rates for all loan types and categories
- **Gold Rate**: Set daily gold rate per gram
- **Dashboard**: View system-wide statistics
  - Total users and customers
  - Pending and approved loans
  - Total disbursed amount
  - Outstanding balance

## 🔍 Auditor Features

Read-only access to:
- All loan records with customer details
- All payment records with approval status
- Complete audit logs with user actions
- System activity timeline

## 🛡️ Security Features

- JWT-based authentication
- Password hashing with bcrypt
- Role-based access control
- Protected API endpoints
- Audit logging for all actions

## 📊 Business Calculations

### EMI Calculation (Flat Interest)
```
Total Interest = (Principal × Interest Rate × Tenure) / (100 × 12)
Total Amount = Principal + Total Interest
EMI Amount = Total Amount / Tenure
```

### Processing Fee
```
Processing Fee = Loan Amount × 5%
Disbursed Amount = Loan Amount - Processing Fee
```

### Gold Loan Validation
```
Max Loan Amount = Gold Weight (grams) × Gold Rate × 0.70
```

## 🏗️ Architecture

### Backend Structure
- `server.py` - Main FastAPI application with all routes
- SQLite database with auto-initialization
- RESTful API with /api prefix for all endpoints
- CORS configured for frontend access

### Frontend Structure
- `App.js` - Main routing and authentication
- `pages/Login.js` - Login page
- `pages/CustomerDashboard.js` - Customer interface
- `pages/CollectionAgentDashboard.js` - Agent interface
- `pages/FinanceOfficerDashboard.js` - Officer interface
- `pages/AdminDashboard.js` - Admin interface
- `pages/AuditorDashboard.js` - Auditor interface
- `App.css` - Professional corporate styling

## 🔌 API Endpoints

### Authentication
- `POST /api/auth/login` - User login
- `GET /api/auth/me` - Get current user

### Customer
- `POST /api/customer/loan-application` - Apply for loan
- `GET /api/customer/loans` - Get customer loans
- `GET /api/customer/emi-schedule/{loan_id}` - Get EMI schedule
- `GET /api/customer/payment-history/{loan_id}` - Get payment history

### Collection Agent
- `GET /api/agent/customers` - Get assigned customers
- `POST /api/agent/enter-payment` - Enter EMI payment

### Finance Officer
- `GET /api/officer/loan-applications` - Get pending applications
- `POST /api/officer/approve-loan` - Approve/reject loan
- `GET /api/officer/pending-payments` - Get pending payments
- `POST /api/officer/approve-payment` - Approve/reject payment

### Admin
- `POST /api/admin/create-user` - Create new user
- `GET /api/admin/users` - Get all users
- `POST /api/admin/create-branch` - Create branch
- `GET /api/admin/branches` - Get all branches
- `POST /api/admin/update-interest-rate` - Update interest rate
- `GET /api/admin/interest-rates` - Get all rates
- `POST /api/admin/update-gold-rate` - Update gold rate
- `GET /api/admin/gold-rate` - Get current gold rate
- `GET /api/admin/stats` - Get dashboard statistics

### Auditor
- `GET /api/auditor/loans` - Get all loans
- `GET /api/auditor/payments` - Get all payments
- `GET /api/auditor/audit-logs` - Get audit logs

## 📝 Database Location

SQLite database file: `/app/backend/sv_fincloud.db`

## ✨ Key Highlights

✅ **Real Software** - Not documentation, fully functional ERP
✅ **Database Connected** - SQLite with all tables and relationships
✅ **Multi-User** - 5 different roles with separate dashboards
✅ **Complete Workflow** - End-to-end loan lifecycle management
✅ **Business Logic** - CIBIL validation, interest calculation, EMI generation
✅ **Professional UI** - Clean, corporate design suitable for finance
✅ **Security** - JWT authentication, password hashing, role-based access
✅ **Audit Trail** - Complete logging of all system actions
✅ **Production Ready** - Error handling, validation, proper architecture

## 🎓 Academic/Demo Ready

This system is perfect for:
- Academic projects and demonstrations
- Learning microfinance operations
- Understanding ERP workflows
- Role-based application development
- Full-stack development showcase

## 📞 Support

For questions or issues:
- Check the test accounts above
- Review the complete workflow section
- Verify database is initialized correctly
- Ensure both frontend and backend are running

---

**SV Fincloud** - Professional Microfinance ERP System
Built with FastAPI, React, and SQLite
