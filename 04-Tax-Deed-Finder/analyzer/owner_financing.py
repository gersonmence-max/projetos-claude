"""
Owner financing calculator.
Computes resale price, down payment, monthly payments, ROI.
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class OwnerFinancingResult:
    resale_price: float
    down_payment: float
    balance: float
    monthly_payment: float
    term_months: int
    total_return: float
    roi_percent: float
    months_to_recover: float


def calculate_owner_financing(
    minimum_bid: float,
    market_value: float,
    resale_ratio: float = 0.65,
    down_payment_ratio: float = 0.10,
    term_months: int = 24,
) -> Optional[OwnerFinancingResult]:
    """
    Calculates owner financing metrics given acquisition cost and market value.

    Args:
        minimum_bid: Acquisition cost (what investor pays at auction).
        market_value: Estimated fair market value.
        resale_ratio: Resale price as fraction of market value (default 65%).
        down_payment_ratio: Down payment as fraction of resale price (default 10%).
        term_months: Loan term in months (default 24).
    """
    if minimum_bid <= 0 or market_value <= 0:
        return None

    resale_price = market_value * resale_ratio
    down_payment = resale_price * down_payment_ratio
    balance = resale_price - down_payment
    monthly_payment = balance / term_months if term_months > 0 else 0
    total_return = down_payment + (monthly_payment * term_months)
    roi = ((total_return / minimum_bid) - 1) * 100 if minimum_bid > 0 else 0
    months_to_recover = minimum_bid / monthly_payment if monthly_payment > 0 else float("inf")

    return OwnerFinancingResult(
        resale_price=round(resale_price, 2),
        down_payment=round(down_payment, 2),
        balance=round(balance, 2),
        monthly_payment=round(monthly_payment, 2),
        term_months=term_months,
        total_return=round(total_return, 2),
        roi_percent=round(roi, 1),
        months_to_recover=round(months_to_recover, 1),
    )
