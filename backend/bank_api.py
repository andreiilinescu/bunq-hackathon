import uuid
import time
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
import random
import requests

# ------------------------------------------------------------------------------
# In-memory data structures
# ------------------------------------------------------------------------------


@dataclass
class User:
    id: str
    name: str
    email: str
    phone: str = None
    accounts_ids: List[str] = field(default_factory=list)
    transactions: List[str] = field(default_factory=list)
    friends_alias: List[str] = field(default_factory=list)


@dataclass
class Account:
    id: str
    description: str
    currency: str
    balance: float
    user_id: str
    transactions: List[str] = field(default_factory=list)


@dataclass
class Payment:
    id: str
    amount: float
    currency: str
    description: str
    from_account_id: str
    to_account_id: str
    timestamp: float


@dataclass
class PaymentRequest:
    id: str
    amount: float
    currency: str
    description: str
    account_id: str
    url: str
    is_paid: bool = False
    timestamp: float = field(default_factory=time.time)


# In-memory database
users: Dict[str, User] = {}
accounts: Dict[str, Account] = {}
payments: List[Payment] = []
payment_requests: Dict[str, PaymentRequest] = {}


# ------------------------------------------------------------------------------
# Helper functions
# ------------------------------------------------------------------------------
def get_user_by_email(email: str) -> Optional[User]:
    for user in users.values():
        if user.email == email:
            return user
    return None


def get_account_by_email(email: str) -> Optional[Account]:
    user = get_user_by_email(email)
    if user:
        main_acc = user.accounts_ids[0] if user.accounts_ids else None
        return get_account_by_id(main_acc)
    return None


def get_account_by_id(account_id: str) -> Optional[Account]:
    return accounts.get(account_id)


def get_user_by_id(user_id: str) -> Optional[User]:
    return users.get(user_id)


def initialize_demo_data():
    """Create some demo users and accounts"""
    # Create users
    user1_id = str(uuid.uuid4())
    user2_id = str(uuid.uuid4())

    users[user1_id] = User(
        id=user1_id,
        name="Andrei Smith",
        email="andrei@example.com",
        accounts_ids=[],
        friends_alias=["bob@example.com"],
    )

    users[user2_id] = User(
        id=user2_id, name="Bob Jones", email="bob@example.com", accounts_ids=[]
    )

    # Create accounts
    account1_id = str(uuid.uuid4())
    account2_id = str(uuid.uuid4())
    account3_id = str(uuid.uuid4())

    accounts[account1_id] = Account(
        id=account1_id,
        description="Andrei's Main Account",
        currency="EUR",
        balance=1000.0,
        user_id=user1_id,
    )

    accounts[account2_id] = Account(
        id=account2_id,
        description="Andrei's USD Account",
        currency="USD",
        balance=500.0,
        user_id=user1_id,
    )

    accounts[account3_id] = Account(
        id=account3_id,
        description="Bob's Main Account",
        currency="EUR",
        balance=750.0,
        user_id=user2_id,
    )

    # Link accounts to users
    users[user1_id].accounts_ids.extend([account1_id, account2_id])
    users[user2_id].accounts_ids.append(account3_id)

    return user1_id, user2_id


# ------------------------------------------------------------------------------
# API functions (matching bunq_api functionality)
# ------------------------------------------------------------------------------


def make_payment(
    amount: float,
    currency: str,
    to_alias: str,
    from_account: str,
    description: str = None,
) -> str:
    """
    Make a payment to another account.
    Args: amount, currency, to_alias (email/phone), from_account, description
    """
    try:
        # Get source account
        source_account = get_account_by_id(from_account)
        if not source_account:
            raise ValueError(f"Source account {from_account} not found")

        # Check currency match
        if source_account.currency != currency:
            raise ValueError(
                f"Currency mismatch: account is in {source_account.currency}, payment in {currency}"
            )

        # Check sufficient funds
        if source_account.balance < amount:
            raise ValueError(
                f"Insufficient funds: have {source_account.balance}, need {amount}"
            )

        # Find target account by alias (email in this simplified version)
        target_account = None
        for account_id, account in accounts.items():
            user = users.get(account.user_id)
            if user and user.email == to_alias and account.currency == currency:
                target_account = account
                break

        if not target_account:
            raise ValueError(
                f"Target account for {to_alias} with currency {currency} not found"
            )

        # Execute payment
        source_account.balance -= amount
        target_account.balance += amount

        # Record payment
        payment_id = str(uuid.uuid4())
        payment = Payment(
            id=payment_id,
            amount=amount,
            currency=currency,
            description=description or "",
            from_account_id=from_account,
            to_account_id=target_account.id,
            timestamp=time.time(),
        )
        payments.append(payment)
        users[source_account.user_id].transactions.append(payment_id)
        users[target_account.user_id].transactions.append(payment_id)

        source_account.transactions.append(payment_id)
        target_account.transactions.append(payment_id)
        return (
            f"✅ Payment {payment_id} executed!\n"
            f"• Amount : {amount} {currency}\n"
            f"• From   : {from_account}\n"
            f"• To     : {to_alias} (email)\n"
            f"• Desc.  : {description or '—'}"
        )

    except Exception as e:
        err_msg = str(e)
        return f"❌ Payment failed: {err_msg}"


