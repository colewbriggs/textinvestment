"""Investment analysis module."""

from app.analysis.defaults import BUFFETT_DEFAULTS, INDUSTRIES
from app.analysis.dip_detector import find_opportunities
from app.analysis.stock_scorer import calculate_score, Opportunity

__all__ = [
    "BUFFETT_DEFAULTS",
    "INDUSTRIES",
    "find_opportunities",
    "calculate_score",
    "Opportunity",
]
