# Setup (Windows, PowerShell)

1. Clone the repo and enter the folder:
   ```powershell
   git clone https://github.com/byfahme/subscription-management-system.git
   cd subscription-management-system
   ```

2. Create and activate a virtual environment:
   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```
   If you see "running scripts is disabled", run this once and try again:
   ```powershell
   Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
   ```

3. Install the packages:
   ```powershell
   python -m pip install flask flask-sqlalchemy flask-login flask-mail python-dateutil itsdangerous
   ```

4. Load the demo data (creates `app.db`):
   ```powershell
   python seed.py
   ```

5. Start the app:
   ```powershell
   python app.py
   ```
   Then open http://127.0.0.1:5000 in your browser.

## Demo logins (local use only)

| Role     | Email                 | Password       |
|----------|-----------------------|----------------|
| Admin    | admin@brightloop.test | Admin@Pass1    |
| Staff    | staff@brightloop.test | Staff@Pass1    |
| Customer | customer1@example.com | Customer@Pass1 |

## Notes

- Public signup always creates a customer. Only an admin can add staff.
- Password reset emails need Gmail settings in `app.py`, read from environment variables. If email isn't configured, the reset link is printed in the terminal.
- `app.db` and `venv/` are never committed to GitHub.