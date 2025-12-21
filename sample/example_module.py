"""Example module for autodoc demonstration.

This module shows how autodoc integrates with the Notion builder.
"""


def greet(*, name: str) -> str:
    """Return a greeting message.

    Args:
        name: The name to greet.

    Returns:
        A greeting string.
    """
    return f"Hello, {name}!"


class Calculator:
    """
    A simple calculator class for demonstration.
    """

    def __init__(self, *, initial_value: float = 0) -> None:
        """Initialize the calculator.

        Args:
            initial_value: The starting value.
        """
        self.value = initial_value

    def add(self, *, amount: float) -> float:
        """Add an amount to the current value.

        Args:
            amount: The amount to add.

        Returns:
            The new value.
        """
        self.value += amount
        return self.value


if __name__ == "__main__":
    greet(name="World")
    calculator = Calculator(initial_value=10)
    calculator.add(amount=5)
