import re
from typing import Optional

# Standard categories in the app (keyword lists — first match wins in order below)
CATEGORIES = {
    "income": ["salary", "neft cr-salary", "freelance", "imps cr"],
    "housing": ["rent", "prop mgmt"],
    "emi": ["home loan emi", "ach dr-hdfc home", "loan emi", "emi", "bajaj finance", "muthoot"],
    "investments": ["mf sip", "sbi mf", "mutual fund"],
    "bills": ["billpay", "credit card hdfc"],
    "insurance": ["lic premium", "insurance lic"],
    "tax": ["income tax"],
    "food": [
        "swiggy", "zomato", "mcdonalds", "dominos", "burger", "pizza",
        "restaurant", "cafe coffee", "cafe", "baker", "dinner", "outing",
    ],
    "transport": [
        "uber", "ola", "rapido", "irctc", "makemytrip", "petrol pump",
        "petrol", "fuel", "hpcl", "bpcl",
    ],
    "shopping": ["amazon pay", "flipkart", "myntra", "ajio", "sale", "gifts"],
    "groceries": [
        "blinkit", "zepto", "instamart", "bigbasket", "dmart", "reliance fresh",
    ],
    "utilities": [
        "bescom", "electricity", "airtel", "jio prepaid", "jio", "vi",
        "recharge", "water", "bbmp",
    ],
    "entertainment": ["netflix", "amazon prime", "hotstar", "spotify", "bookmyshow", "pvr"],
    "health": ["pharmacy", "apollo", "medplus", "hospital", "clinic", "practo"],
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

    # 2. Rule-based keyword matching (longer phrases first per category)
    for cat, keywords in CATEGORIES.items():
        for kw in sorted(keywords, key=len, reverse=True):
            if kw in text_to_search:
                label = cat.title()
                if label == "Emi":
                    return "EMI"
                return label

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
