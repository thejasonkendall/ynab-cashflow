import os
import requests
from datetime import datetime, date
import calendar

# Set variables 
YNAB_BASE_URL = "https://api.ynab.com/v1"
YNAB_API_KEY = os.environ.get("YNAB_API_KEY")
YNAB_BUDGET_ID = os.environ.get("YNAB_BUDGET_ID")
TO_PHONE_NUMBER = os.environ.get("TO_PHONE_NUMBER")  # Just the digits, no formatting
TEXTBELT_KEY = os.environ.get("TEXTBELT_KEY")  # Your TextBelt API key

# Check env variables
required_vars = {
    "YNAB_API_KEY": YNAB_API_KEY,
    "YNAB_BUDGET_ID": YNAB_BUDGET_ID,
    "TO_PHONE_NUMBER": TO_PHONE_NUMBER,
    "TEXTBELT_KEY": TEXTBELT_KEY
}

for var_name, var_value in required_vars.items():
    if var_value is None:
        raise ValueError(f"{var_name} environment variable is not set")

# Get cash flow function
def get_monthly_cashflow(budget_id):
    """Calculate cashflow for the current month."""
    # Get current month boundaries
    today = date.today()
    first_day = date(today.year, today.month, 1).strftime("%Y-%m-%d")
    last_day = date(today.year, today.month, 
                   calendar.monthrange(today.year, today.month)[1]).strftime("%Y-%m-%d")
    
    # Get all transactions for the current month
    url = f"{YNAB_BASE_URL}/budgets/{budget_id}/transactions"
    headers = {"Authorization": f"Bearer {YNAB_API_KEY}"}
    params = {"since_date": first_day}

    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    
    transactions = response.json()["data"]["transactions"]
    
    # Calculate income and expenses (excluding transfers)
    income = sum(transaction["amount"] for transaction in transactions 
        if transaction["amount"] > 0 and transaction.get("transfer_account_id") is None) / 1000.0
            
    expenses = sum(transaction["amount"] for transaction in transactions 
        if transaction["amount"] < 0 and transaction.get("transfer_account_id") is None) / 1000.0
    
    cashflow = income + expenses  # expenses are already negative
    
    return {
        "income": income,
        "expenses": abs(expenses),  
        "cashflow": cashflow
    }

# Send text message via TextBelt API
def send_text_message(message):
    """Send text message via TextBelt API."""
    
    url = 'https://textbelt.com/text'
    payload = {
        'phone': TO_PHONE_NUMBER,
        'message': message,
        'key': TEXTBELT_KEY
    }
    
    try:
        response = requests.post(url, data=payload)
        response_json = response.json()
        
        if response_json.get('success'):
            # Extract the information we want to show
            text_id = response_json.get('textId')
            quota_remaining = response_json.get('quotaRemaining')
            
            # Return a message with the quota information
            return f"Message sent successfully! Text ID: {text_id}, Quota Remaining: {quota_remaining}"
        else:
            error_message = response_json.get('error') or "Unknown error"
            raise Exception(f"Failed to send message: {error_message}")
    
    except Exception as e:
        print(f"Error sending text message: {e}")
        raise


def main():
    try:
        # Get monthly cashflow
        cashflow_data = get_monthly_cashflow(YNAB_BUDGET_ID)
  
        # Format message - Keep it short and simple for SMS
        today = datetime.now().strftime("%Y-%m-%d")
        message = f"""From thejasonkendall {today}
Monthly Cashflow: {"$" + f"{cashflow_data['cashflow']:.2f}" if cashflow_data['cashflow'] >= 0 else "-$" + f"{abs(cashflow_data['cashflow']):.2f}"}
Income: {"$" + f"{cashflow_data['income']:.2f}" if cashflow_data['income'] >= 0 else "-$" + f"{abs(cashflow_data['income']):.2f}"}
Expenses: {"$" + f"{cashflow_data['expenses']:.2f}" if cashflow_data['expenses'] >= 0 else "-$" + f"{abs(cashflow_data['expenses']):.2f}"}"""

        print(message)
        
        # Send text message
        result = send_text_message(message)
        print(result)
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()