"""Stock scoring for value investing opportunities."""

from dataclasses import dataclass
from typing import Optional

from app.models import StocksCache, UserPreferences


@dataclass
class Opportunity:
    """A potential investment opportunity."""

    stock: StocksCache
    score: float
    drop_from_high: float
    reasons: list[str]

    @property
    def ticker(self) -> str:
        return self.stock.ticker

    @property
    def price(self) -> Optional[float]:
        return self.stock.last_price


def calculate_score(stock: StocksCache, prefs: UserPreferences) -> tuple[float, list[str]]:
    """
    Calculate an opportunity score for a stock based on value metrics.

    Returns a score from 0-100 and a list of reasons explaining the score.
    Higher score = better opportunity.
    """
    score = 0.0
    reasons = []

    # Drop from 52-week high (0-30 points)
    if stock.fifty_two_week_high and stock.last_price:
        drop = (stock.fifty_two_week_high - stock.last_price) / stock.fifty_two_week_high
        if drop >= 0.30:
            score += 30
            reasons.append(f"Down {drop:.0%} from 52-week high (significant discount)")
        elif drop >= 0.20:
            score += 25
            reasons.append(f"Down {drop:.0%} from 52-week high (good discount)")
        elif drop >= prefs.min_drop_threshold:
            score += 15
            reasons.append(f"Down {drop:.0%} from 52-week high")

    # P/E Ratio (0-20 points) - lower is better for value investing
    if stock.pe_ratio is not None:
        if stock.pe_ratio < 10:
            score += 20
            reasons.append(f"Very low P/E of {stock.pe_ratio:.1f}")
        elif stock.pe_ratio < 15:
            score += 15
            reasons.append(f"Low P/E of {stock.pe_ratio:.1f}")
        elif stock.pe_ratio <= prefs.max_pe:
            score += 10
            reasons.append(f"Reasonable P/E of {stock.pe_ratio:.1f}")

    # Debt-to-Equity (0-15 points) - lower is better
    if stock.debt_to_equity is not None:
        if stock.debt_to_equity < 0.5:
            score += 15
            reasons.append(f"Very low debt (D/E: {stock.debt_to_equity:.2f})")
        elif stock.debt_to_equity < 1.0:
            score += 10
            reasons.append(f"Low debt (D/E: {stock.debt_to_equity:.2f})")
        elif stock.debt_to_equity <= prefs.max_debt_equity:
            score += 5
            reasons.append(f"Manageable debt (D/E: {stock.debt_to_equity:.2f})")

    # ROE (0-20 points) - higher is better
    if stock.roe is not None:
        if stock.roe >= 0.25:
            score += 20
            reasons.append(f"Excellent ROE of {stock.roe:.0%}")
        elif stock.roe >= 0.20:
            score += 15
            reasons.append(f"Strong ROE of {stock.roe:.0%}")
        elif stock.roe >= prefs.min_roe:
            score += 10
            reasons.append(f"Good ROE of {stock.roe:.0%}")

    # Profit Margin (0-15 points) - higher is better
    if stock.profit_margin is not None:
        if stock.profit_margin >= 0.20:
            score += 15
            reasons.append(f"High profit margin of {stock.profit_margin:.0%}")
        elif stock.profit_margin >= 0.10:
            score += 10
            reasons.append(f"Solid profit margin of {stock.profit_margin:.0%}")
        elif stock.profit_margin >= 0.05:
            score += 5
            reasons.append(f"Positive margin of {stock.profit_margin:.0%}")

    return score, reasons


def meets_criteria(stock: StocksCache, prefs: UserPreferences) -> tuple[bool, float]:
    """
    Check if a stock meets the user's investment criteria.

    Returns (passes_filter, drop_percentage).
    """
    if not stock.last_price or not stock.fifty_two_week_high:
        return False, 0.0

    drop = (stock.fifty_two_week_high - stock.last_price) / stock.fifty_two_week_high

    # Check minimum drop threshold
    if drop < prefs.min_drop_threshold:
        return False, drop

    # Check P/E ratio (if available)
    if stock.pe_ratio is not None and stock.pe_ratio > prefs.max_pe:
        return False, drop

    # Check debt-to-equity (if available)
    if stock.debt_to_equity is not None and stock.debt_to_equity > prefs.max_debt_equity:
        return False, drop

    # Check ROE (if available)
    if stock.roe is not None and stock.roe < prefs.min_roe:
        return False, drop

    return True, drop