def bankme_link(
    amount: float,
    currency: str = "EUR",
    monetary_account_id: str = None,
    description: str = None,
) -> str:
    """
    Create a public payment request link.
    Args: amount, currency, monetary_account_id, description
    Returns the tab URL and summary.
    """
    try:
        # Verify account exists
        if monetary_account_id and monetary_account_id not in accounts:
            raise ValueError(f"Account {monetary_account_id} not found")

        # Generate a payment request
        request_id = str(uuid.uuid4())
        url = f"https://fakebunq.me/{request_id}"

        payment_request = PaymentRequest(
            id=request_id,
            amount=amount,
            currency=currency,
            description=description or "",
            account_id=monetary_account_id,
            url=url,
        )

        payment_requests[request_id] = payment_request

        return (
            f"✅ Payment request created!\n"
            f"• Amount : {amount} {currency}\n"
            f"• Desc.  : {description or '—'}\n"
            f"• URL    : {url}"
        )

    except Exception as e:
        err_msg = str(e)
        return f"❌ Payment request failed: {err_msg}"


def get_accounts(user_id: str = None) -> List[Dict[str, Any]]:
    """Get all accounts for a user or all accounts if user_id is None"""
    result = []

    for account_id, account in accounts.items():
        if user_id is None or account.user_id == user_id:
            result.append(
                {
                    "id": account_id,
                    "description": account.description,
                    "balance": account.balance,
                    "currency": account.currency,
                }
            )

    return result


# @function_tool(
#     description_override="Get an indicative FX spot rate. Args: base_currency (str), "
#     "target_currency (str). Returns ‘1 <base> = <rate> <target>’. "
#     "Use for quick reference only."
# )
def get_exchange_rate(base_currency: str, target_currency: str) -> float:
    """
    Get the current exchange rate between two currencies using a free exchange rate API.
    Args: base_currency (str), target_currency (str)
    Returns: Formatted string with the exchange rate
    """
    try:
        # Use a free exchange rate API
        url = f"https://api.exchangerate-api.com/v4/latest/{base_currency}"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        if target_currency in data["rates"]:
            rate = data["rates"][target_currency]
            return rate
        else:
            return -1

    except Exception as e:
        return -2


# Initialize with demo data
current_user_id, _ = initialize_demo_data()


def transfer_between_accounts(
    from_account_id: str, to_account_id: str, amount: float, description: str = None
) -> str:
    """
    Transfer money between two accounts owned by the same user.
    Handles currency conversion if the accounts have different currencies.

    Args:
        from_account_id: Source account ID
        to_account_id: Target account ID
        amount: Amount to transfer
        description: Optional transfer description

    Returns:
        Success or error message
    """
    try:
        # Get source and target accounts
        source_account = get_account_by_id(from_account_id)
        target_account = get_account_by_id(to_account_id)

        # Validate accounts exist
        if not source_account:
            raise ValueError(f"Source account {from_account_id} not found")
        if not target_account:
            raise ValueError(f"Target account {to_account_id} not found")

        # Validate both accounts belong to the same user
        if source_account.user_id != target_account.user_id:
            raise ValueError(
                "Cannot transfer between accounts belonging to different users"
            )

        # Check sufficient funds
        if source_account.balance < amount:
            raise ValueError(
                f"Insufficient funds: have {source_account.balance}, need {amount}"
            )

        # Handle currency conversion if needed
        target_amount = amount
        if source_account.currency != target_account.currency:
            # Get exchange rate
            try:
                rate_str = get_exchange_rate(
                    source_account.currency, target_account.currency
                )
                rate = float(rate_str.split("=")[1].split()[0].strip())
                target_amount = amount * rate
            except Exception as e:
                raise ValueError(f"Failed to convert currency: {str(e)}")

        # Execute transfer
        source_account.balance -= amount
        target_account.balance += target_amount

        # Record transfer as payment
        payment_id = str(uuid.uuid4())
        payment = Payment(
            id=payment_id,
            amount=amount,
            currency=source_account.currency,
            description=description or f"Transfer to {target_account.description}",
            from_account_id=from_account_id,
            to_account_id=to_account_id,
            timestamp=time.time(),
        )
        payments.append(payment)

        # Create success message
        if source_account.currency != target_account.currency:
            return (
                f"✅ Transfer {payment_id} executed with currency conversion!\n"
                f"• Amount: {amount} {source_account.currency} → {target_amount:.2f} {target_account.currency}\n"
                f"• From: {source_account.description}\n"
                f"• To: {target_account.description}\n"
                f"• Desc: {description or 'Internal transfer'}"
            )
        else:
            return (
                f"✅ Transfer {payment_id} executed!\n"
                f"• Amount: {amount} {source_account.currency}\n"
                f"• From: {source_account.description}\n"
                f"• To: {target_account.description}\n"
                f"• Desc: {description or 'Internal transfer'}"
            )

    except Exception as e:
        err_msg = str(e)
        return f"❌ Transfer failed: {err_msg}"


# Example usage:
if __name__ == "__main__":
    print("Fake Bank API initialized")
    print(f"Users: {len(users)}")
    print(f"Accounts: {len(accounts)}")
    print(get_account_by_id(get_user_by_id(current_user_id).accounts_ids[0]))
    # Example to make a payment
    result = make_payment(
        50.0,
        "EUR",
        "bob@example.com",
        get_user_by_id(current_user_id).accounts_ids[0],
        "Test payment",
    )
    print(result)
    print(get_account_by_id(get_user_by_id(current_user_id).accounts_ids[0]))
    transfer_between_accounts(
        get_user_by_id(current_user_id).accounts_ids[0],
        get_user_by_id(current_user_id).accounts_ids[1],
        100.0,
        "Test transfer",
    )
    print(get_account_by_id(get_user_by_id(current_user_id).accounts_ids[0]))
    print(get_account_by_id(get_user_by_id(current_user_id).accounts_ids[1]))
