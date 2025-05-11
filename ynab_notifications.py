import os
import requests
from datetime import datetime, date
import calendar
import boto3  # AWS SDK for Python

# Set variables 
YNAB_BASE_URL = "https://api.ynab.com/v1"
YNAB_API_KEY = os.environ.get("YNAB_API_KEY")
YNAB_BUDGET_ID = os.environ.get("YNAB_BUDGET_ID")
SNS_TOPIC_ARN = os.environ.get("SNS_TOPIC_ARN")
AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.environ.get("AWS_REGION")

# Check env variables
if YNAB_API_KEY is None:
    raise ValueError("YNAB_API_KEY environment variable is not set")

if YNAB_BUDGET_ID is None:
    raise ValueError("YNAB_BUDGET_ID environment variable is not set")

if SNS_TOPIC_ARN is None:
    raise ValueError("SNS_TOPIC_ARN environment variable is not set")

if AWS_ACCESS_KEY_ID is None:
    raise ValueError("AWS_ACCESS_KEY_ID environment variable is not set")

if AWS_SECRET_ACCESS_KEY is None:
    raise ValueError("AWS_SECRET_ACCESS_KEY environment variable is not set")

if AWS_REGION is None:
    raise ValueError("AWS_REGION environment variable is not set")


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

# Send text message function - updated to use AWS SNS
def send_text_message(message):
    """Send text message via AWS SNS."""
    # Create an SNS client
    sns = boto3.client(
        'sns',
        region_name=AWS_REGION,
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY
    )
    
    subject = "Test Notification"
    
    # Publish the message to the topic
    try:
        response = sns.publish(
            TopicArn=SNS_TOPIC_ARN,
            Message=message,
            Subject=subject
        )
        print(f"Message published successfully! Message ID: {response['MessageId']}")
    except Exception as e:
        print(f"Error publishing message: {e}")


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
        message_id = send_text_message(message)
        print(f"Message sent successfully! Message ID: {message_id}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()