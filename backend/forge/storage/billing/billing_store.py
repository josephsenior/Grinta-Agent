"""Billing storage for managing user balance and subscriptions."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional
from decimal import Decimal
from datetime import datetime

from forge.core.logger import forge_logger as logger
from forge.utils.async_utils import call_sync_from_async


# Global billing store instance
_billing_store_instance: Optional["FileBillingStore"] = None


def get_billing_store() -> "FileBillingStore":
    """Get or create global billing store instance."""
    global _billing_store_instance
    if _billing_store_instance is None:
        storage_path = os.getenv("BILLING_STORAGE_PATH")
        _billing_store_instance = FileBillingStore(storage_path=storage_path)
    return _billing_store_instance


class FileBillingStore:
    """File-based billing storage for user balance and subscriptions."""

    def __init__(self, storage_path: str | None = None):
        """Initialize file-based billing store.

        Args:
            storage_path: Path to billing storage directory (default: .forge/billing)
        """
        if storage_path is None:
            storage_path = os.path.join(os.getcwd(), ".forge", "billing")
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self._balance_cache: dict[str, Decimal] = {}
        self._subscription_cache: dict[str, dict] = {}
        self._load_data()

    def _load_data(self) -> None:
        """Load all billing data from storage into cache."""
        balance_file = self.storage_path / "balances.json"
        subscription_file = self.storage_path / "subscriptions.json"

        # Load balances
        if balance_file.exists():
            try:
                with open(balance_file, "r") as f:
                    data = json.load(f)
                    for user_id, balance_str in data.get("balances", {}).items():
                        self._balance_cache[user_id] = Decimal(str(balance_str))
                logger.info(f"Loaded {len(self._balance_cache)} user balances")
            except Exception as e:
                logger.error(f"Error loading balances: {e}")

        # Load subscriptions
        if subscription_file.exists():
            try:
                with open(subscription_file, "r") as f:
                    data = json.load(f)
                    self._subscription_cache = data.get("subscriptions", {})
                logger.info(f"Loaded {len(self._subscription_cache)} subscriptions")
            except Exception as e:
                logger.error(f"Error loading subscriptions: {e}")

    def _save_balances(self) -> None:
        """Save balances to disk."""
        balance_file = self.storage_path / "balances.json"
        try:
            data = {
                "balances": {
                    user_id: str(balance) for user_id, balance in self._balance_cache.items()
                }
            }
            with open(balance_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving balances: {e}")

    def _save_subscriptions(self) -> None:
        """Save subscriptions to disk."""
        subscription_file = self.storage_path / "subscriptions.json"
        try:
            data = {"subscriptions": self._subscription_cache}
            with open(subscription_file, "w") as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error saving subscriptions: {e}")

    async def get_balance(self, user_id: str) -> Decimal:
        """Get user balance.

        Args:
            user_id: User ID

        Returns:
            User balance (defaults to 0.00)
        """
        return self._balance_cache.get(user_id, Decimal("0.00"))

    async def add_balance(self, user_id: str, amount: Decimal) -> Decimal:
        """Add balance to user account.

        Args:
            user_id: User ID
            amount: Amount to add

        Returns:
            New balance
        """
        current_balance = await self.get_balance(user_id)
        new_balance = current_balance + amount
        self._balance_cache[user_id] = new_balance
        await call_sync_from_async(self._save_balances)
        logger.info(f"Added ${amount} to user {user_id}. New balance: ${new_balance}")
        return new_balance

    async def deduct_balance(self, user_id: str, amount: Decimal) -> bool:
        """Deduct balance from user account.

        Args:
            user_id: User ID
            amount: Amount to deduct

        Returns:
            True if deduction was successful, False if insufficient balance
        """
        current_balance = await self.get_balance(user_id)
        if current_balance < amount:
            return False

        new_balance = current_balance - amount
        self._balance_cache[user_id] = new_balance
        await call_sync_from_async(self._save_balances)
        logger.info(f"Deducted ${amount} from user {user_id}. New balance: ${new_balance}")
        return True

    async def get_subscription(self, user_id: str) -> Optional[dict]:
        """Get user subscription.

        Args:
            user_id: User ID

        Returns:
            Subscription data or None
        """
        return self._subscription_cache.get(user_id)

    async def set_subscription(
        self,
        user_id: str,
        status: str,
        start_at: str,
        end_at: str,
    ) -> dict:
        """Set user subscription.

        Args:
            user_id: User ID
            status: Subscription status (ACTIVE, DISABLED, etc.)
            start_at: Subscription start date (ISO format)
            end_at: Subscription end date (ISO format)

        Returns:
            Subscription data
        """
        subscription = {
            "status": status,
            "start_at": start_at,
            "end_at": end_at,
            "created_at": datetime.utcnow().isoformat(),
        }
        self._subscription_cache[user_id] = subscription
        await call_sync_from_async(self._save_subscriptions)
        logger.info(f"Set subscription for user {user_id}: {status}")
        return subscription

