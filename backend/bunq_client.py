import os
from typing import Dict, Optional
from datetime import datetime
from bunq.sdk.context import ApiContext, ApiEnvironmentType
from bunq.sdk.model.generated import endpoint
from bunq.sdk.model.generated.object_ import Pointer, Amount, SchedulePaymentEntry
from dotenv import load_dotenv

class BunqClient:
    def __init__(self, api_key: Optional[str] = None, device_description: str = "Bunq Payment Agent"):
        """
        Initialize the Bunq client for payments.
        
        Args:
            api_key (str, optional): Your Bunq API key. If not provided, will try to load from BUNQ_API_KEY env var.
            device_description (str): Description of this device/application
        """
        load_dotenv()
        self.api_key = api_key or os.getenv("BUNQ_API_KEY")
        if not self.api_key:
            raise ValueError("Bunq API key is required. Set it via constructor or BUNQ_API_KEY environment variable")
        
        self.device_description = device_description
        self.context_file = "bunq_context.json"
        self.api_context = self._setup_context()

    def _setup_context(self) -> ApiContext:
        """Set up the Bunq API context."""
        try:
            if os.path.exists(self.context_file):
                return ApiContext.restore(self.context_file)
            else:
                context = ApiContext.create(
                    ApiEnvironmentType.PRODUCTION,
                    self.api_key,
                    self.device_description
                )
                context.save(self.context_file)
                return context
        except Exception as e:
            raise Exception(f"Failed to setup Bunq context: {str(e)}")

    def send_payment(
        self,
        from_account_id: int,
        to_iban: str,
        amount: float,
        description: str,
        currency: str = "EUR"
    ) -> Dict:
        """
        Send an immediate payment to an IBAN.
        
        Args:
            from_account_id (int): Your Bunq account ID to send from
            to_iban (str): Recipient's IBAN
            amount (float): Amount to send
            description (str): Payment description
            currency (str): Currency code (default: EUR)
            
        Returns:
            Dict: Payment details including status
        """
        try:
            pointer = Pointer("IBAN", to_iban)
            amount_obj = Amount(f"{amount:.2f}", currency)
            
            payment = endpoint.Payment.create(
                amount_obj,
                pointer,
                description,
                from_account_id
            ).value
            
            return {
                "id": payment.id_,
                "status": payment.status,
                "amount": payment.amount.value,
                "currency": payment.amount.currency,
                "description": payment.description,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            raise Exception(f"Failed to send payment: {str(e)}")

    def schedule_payment(
        self,
        from_account_id: int,
        to_iban: str,
        amount: float,
        description: str,
        schedule_date: datetime,
        currency: str = "EUR"
    ) -> Dict:
        """
        Schedule a payment for a future date.
        
        Args:
            from_account_id (int): Your Bunq account ID to send from
            to_iban (str): Recipient's IBAN
            amount (float): Amount to send
            description (str): Payment description
            schedule_date (datetime): When to execute the payment
            currency (str): Currency code (default: EUR)
            
        Returns:
            Dict: Scheduled payment details
        """
        try:
            pointer = Pointer("IBAN", to_iban)
            amount_obj = Amount(f"{amount:.2f}", currency)
            
            # Create schedule entry
            schedule_entry = SchedulePaymentEntry(
                amount=amount_obj,
                counterparty_alias=pointer,
                description=description
            )
            
            # Create scheduled payment
            scheduled_payment = endpoint.SchedulePayment.create(
                schedule_entry,
                schedule_date,
                from_account_id
            ).value
            
            return {
                "id": scheduled_payment.id_,
                "status": scheduled_payment.status,
                "amount": scheduled_payment.payment.amount.value,
                "currency": scheduled_payment.payment.amount.currency,
                "description": scheduled_payment.payment.description,
                "scheduled_for": schedule_date.isoformat()
            }
        except Exception as e:
            raise Exception(f"Failed to schedule payment: {str(e)}")

    def list_scheduled_payments(self, account_id: int) -> Dict:
        """
        List all scheduled payments for an account.
        
        Args:
            account_id (int): Your Bunq account ID
            
        Returns:
            Dict: List of scheduled payments
        """
        try:
            scheduled_payments = endpoint.SchedulePayment.list(account_id).value
            return {
                "scheduled_payments": [
                    {
                        "id": payment.id_,
                        "amount": payment.payment.amount.value,
                        "currency": payment.payment.amount.currency,
                        "description": payment.payment.description,
                        "scheduled_for": payment.time_schedule.scheduled_time,
                        "status": payment.status
                    }
                    for payment in scheduled_payments
                ]
            }
        except Exception as e:
            raise Exception(f"Failed to list scheduled payments: {str(e)}")

    def cancel_scheduled_payment(self, account_id: int, schedule_id: int) -> Dict:
        """
        Cancel a scheduled payment.
        
        Args:
            account_id (int): Your Bunq account ID
            schedule_id (int): ID of the scheduled payment to cancel
            
        Returns:
            Dict: Cancellation status
        """
        try:
            result = endpoint.SchedulePayment.delete(account_id, schedule_id)
            return {
                "status": "cancelled",
                "schedule_id": schedule_id,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            raise Exception(f"Failed to cancel scheduled payment: {str(e)}") 