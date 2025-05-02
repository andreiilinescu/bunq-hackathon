import asyncio
import os

from openai import AsyncOpenAI

from agents import (
    Agent,
    OpenAIChatCompletionsModel,
    Runner,
    function_tool,
    set_tracing_disabled,
)

BASE_URL = (
    os.getenv("EXAMPLE_BASE_URL")
    or "https://generativelanguage.googleapis.com/v1beta/openai/"
)
API_KEY = os.getenv("EXAMPLE_API_KEY") or "AIzaSyDDH5CHSZx9FcAYF3cXn_Pu86kZtuErjjs"
MODEL_NAME = os.getenv("EXAMPLE_MODEL_NAME") or "gemini-2.0-flash"

if not BASE_URL or not API_KEY or not MODEL_NAME:
    raise ValueError(
        "Please set EXAMPLE_BASE_URL, EXAMPLE_API_KEY, EXAMPLE_MODEL_NAME via env var or code."
    )


client = AsyncOpenAI(base_url=BASE_URL, api_key=API_KEY)
set_tracing_disabled(disabled=True)


@function_tool
def get_weather(city: str):
    print(f"[debug] getting weather for {city}")
    return f"The weather in {city} is sunny."


@function_tool
def list_bunq_accounts() -> str:
    """
    List all Bunq account IDs and types.

    Returns:
        str: A formatted list of account IDs and their account type names.
    """
    # TODO: Fetch via Bunq SDK/API
    return "Accounts:\n- 12345 (Checking)\n- 67890 (Savings)"


@function_tool
def get_bunq_balance(account_id: str) -> str:
    """
    Return the balance for a given Bunq account ID.

    Parameters:
        account_id (str): The unique identifier of the Bunq account.

    Returns:
        str: Formatted balance information for the specified account.
    """
    # TODO: Integrate with real Bunq SDK or API
    return f"Balance for account {account_id}: €1,234.56"


@function_tool
def get_transaction_history(account_id: str, limit: int = 10) -> str:
    """
    Fetch recent transactions for a Bunq account.

    Parameters:
        account_id (str): The unique identifier of the Bunq account.
        limit (int, optional): Maximum number of transactions to retrieve. Defaults to 10.

    Returns:
        str: A formatted list of recent transactions up to the specified limit.
    """
    # TODO: Replace with API call
    txs = [
        {"id": "tx1", "amount": "-€20.00", "description": "Coffee Shop"},
        {"id": "tx2", "amount": "+€500.00", "description": "Salary"},
        # ...
    ]
    lines = [f"{t['id']}: {t['amount']} ({t['description']})" for t in txs[:limit]]
    return "\n".join(lines)


@function_tool
def create_payment(
    from_account: str, to_account: str, amount: float, currency: str = "EUR"
) -> str:
    """
    Create a payment between two Bunq accounts.

    Parameters:
        from_account (str): The account ID to debit from.
        to_account (str): The account ID to credit to.
        amount (float): The monetary amount to transfer.
        currency (str, optional): The currency code for the transfer. Defaults to 'EUR'.

    Returns:
        str: Confirmation message with transaction ID.
    """
    # TODO: Call Bunq payment endpoint
    return f"Payment of {amount} {currency} from {from_account} to {to_account} initiated successfully (ID: pay_ABC123)."


@function_tool
def get_exchange_rate(base_currency: str, target_currency: str) -> str:
    """
    Get the current exchange rate between two currencies.

    Parameters:
        base_currency (str): The source currency code (e.g., 'EUR').
        target_currency (str): The destination currency code (e.g., 'USD').

    Returns:
        str: A formatted string showing the exchange rate.
    """
    # TODO: Use an external FX API or Bunq API
    rate = 0.85  # example rate
    return f"1 {base_currency} = {rate} {target_currency}"


async def chat_loop():
    # initialize your agent once
    agent = Agent(
        name="Assistant",
        instructions="Make sure to answer the questions!",
        model=OpenAIChatCompletionsModel(model=MODEL_NAME, openai_client=client),
        tools=[
            get_weather,
            get_bunq_balance,
            list_bunq_accounts,
            get_transaction_history,
            create_payment,
            get_exchange_rate,
        ],
    )

    print("Type ‘exit’ or ‘quit’ to stop.")
    while True:
        # read user input without blocking the event loop
        user_input = await asyncio.to_thread(input, "\nYou: ")
        if user_input.strip().lower() in {"exit", "quit"}:
            print("Goodbye!")
            break

        # call the agent
        result = await Runner.run(agent, user_input)
        print(f"Agent: {result.final_output}")


if __name__ == "__main__":
    asyncio.run(chat_loop())
