# 🍽️ DishGennie — Premium Maid Booking Platform

A full-stack Django web application for booking professional home cooking services. Features separate dashboards for customers, maids, and administrators with real-time booking management, payment integration, and email OTP verification.

![Django](https://img.shields.io/badge/Django-5.2-green?logo=django)
![Python](https://img.shields.io/badge/Python-3.13-blue?logo=python)
![DRF](https://img.shields.io/badge/DRF-3.17-red)
![License](https://img.shields.io/badge/License-MIT-yellow)

## ✨ Features

### 👤 Customer Panel
- Browse & book verified maids
- Real-time booking tracking
- Wallet system for payments
- Rating & review system
- Notification center

### 👩‍🍳 Maid Panel
- Accept/reject booking requests
- Earnings dashboard
- Profile & availability management
- Navigation to customer location
- Review management

### 🔧 Admin Panel
- Dashboard with KPIs & charts (revenue, bookings, services)
- Maid verification (approve/reject with remarks)
- User & maid management
- Booking & payment oversight
- Analytics & reports
- Dispute resolution

### 🔐 Security
- Email OTP verification on registration
- JWT + Session dual authentication
- Role-based access control (Customer, Maid, Admin)
- CSRF protection on all forms

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- pip

### Installation

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/DishGennie.git
cd DishGennie

# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate
# Activate (Mac/Linux)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Setup environment variables
cp .env.example .env
# Edit .env with your credentials

# Run migrations
python manage.py migrate

# Create admin user & seed data
python manage.py shell -c "
from apps.accounts.models import CustomUser
from apps.services.models import ServiceCategory, City
CustomUser.objects.create_superuser(username='admin', password='admin123', email='admin@dishgennie.com', first_name='Admin', last_name='User', role='admin')
for name, state in [('Mumbai','Maharashtra'),('Delhi','Delhi'),('Bangalore','Karnataka'),('Pune','Maharashtra')]:
    City.objects.create(name=name, state=state)
for name in ['Home Cooking','Deep Cleaning','Meal Prep','Party Cooking','Tiffin Service']:
    ServiceCategory.objects.create(name=name, base_price=500)
print('Setup complete!')
"

# Run the server
python manage.py runserver
```

### Access the app
- **Home**: http://127.0.0.1:8000/
- **Login**: http://127.0.0.1:8000/accounts/login/
- **Admin**: username `admin`, password `admin123`

## 📧 Email OTP Setup (Gmail)

1. Create a Gmail account (e.g., `yourapp@gmail.com`)
2. Enable [2-Step Verification](https://myaccount.google.com/security)
3. Generate an [App Password](https://myaccount.google.com/apppasswords)
4. Update `.env`:
```env
EMAIL_HOST_USER=yourapp@gmail.com
EMAIL_HOST_PASSWORD=your-16-char-app-password
```

## 📁 Project Structure

```
DishGennie/
├── apps/
│   ├── accounts/       # User auth, profiles, OTP verification
│   ├── bookings/       # Booking CRUD & management
│   ├── notifications/  # Real-time notification system
│   ├── payments/       # Wallet & payment processing
│   ├── reviews/        # Rating & review system
│   ├── services/       # Service categories & cities
│   ├── support/        # Customer support tickets
│   ├── analytics/      # Admin analytics & reports
│   └── tracking/       # Live booking tracking
├── templates/
│   ├── accounts/       # Login, signup, OTP verification
│   ├── user/           # Customer dashboard & pages
│   ├── maid/           # Maid dashboard & pages
│   └── admin_panel/    # Admin dashboard & management
├── static/
│   ├── css/            # Base, components, page-specific styles
│   └── js/             # Core app.js with API client & utilities
├── dishgennie/         # Django project settings
├── requirements.txt
├── Procfile            # Deployment config
└── runtime.txt         # Python version
```

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Django 5.2, Django REST Framework |
| Frontend | HTML5, CSS3, JavaScript (Vanilla) |
| Auth | JWT (SimpleJWT) + Django Sessions |
| Charts | Chart.js |
| Icons | Bootstrap Icons |
| UI Framework | Bootstrap 5 |
| Email | Gmail SMTP |
| Database | SQLite (dev) / PostgreSQL (prod) |

## 🌐 Deployment

The project includes `Procfile` and `runtime.txt` for easy deployment on **Render**, **Railway**, or **Heroku**.

```bash
# Production settings
DEBUG=False
ALLOWED_HOSTS=your-domain.com
DATABASE_URL=postgresql://...
```

## 📄 License

This project is licensed under the MIT License.

## 👨‍💻 Author

**Alok Vikram** — Built with ❤️
