import os
import json #remove later
import requests
from datetime import datetime, date
import calendar
from twilio.rest import Client

# Set variables 
YNAB_BASE_URL = "https://api.ynab.com/v1"
YNAB_API_KEY = os.environ.get("YNAB_API_KEY")
YNAB_BUDGET_ID = os.environ.get("YNAB_BUDGET_ID")
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.environ.get("TWILIO_PHONE_NUMBER")
YOUR_PHONE_NUMBER = os.environ.get("YOUR_PHONE_NUMBER")


# Check env variables
if YNAB_API_KEY is None:
    raise ValueError("YNAB_API_KEY environment variable is not set")

if YNAB_BUDGET_ID is None:
    raise ValueError("YNAB_BUDGET_ID environment variable is not set")

if TWILIO_ACCOUNT_SID is None:
    raise ValueError("TWILIO_ACCOUNT_SID environment variable is not set")

if TWILIO_AUTH_TOKEN is None:
    raise ValueError("TWILIO_AUTH_TOKEN environment variable is not set")

if TWILIO_PHONE_NUMBER is None:
    raise ValueError("TWILIO_PHONE_NUMBER environment variable is not set")

if YOUR_PHONE_NUMBER is None:
    raise ValueError("YOUR_PHONE_NUMBERID environment variable is not set")

# Get cash flow function
def get_monthly_cashflow(budget_id):
    """Calculate cashflow for the current month."""
    # print(f"budget id: {budget_id}")

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
        "income": income,  # Return raw numbers, not strings
        "expenses": abs(expenses),  
        "cashflow": cashflow
    }

# Send text message function
def send_text_message(message):
    print("I would sent it!")
    """Send text message via Twilio."""
    client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    
    message = client.messages.create(
        body=message,
        from_=TWILIO_PHONE_NUMBER,
        to=YOUR_PHONE_NUMBER
    )
    
    return message.sid

def main():
    try:
        # Get monthly cashflow
        cashflow_data = get_monthly_cashflow(YNAB_BUDGET_ID)
  
        # Format message
        today = datetime.now().strftime("%Y-%m-%d")
        message = f"""
            YNAB Report For {today}
            Monthly Cashflow: {"$" + f"{cashflow_data['cashflow']:.2f}" if cashflow_data['cashflow'] >= 0 else "-$" + f"{abs(cashflow_data['cashflow']):.2f}"}
            Income: {"$" + f"{cashflow_data['income']:.2f}" if cashflow_data['income'] >= 0 else "-$" + f"{abs(cashflow_data['income']):.2f}"}
            Expenses: {"$" + f"{cashflow_data['expenses']:.2f}" if cashflow_data['expenses'] >= 0 else "-$" + f"{abs(cashflow_data['expenses']):.2f}"}
        """

        print(message)
        
        # Send text message
        send_text_message(message)
        print("Message sent successfully!")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()