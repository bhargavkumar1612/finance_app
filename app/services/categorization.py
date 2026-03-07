import re
from typing import Optional

# Standard categories in the app
CATEGORIES = {
    "food": ["swiggy", "zomato", "mcdonalds", "burger", "pizza", "restaurant", "cafe", "baker"],
    "transport": ["uber", "ola", "rapido", "irctc", "makemytrip", "petrol", "fuel", "hpcl", "bpcl"],
    "shopping": ["amazon", "flipkart", "myntra", "ajio", "retail", "mart"],
    "groceries": ["blinkit", "zepto", "instamart", "bigbasket", "dmart", "reliance fresh"],
    "utilities": ["bescom", "airtel", "jio", "vi", "electricity", "water", "bbmp", "bescom", "recharge"],
    "entertainment": ["netflix", "amazon prime", "hotstar", "spotify", "bookmyshow", "pvr"],
    "emi": ["loan", "emi", "bajaj finance", "muthoot"],
    "health": ["pharmacy", "apollo", "medplus", "hospital", "clinic", "practo"]
}

def auto_categorize(merchant: str, raw_description: str) -> Optional[str]:
    """
    Attempts to rule-match a merchant or description to a standard category.
    Optimized for Indian context (Swiggy, Zomato, UPI handles).
    """
    text_to_search = f"{str(merchant).lower()} {str(raw_description).lower()}"
    
    # 1. Check for UPI handles that specifically identify business types
    if "@" in text_to_search:
        if "swiggy@" in text_to_search or "zomato@" in text_to_search:
            return "Food"
        if "blinkit@" in text_to_search or "zepto@" in text_to_search:
            return "Groceries"
        if "uber@" in text_to_search or "ola@" in text_to_search:
            return "Transport"

    # 2. Rule-based keyword matching
    for cat, keywords in CATEGORIES.items():
        for kw in keywords:
            # Word boundary matching to prevent partial matches (e.g. 'loan' inside 'upload')
            if re.search(r'\b' + re.escape(kw) + r'\b', text_to_search):
                return cat.title()
                
    return "General"

def extract_upi_id(description: str) -> Optional[str]:
    """
    Extracts the UPI ID (VPA) from an Indian bank transaction description if present.
    Common formats: UPI-Merchant Name-merchant@bank-Okk...
    """
    desc = str(description).strip()
    match = re.search(r'([a-zA-Z0-9.\-_]+@[a-zA-Z]+)', desc)
    if match:
        return match.group(1).lower()
    return None
