# Renukambal Home Foods

A small Flask + SQLite ordering website with WhatsApp click-to-chat and a password-protected order dashboard.

## Features
- Product catalogue and variants
- Shopping cart
- Customer delivery details
- Order saved to SQLite before WhatsApp opens
- Unique order number
- Admin order list, search, status, tentative delivery date and remarks

## 1. Requirements
- Python 3.10+
- Visual Studio Code
- Git (for GitHub)

## 2. Open project
Open this folder in VS Code: `renukambal-home-foods`

## 3. Create virtual environment (Windows PowerShell)
```powershell
py -m venv .venv
.venv\\Scripts\\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If PowerShell blocks activation, use Command Prompt:
```cmd
.venv\\Scripts\\activate.bat
```

## 4. Configure
Copy `.env.example` to `.env`:
```powershell
Copy-Item .env.example .env
```
Edit `.env`:
- `WHATSAPP_NUMBER`: your business phone number with country code, digits only. Example: `919876543210`.
- Change `ADMIN_USERNAME` and `ADMIN_PASSWORD`.
- Change `SECRET_KEY` to a long random value.

The app loads `.env` automatically only if you add the following at the top of `app.py` after imports:
```python
from dotenv import load_dotenv
load_dotenv()
```
(Recommended: add these two lines before reading environment variables.)

## 5. Configure products and prices
Edit `products.py`.
- Replace pack variants with the actual sizes you plan to sell.
- Replace `None` with actual numeric prices, e.g. `120`.
- Product photos are stored locally in `static/images/` so they remain consistent; replace these with your own product photos when available.

Until prices are entered, the website displays "Price on request" and the final amount is confirmed by the owner.

## 6. Run locally
```powershell
python app.py
```
Open:
- Customer website: http://127.0.0.1:5000
- Admin login: http://127.0.0.1:5000/admin/login
- Health check: http://127.0.0.1:5000/health

Default local admin login is read from `.env`. Change it before sharing the site.

## 7. Order tracking
When a customer submits checkout:
1. Flask validates the customer and cart details.
2. The order and line items are stored in `data/renukambal.db`.
3. The app creates a unique order number.
4. Browser redirects to WhatsApp with the order summary pre-filled.
5. Customer must press Send in WhatsApp.

An order saved in the database does not prove the WhatsApp message was sent. The admin dashboard initially marks all submissions as `New`.

## 8. Git and GitHub
Create a new empty repository on GitHub, then from this project folder:
```powershell
git init
git add .
git commit -m "Initial Renukambal Home Foods website"
git branch -M main
git remote add origin https://github.com/YOUR-GITHUB-USERNAME/renukambal-home-foods.git
git push -u origin main
```
Do not add `.env`, database files, or customer data to Git. `.gitignore` excludes them.

## Important before public launch
- Replace the placeholder WhatsApp number.
- Enter verified prices and pack sizes.
- Replace stock image URLs with photos you have rights to use.
- Change admin credentials and SECRET_KEY.
- Use HTTPS and secure cookies.
- Add database backups and a persistent database host before cloud deployment.
- Add stronger protections (CSRF protection, login rate limiting, backups, privacy notice) before accepting real customer data publicly.

## Hosting note
This version is designed for local development first. Do not deploy this SQLite database to a free Render web service: Render's free web service filesystem is ephemeral and local database changes can be lost on restarts/redeploys. For public deployment, move the database to a persistent managed database or choose a host with persistent storage.
