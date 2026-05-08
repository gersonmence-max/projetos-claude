def add(a: float, b: float) -> float:
    """
    Adds two numbers and returns their sum.

    Args:
        a (float): The first number.
        b (float): The second number.

    Returns:
        float: The sum of a and b.
    """
    return a + b

def subtract(a: float, b: float) -> float:
    """
    Subtracts the second number from the first and returns the result.

    Args:
        a (float): The number to subtract from.
        b (float): The number to subtract.

    Returns:
        float: The difference of a and b.
    """
    return a - b

def multiply(a: float, b: float) -> float:
    """
    Multiplies two numbers and returns their product.

    Args:
        a (float): The first number.
        b (float): The second number.

    Returns:
        float: The product of a and b.
    """
    return a * b

def divide(a: float, b: float) -> float:
    """
    Divides the first number by the second and returns the result.

    Args:
        a (float): The dividend.
        b (float): The divisor.

    Returns:
        float: The quotient of a divided by b.

    Raises:
        ValueError: If the divisor b is zero.
    """
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b

if __name__ == "__main__":
    print("--- Calculator Demo ---")

    # Demonstrate addition
    num1, num2 = 10, 5
    print(f"{num1} + {num2} = {add(num1, num2)}")

    # Demonstrate subtraction
    num1, num2 = 20, 7
    print(f"{num1} - {num2} = {subtract(num1, num2)}")

    # Demonstrate multiplication
    num1, num2 = 4, 6.5
    print(f"{num1} * {num2} = {multiply(num1, num2)}")

    # Demonstrate division
    num1, num2 = 100, 4
    print(f"{num1} / {num2} = {divide(num1, num2)}")

    # Demonstrate division by zero error handling
    num1, num2 = 15, 0
    try:
        print(f"{num1} / {num2} = {divide(num1, num2)}")
    except ValueError as e:
        print(f"Error when trying to divide {num1} by {num2}: {e}")

    # Another example
    num1, num2 = -8, 2
    print(f"{num1} + {num2} = {add(num1, num2)}")
    print(f"{num1} - {num2} = {subtract(num1, num2)}")
    print(f"{num1} * {num2} = {multiply(num1, num2)}")
    print(f"{num1} / {num2} = {divide(num1, num2)}")

    print("\n--- Demo Complete ---")