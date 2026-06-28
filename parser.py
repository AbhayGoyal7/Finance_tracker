import re

CATEGORY_KEYWORDS = {
    "travel":      ["ola", "uber", "metro", "auto", "rapido", "bus", "train", "flight", "cab"],
    "food":        ["swiggy", "zomato", "chai", "lunch", "dinner", "breakfast", "restaurant", "cafe", "maggi", "hotel"],
    "groceries":   ["blinkit", "zepto", "bigbasket", "dmart", "kirana", "vegetable", "fruit", "milk"],
    "clothes":     ["myntra", "ajio", "shirt", "jeans", "dress", "shoe", "amazon fashion"],
    "rent":        ["rent", "pg", "hostel", "landlord"],
    "bills":       ["electricity", "wifi", "internet", "mobile recharge", "recharge", "water bill", "gas"],
    "luxuries":    ["netflix", "prime", "hotstar", "gym", "movie", "spotify", "game", "shopping"],
    "investments": ["sip", "etf", "stocks", "mutual fund", "zerodha", "groww", "fd", "ppf"],
    "health":      ["medicine", "doctor", "pharmacy", "hospital", "clinic", "medplus"],
    "education":   ["course", "udemy", "book", "college", "fee", "coaching"],
}

INCOME_KEYWORDS = ["salary", "refund", "cashback", "received", "credited", "got", "income", "bonus", "stipend"]

FILLER_WORDS = [
    r"\bspent\b", r"\bpaid\b", r"\bon\b", r"\bfor\b", r"\bthe\b",
    r"\ba\b", r"\ban\b", r"\bsome\b", r"\bwith\b", r"\bmy\b",
    r"\btoday\b", r"\byesterday\b", r"\bjust\b", r"\bbought\b",
    r"\bpurchased\b", r"\bbooked\b",
]


def _parse_amount(token):
    t = token.lower().strip()
    t = re.sub(r"^(rs\.?|₹)", "", t, flags=re.IGNORECASE)
    t = re.sub(r"(rs\.?|₹)$", "", t, flags=re.IGNORECASE)
    m = re.fullmatch(r"([\d,]+(?:\.\d+)?)l", t)
    if m:
        return float(m.group(1).replace(",", "")) * 100000
    m = re.fullmatch(r"([\d,]+(?:\.\d+)?)k", t)
    if m:
        return float(m.group(1).replace(",", "")) * 1000
    m = re.fullmatch(r"[\d,]+(?:\.\d+)?", t)
    if m:
        return float(t.replace(",", ""))
    return None


def _find_amount(tokens):
    for i, tok in enumerate(tokens):
        stripped = re.sub(r"^(rs\.?|₹)", "", tok, flags=re.IGNORECASE)
        stripped = re.sub(r"(rs\.?|₹)$", "", stripped, flags=re.IGNORECASE)
        if stripped != tok:
            val = _parse_amount(tok)
            if val is not None:
                return val, tokens[:i] + tokens[i+1:]
    for i, tok in enumerate(tokens):
        val = _parse_amount(tok)
        if val is not None:
            return val, tokens[:i] + tokens[i+1:]
    return None, tokens


def _detect_category(text):
    lower = text.lower()
    for cat, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw in lower:
                return cat
    return "other"


def _detect_type(text):
    lower = text.lower()
    for kw in INCOME_KEYWORDS:
        if kw in lower:
            return "income"
    return "expense"


def _build_note(text):
    note = text
    note = re.sub(r"(rs\.?\s*)?[\d,]+(?:\.\d+)?[kKlL]?\s*(rs\.?|₹)?", " ", note, flags=re.IGNORECASE)
    note = re.sub(r"₹", " ", note)
    for pat in FILLER_WORDS:
        note = re.sub(pat, " ", note, flags=re.IGNORECASE)
    note = re.sub(r"\s+", " ", note).strip()
    return note if note else text.strip()


def parse(message):
    txt = message.strip()
    tokens = txt.split()
    amount, _ = _find_amount(tokens)
    if amount is None:
        amount = 0.0
    txn_type = _detect_type(txt)
    category = "income" if txn_type == "income" else _detect_category(txt)
    note = _build_note(txt)
    return {"amount": amount, "category": category, "note": note, "type": txn_type}