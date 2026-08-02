# DishGennie — System Architecture

**Domain:** dishgennie.adityadubey.co.in
**Hosting:** Vercel (Django, serverless)
**Database:** Neon (PostgreSQL) — production; migrated from local SQLite
**Type:** Progressive Web Application (PWA)
**Stack:** Django (with Django Templates)

---

## 1. Overview

DishGennie is a hyperlocal maid-recommendation and booking platform with three roles:

| Role  | Capability |
|-------|------------|
| **User**  | Discover nearby maids, book service, track maid's live location, verify arrival via OTP, make payment (UPI/cash) |
| **Maid**  | Register with QR/UPI details, get admin-verified, appear in nearby search once approved, share live location during active bookings, confirm payment received |
| **Admin** | Full platform access; verify and approve/reject maid registrations; receives notification on every new registration |

---

## 2. High-Level Architecture

```
                    ┌─────────────────────────────┐
                    │        Vercel (Django)       │
                    │                               │
   Browser/PWA ───▶ │  Django Views + Templates     │◀─── Static/PWA assets
   (User/Maid/Admin)│  Django REST-style endpoints  │      (manifest.json,
                    │  for polling & AJAX calls     │       service worker)
                    └───────────┬───────────────────┘
                                │
                 ┌──────────────┼──────────────────┐
                 │              │                  │
                 ▼              ▼                  ▼
          ┌────────────┐ ┌────────────┐   ┌────────────────┐
          │   Neon     │ │  Brevo API  │   │  (Future)      │
          │  Postgres  │ │  (Email)    │   │  Payment GW /  │
          │            │ │             │   │  SMS Gateway   │
          └────────────┘ └────────────┘   └────────────────┘
```

---

## 3. Django App Structure

```
dishgennie/
├── accounts/          # Custom User model, role-based auth (user/maid/admin)
├── maids/             # MaidProfile, verification workflow, QR/UPI upload
├── bookings/          # Booking lifecycle, OTP generation & verification
├── tracking/          # Location POST (maid) + polling GET (user) endpoints
├── payments/          # Payment record, manual confirmation (UPI/cash)
├── notifications/     # Brevo email service wrapper
├── static/            # PWA assets: manifest.json, service-worker.js, icons
└── dishgennie/        # Project settings, urls, wsgi/asgi
```

---

## 4. Data Models (Summary)

### `accounts.User` (extends Django's AbstractUser)
| Field | Type | Notes |
|---|---|---|
| role | CharField (choices: user/maid/admin) | |
| phone_number | CharField | |
| email | EmailField | used for OTP + notifications |

### `maids.MaidProfile`
| Field | Type | Notes |
|---|---|---|
| user | OneToOne → User | |
| is_verified | Boolean | default False, set by admin |
| is_available | Boolean | toggled by maid |
| qr_code | ImageField | uploaded at registration |
| upi_id | CharField | uploaded at registration |
| current_lat / current_lng | FloatField | updated via polling endpoint |
| last_location_update | DateTimeField | staleness check |
| id_proof_doc | FileField (optional) | for verification |

### `bookings.Booking`
| Field | Type | Notes |
|---|---|---|
| user | FK → User | |
| maid | FK → MaidProfile | |
| status | CharField (pending/accepted/on_the_way/arrived/in_progress/completed/cancelled) | |
| otp | CharField (4-6 digit) | generated on booking confirm |
| otp_verified_at | DateTimeField (nullable) | |
| created_at / updated_at | DateTimeField | |

### `payments.Payment`
| Field | Type | Notes |
|---|---|---|
| booking | OneToOne → Booking | |
| method | CharField (upi/cash) | |
| amount | DecimalField | |
| status | CharField (pending/confirmed) | |
| confirmed_by_maid_at | DateTimeField (nullable) | manual confirmation |

---

## 5. Core Flow

1. **Maid Registration** → uploads QR code + UPI ID → status `is_verified=False`
   → Welcome email to maid + notification email to admin (via Brevo)
2. **Admin Verification** → admin reviews and approves/rejects in admin panel
   → only `is_verified=True` maids appear in nearby search
3. **User Registration** → welcome email to user + notification email to admin
4. **Booking**
   - User searches nearby available & verified maids (radius-based query on lat/lng)
   - User books a maid → `Booking` created, OTP generated
   - OTP sent to **user's email via Brevo**
5. **Live Tracking (Polling)**
   - Maid's phone/browser sends `POST /api/tracking/update/` every 5–10 seconds with current lat/lng
   - User's booking page calls `GET /api/tracking/status/<booking_id>/` every 5–10 seconds via `setInterval` + `fetch`
   - Frontend map/marker updates with each poll response
6. **Arrival & OTP Verification**
   - User shares the OTP verbally to the maid
   - Maid enters OTP in her app → `POST /api/bookings/<id>/verify-otp/`
   - On success, `status → in_progress`, `otp_verified_at` set
