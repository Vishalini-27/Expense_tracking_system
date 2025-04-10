import sqlite3
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
import os

class ExpenseTracker:
    def __init__(self, db_name="expense_tracker.db"):
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
        self.setup_database()
        self.email_config = {
            'sender': 'your_email@gmail.com',
            'password': os.getenv('EMAIL_PASSWORD')  # Use environment variable for security
        }

    def setup_database(self):
        # Create tables if they don't exist
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY,
                user_id INTEGER,
                amount REAL,
                category TEXT,
                description TEXT,
                date TEXT,
                shared_with TEXT DEFAULT ''
            )
        ''')
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS budgets (
                id INTEGER PRIMARY KEY,
                user_id INTEGER,
                category TEXT,
                amount REAL,
                month TEXT,
                alert_threshold REAL DEFAULT 0.1
            )
        ''')
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                email TEXT UNIQUE,
                name TEXT
            )
        ''')
        self.conn.commit()

    def add_user(self, email, name):
        """Add a new user to the system"""
        try:
            self.cursor.execute(
                "INSERT INTO users (email, name) VALUES (?, ?)",
                (email, name)
            )
            self.conn.commit()
            return self.cursor.lastrowid
        except sqlite3.IntegrityError:
            return self.get_user_id(email)

    def get_user_id(self, email):
        """Get user ID by email"""
        self.cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        result = self.cursor.fetchone()
        return result[0] if result else None

    def log_expense(self, user_id, amount, category, description, shared_with=None):
        """Log a new expense and check budget"""
        date = datetime.now().strftime("%Y-%m-%d")
        self.cursor.execute(
            "INSERT INTO expenses (user_id, amount, category, description, date, shared_with) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, amount, category, description, date, shared_with or '')
        )
        self.conn.commit()
        self.check_budget(user_id, category)

    def set_budget(self, user_id, category, amount, month, alert_threshold=0.1):
        """Set monthly budget for a category"""
        self.cursor.execute(
            "INSERT OR REPLACE INTO budgets (user_id, category, amount, month, alert_threshold) "
            "VALUES (?, ?, ?, ?, ?)",
            (user_id, category, amount, month, alert_threshold)
        )
        self.conn.commit()

    def check_budget(self, user_id, category):
        """Check if budget is exceeded and send alerts"""
        month = datetime.now().strftime("%Y-%m")
        self.cursor.execute(
            "SELECT amount, alert_threshold FROM budgets WHERE user_id = ? AND category = ? AND month = ?",
            (user_id, category, month)
        )
        budget_data = self.cursor.fetchone()
        
        if not budget_data:
            return
        
        budget, threshold = budget_data
        total_spent = self.get_monthly_spending(user_id, category, month)
        
        remaining_percent = (budget - total_spent) / budget
        if total_spent > budget:
            self.send_alert(user_id, category, "Budget exceeded", f"Spent {total_spent} over {budget}")
        elif remaining_percent <= threshold:
            self.send_alert(user_id, category, "Low budget warning", f"Only {remaining_percent*100:.1f}% remaining")

    def send_alert(self, user_id, category, subject, message):
        """Send email alert to user"""
        self.cursor.execute("SELECT email FROM users WHERE id = ?", (user_id,))
        email = self.cursor.fetchone()[0]
        
        msg = MIMEText(message)
        msg['Subject'] = f"Expense Tracker: {subject} - {category}"
        msg['From'] = self.email_config['sender']
        msg['To'] = email
        
        try:
            with smtplib.SMTP('smtp.gmail.com', 587) as server:
                server.starttls()
                server.login(self.email_config['sender'], self.email_config['password'])
                server.send_message(msg)
        except Exception as e:
            print(f"Failed to send email: {e}")

    def get_monthly_spending(self, user_id, category, month):
        """Calculate total spending for a month"""
        self.cursor.execute(
            "SELECT SUM(amount) FROM expenses WHERE user_id = ? AND category = ? AND date LIKE ?",
            (user_id, category, f"{month}%")
        )
        result = self.cursor.fetchone()[0]
        return result or 0.0

    def generate_report(self, user_id, month):
        """Generate monthly spending report"""
        self.cursor.execute(
            "SELECT category, SUM(amount) FROM expenses WHERE user_id = ? AND date LIKE ? GROUP BY category",
            (user_id, f"{month}%")
        )
        expenses = dict(self.cursor.fetchall())
        
        self.cursor.execute(
            "SELECT category, amount FROM budgets WHERE user_id = ? AND month = ?",
            (user_id, month)
        )
        budgets = dict(self.cursor.fetchall())
        
        report = f"Report for {month}\n"
        report += "Category | Spent | Budget | Status\n"
        report += "-" * 40 + "\n"
        
        for category in set(expenses.keys()) | set(budgets.keys()):
            spent = expenses.get(category, 0.0)
            budget = budgets.get(category, 0.0)
            status = "Under" if spent <= budget or budget == 0 else "Over"
            report += f"{category:10} | {spent:6.2f} | {budget:6.2f} | {status}\n"
        
        return report

# CLI Interface
def main():
    tracker = ExpenseTracker()
    
    while True:
        print("\n1. Add User\n2. Log Expense\n3. Set Budget\n4. View Report\n5. Exit")
        choice = input("Enter choice: ")
        
        if choice == "1":
            email = input("Email: ")
            name = input("Name: ")
            user_id = tracker.add_user(email, name)
            print(f"User created with ID: {user_id}")
            
        elif choice == "2":
            user_id = int(input("User ID: "))
            amount = float(input("Amount: "))
            category = input("Category: ")
            desc = input("Description: ")
            shared = input("Shared with (comma-separated emails, optional): ")
            tracker.log_expense(user_id, amount, category, desc, shared)
            
        elif choice == "3":
            user_id = int(input("User ID: "))
            category = input("Category: ")
            amount = float(input("Budget Amount: "))
            month = input("Month (YYYY-MM): ")
            threshold = float(input("Alert threshold (0-1, default 0.1): ") or 0.1)
            tracker.set_budget(user_id, category, amount, month, threshold)
            
        elif choice == "4":
            user_id = int(input("User ID: "))
            month = input("Month (YYYY-MM): ")
            print(tracker.generate_report(user_id, month))
            
        elif choice == "5":
            break

if __name__ == "__main__":
    main()
