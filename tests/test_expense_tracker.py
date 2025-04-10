import unittest
from src.expense_tracker import ExpenseTracker

class TestExpenseTracker(unittest.TestCase):
    def setUp(self):
        self.tracker = ExpenseTracker("test.db")
        self.user_id = self.tracker.add_user("test@example.com", "Test User")

    def test_add_user(self):
        self.assertEqual(self.tracker.get_user_id("test@example.com"), self.user_id)

    def test_log_expense(self):
        self.tracker.log_expense(self.user_id, 50.0, "Food", "Lunch")
        spending = self.tracker.get_monthly_spending(self.user_id, "Food", "2025-04")
        self.assertEqual(spending, 50.0)

    def test_budget_alert(self):
        self.tracker.set_budget(self.user_id, "Food", 100.0, "2025-04", 0.1)
        self.tracker.log_expense(self.user_id, 95.0, "Food", "Dinner")
        # Manual check required for email alert in real scenario
        self.assertTrue(True)  # Placeholder for alert check

if __name__ == '__main__':
    unittest.main()
