from config import settings


class TokenBudgetManager:
    def __init__(self, budget: int = None):
        self._budget = budget or settings.token_budget_per_conversation
        self._used = 0

    def consume(self, tokens: int):
        self._used += tokens

    @property
    def remaining(self) -> int:
        return max(0, self._budget - self._used)

    @property
    def usage_ratio(self) -> float:
        return self._used / self._budget

    @property
    def alert(self) -> bool:
        return self.usage_ratio >= settings.token_budget_alert_threshold

    @property
    def exhausted(self) -> bool:
        return self._used >= self._budget

    def summary(self) -> dict:
        return {
            "used": self._used,
            "budget": self._budget,
            "remaining": self.remaining,
            "usage_pct": round(self.usage_ratio * 100, 1),
            "alert": self.alert,
        }