7. **Work Completion**
   - Maid/User marks work as completed → `status → completed`
8. **Payment**
   - **UPI path**: User redirected to maid's saved QR code page → pays via any UPI app → **maid manually clicks "Payment Received"** to confirm
   - **Cash path**: Maid clicks **"Collected Cash Payment"** → system displays the amount due → maid collects cash physically → confirms in-app
   - Either path ends with `Payment.status = confirmed`

---

## 6. Real-Time Location Tracking (Polling Approach)

Chosen over WebSockets/Django Channels because **Vercel serverless functions do not support persistent connections**.

### Endpoints
```
POST /api/tracking/update/
  Auth: Maid (session/token)
  Body: { "lat": 26.9124, "lng": 75.7873 }
  → Updates MaidProfile.current_lat/current_lng + last_location_update
  Called every 5-10s from maid's active booking page (JS geolocation watchPosition + interval POST)

GET /api/tracking/status/<booking_id>/
  Auth: User (session/token), must own the booking
  → Returns: { "lat": ..., "lng": ..., "updated_at": ..., "maid_status": "on_the_way" }
  Called every 5-10s from user's booking page via setInterval(fetch)
```

### Frontend Behavior
- Maid page: `navigator.geolocation.watchPosition()` → captures location → interval sends to backend
- User page: `setInterval` → fetch endpoint → update map marker (e.g., Leaflet/Google Maps)
- Polling stops automatically once `Booking.status` reaches `completed` or `cancelled`

---

## 7. Email Notifications (Brevo)

### Configuration
```python
BREVO_API_KEY = env("BREVO_API_KEY")
DEFAULT_FROM_EMAIL = "info@adityadubey.co.in"
ADMIN_EMAIL = "info@adityadubey.co.in"
```

### Triggered Emails
| Event | To | Purpose |
|---|---|---|
| Maid registers | Maid | Welcome email |
| Maid registers | Admin | New maid registration — review needed |
| User registers | User | Welcome email |
| User registers | Admin | New user registration notice |
| Booking confirmed | User | OTP for maid verification |

### Service Wrapper (`notifications/services.py`)
```python
def send_email(to_email, subject, html_content):
    # Calls Brevo transactional email API
    ...

def send_welcome_email(user):
    ...

def send_otp_email(booking):
    ...

def notify_admin(subject, message):
    send_email(settings.ADMIN_EMAIL, subject, message)
```

---

## 8. Payment Handling

- **No payment gateway integration** at this stage — both UPI and cash confirmations are **manual**, initiated by the maid.
- **UPI**: Static QR code (image) + UPI ID stored per maid at registration; displayed to user post-completion.
- **Cash**: System only displays the amount due; actual exchange happens offline; maid confirms via button click.
- `Payment.status` is a **record/log**, not a verified transaction — important limitation to communicate to stakeholders.

---

## 9. Database Migration: SQLite → Neon (Postgres)

```bash
# 1. Dump existing SQLite data
python manage.py dumpdata --natural-foreign --natural-primary \
    -e contenttypes -e auth.permission > data_dump.json

# 2. Update settings.py DATABASES to point to Neon Postgres
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("NEON_DB_NAME"),
        "USER": env("NEON_DB_USER"),
        "PASSWORD": env("NEON_DB_PASSWORD"),
        "HOST": env("NEON_DB_HOST"),
        "PORT": "5432",
        "OPTIONS": {"sslmode": "require"},
    }
}

# 3. Run migrations on Neon
python manage.py migrate

# 4. Load data into Neon
python manage.py loaddata data_dump.json
```

**Known gotchas:**
- Boolean/datetime field type mismatches between SQLite and Postgres may require manual fixes in the dump.
- Run `migrate` **before** `loaddata`, never after — order matters.
- If using auto-increment PKs, sequences may need reset post-load (`sqlsequencereset`).

---

## 10. PWA Conversion Requirements

- `manifest.json` — app name, icons, theme color, start_url, display: standalone
- `service-worker.js` — cache static assets, offline fallback page
- Registered in base template:
  ```html
  <link rel="manifest" href="{% static 'manifest.json' %}">
  <script>
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.register("{% static 'service-worker.js' %}");
    }
  </script>
  ```
- **Limitation to note:** Background location updates while the app/browser tab is not active are restricted on mobile browsers (especially iOS Safari). Polling works reliably only while the maid's booking page is open and active.

---

## 11. Open Items / Future Considerations

- SMS-based OTP (currently email-only via Brevo) — add later if email delivery proves unreliable for time-sensitive OTP.
- Automated UPI payment verification via a payment gateway (Razorpay/Cashfree) instead of manual confirmation.
- GeoDjango/PostGIS for more efficient "nearby maids" queries at scale (Neon supports PostGIS extension).
- Rating/review system for maids post-completion.
- Admin dashboard analytics (bookings, revenue, active maids).

---

**Document version:** 1.0
**Last updated:** August 2026
