import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from langchain.agents import initialize_agent, AgentType, Tool
from langchain.chat_models import init_chat_model
import json

API_KEY = "AIzaSyDDH5CHSZx9FcAYF3cXn_Pu86kZtuErjjs"
# Load environment variables
GCP_PROJECT = os.getenv("GCP_PROJECT")
GCP_LOCATION = os.getenv("GCP_LOCATION", "us-central1")

# Initialize Flask app and enable CORS for React frontend communication
app = Flask(__name__)
CORS(app)

llm = init_chat_model(
    "gemini-2.0-flash",
    model_provider="google_genai",
    api_key=API_KEY,
)


def list_bunq_accounts() -> str:
    """List all Bunq account IDs and types."""
    # TODO: Fetch via Bunq SDK/API
    return "Accounts:- 12345 (Checking)- 67890 (Savings)"


def get_bunq_balance(account_id: str) -> str:
    """Return the balance for a given Bunq account ID."""
    # TODO: Integrate with real Bunq SDK or API
    return f"Balance for account {account_id}: €1,234.56"


def get_transaction_history(account_id: str, limit: int = 10) -> str:
    """Fetch recent transactions for an account (default 10)."""
    # TODO: Replace with API call
    txs = [
        {"id": "tx1", "amount": "-€20.00", "description": "Coffee Shop"},
        {"id": "tx2", "amount": "+€500.00", "description": "Salary"},
        # ...
    ]
    lines = [f"{t['id']}: {t['amount']} ({t['description']})" for t in txs[:limit]]
    return "".join(lines)


def create_payment(
    from_account: str, to_account: str, amount: float, currency: str = "EUR"
) -> str:
    """Create a payment between two accounts."""
    # TODO: Call Bunq payment endpoint
    return f"Payment of {amount} {currency} from {from_account} to {to_account} initiated successfully (ID: pay_ABC123)."


def get_exchange_rate(base_currency: str, target_currency: str) -> str:
    """Get current exchange rate between two currencies."""
    # TODO: Use an external FX API or Bunq API
    rate = 0.85  # example rate
    return f"1 {base_currency} = {rate} {target_currency}"


# Wrap as LangChain Tools
tools = [
    Tool(
        name="list_accounts",
        func=list_bunq_accounts,
        description="List all Bunq account IDs and their account types. (No parameters)",
    ),
    Tool(
        name="get_balance",
        func=get_bunq_balance,
        description="Get the balance of a Bunq account. Parameters: account_id (str)",
    ),
    Tool(
        name="get_transactions",
        func=get_transaction_history,
        description="Retrieve recent transactions. Parameters: account_id (str), limit (int, optional)",
    ),
    Tool(
        name="create_payment",
        func=create_payment,
        description="Create a payment. Parameters: from_account (str), to_account (str), amount (float), currency (str, optional)",
    ),
    Tool(
        name="get_fx_rate",
        func=get_exchange_rate,
        description="Fetch the exchange rate. Parameters: base_currency (str), target_currency (str)",
    ),
]

# Initialize LangChain agent with function-calling capability
tgent = initialize_agent(
    tools=tools,
    llm=llm,
    agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True,
)


@app.route("/chat", methods=["POST"])
def chat():
    payload = request.get_json(force=True)
    user_message = payload.get("message", "")

    # Process the message (including function calls)
    response = tgent.run(user_message)
    return jsonify({"response": response})


if __name__ == "__main__":
    # Run on port 5000 for local development
    app.run(host="0.0.0.0", port=5005, debug=True)
