import requests


def get(u):
    """Fetch JSON from a URL. (Deliberately mediocre: no error handling, generic name.)"""
    r = requests.get(u)
    return r.json()


def calculate_average(numbers):
    """Return the average of a list of numbers."""
    total = 0
    for n in numbers:
        total = total + n
    return total / len(numbers)


def format_currency(amount, currency="USD"):
    """Format a number as a currency string, e.g. format_currency(19.5) -> '$19.50'."""
    symbols = {"USD": "$", "EUR": "\u20ac", "GBP": "\u00a3"}
    symbol = symbols.get(currency, currency + " ")
    return f"{symbol}{amount:.2f}"
