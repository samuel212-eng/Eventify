# ⚡ Eventify — Django Event Website

A full-featured event management website built with Django, Bootstrap 5, and plain HTML/CSS. 

---

## What it does

- 🎉 **Browse events** — search, filter by category, see availability
- ✍️ **Create events** — upload a banner image, set price, capacity, date
- ✏️ **Edit & Delete** — full CRUD for event organisers
- 🎟️ **Register** — sign up for events, view your tickets, cancel anytime
- 🔐 **Authentication** — sign up, log in, log out (built into Django)
- 🛠️ **Admin panel** — manage everything at /admin

---

## How to run it

### Step 1 — Make sure you have Python 3.8+
```
python --version
```

### Step 2 — Run the setup script (only once)
```
python setup.py
```
This will:
- Install Django and Pillow
- Create the database
- Add sample categories
- Ask you to create an admin account

### Step 3 — Start the development server
```
python manage.py runserver
```

### Step 4 — Open your browser
- **Website:**    http://127.0.0.1:8000
- **Admin panel:** http://127.0.0.1:8000/admin

---

## Project layout (what each file does)

```
eventsite/
│
├── manage.py              ← The main command-line tool
├── setup.py               ← One-time setup helper
│
├── eventsite/             ← Project configuration
│   ├── settings.py        ← All site settings (database, apps, etc.)
│   └── urls.py            ← Master URL list (address book)
│
├── events/                ← Our app (all the real code)
│   ├── models.py          ← Database tables (Event, Registration, Category)
│   ├── views.py           ← One function per page
│   ├── forms.py           ← HTML forms
│   ├── urls.py            ← URLs for this app
│   ├── admin.py           ← What shows up in /admin
│   └── templates/events/  ← HTML files for event pages
│
├── templates/             ← Shared HTML files
│   ├── base.html          ← Master layout (navbar, footer)
│   └── registration/      ← Login & signup pages
│
├── static/                ← CSS, JS, images
├── media/                 ← Uploaded event images (auto-created)
└── db.sqlite3             ← The database file (auto-created)
```

---

## How CRUD works (simple explanation)

| Action | URL | Who can do it |
|--------|-----|---------------|
| **C**reate | /events/create/ | Logged-in users |
| **R**ead | /events/ and /events/1/ | Everyone |
| **U**pdate | /events/1/edit/ | Event organiser only |
| **D**elete | /events/1/delete/ | Event organiser only |

---

## Tech used

| Tool | What it does |
|------|-------------|
| **Django** | The Python web framework — handles everything |
| **SQLite** | The database — a simple file, no install needed |
| **Bootstrap 5** | CSS framework — makes things look good fast |
| **Pillow** | Python library for handling image uploads |
| **Google Fonts** | Beautiful typography (Syne + DM Sans) |

---

## Going live (production checklist)

1. Change `SECRET_KEY` in settings.py to something random
2. Set `DEBUG = False`
3. Set `ALLOWED_HOSTS = ['yourdomain.com']`
4. Use PostgreSQL instead of SQLite
5. Serve static files with WhiteNoise or a CDN
