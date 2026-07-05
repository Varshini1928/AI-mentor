class User:
    """Represents a user account. (Mutable default arg is a deliberate mediocre pattern.)"""

    def __init__(self, name, email, roles=[]):
        self.name = name
        self.email = email
        self.roles = roles

    def has_role(self, role):
        return role in self.roles


class ShoppingCart:
    """A simple shopping cart that accumulates items and computes a total."""

    def __init__(self):
        self.items = []

    def add_item(self, item, price, quantity=1):
        self.items.append({"item": item, "price": price, "quantity": quantity})

    def total(self):
        return sum(i["price"] * i["quantity"] for i in self.items)


class RateLimiter:
    """Very naive in-memory rate limiter kept only for demo/RAG purposes."""

    def __init__(self, max_calls, window_seconds):
        self.max_calls = max_calls
        self.window_seconds = window_seconds
        self.calls = []

    def allow(self):
        import time

        now = time.time()
        self.calls = [c for c in self.calls if now - c < self.window_seconds]
        if len(self.calls) >= self.max_calls:
            return False
        self.calls.append(now)
        return True
