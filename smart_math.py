"""
High-Precision Math & Science Solver for AR AI 1.5.
Provides step-by-step algebra, trigonometry, and arithmetic calculations in pure server style.
"""

import re
import math
from typing import Optional

TRIG_SPECIAL = {
    ("sin", 0): "0",
    ("sin", 30): "0.5 or 1/2",
    ("sin", 45): "sqrt(2)/2 or 0.707",
    ("sin", 60): "sqrt(3)/2 or 0.866",
    ("sin", 90): "1",
    ("sin", 180): "0",
    ("sin", 270): "-1",
    ("sin", 360): "0",

    ("cos", 0): "1",
    ("cos", 30): "sqrt(3)/2 or 0.866",
    ("cos", 45): "sqrt(2)/2 or 0.707",
    ("cos", 60): "0.5 or 1/2",
    ("cos", 90): "0",
    ("cos", 180): "-1",
    ("cos", 270): "0",
    ("cos", 360): "1",

    ("tan", 0): "0",
    ("tan", 30): "sqrt(3)/3 or 0.577",
    ("tan", 45): "1",
    ("tan", 60): "sqrt(3) or 1.732",
    ("tan", 90): "undefined (vertical asymptote)",
    ("tan", 180): "0",
    ("tan", 360): "0",
}

def solve_math_query(query: str) -> Optional[str]:
    """Detect and accurately solve algebra, trigonometry, and arithmetic questions."""
    q = query.lower().strip().rstrip("?").replace(",", "")

    # 1. Trigonometry: sin, sine, cos, cosine, tan, tangent
    # e.g. "what is sine 30", "sin(30)", "cosine of 60", "tan 45"
    m_trig = re.search(r'\b(sin|sine|cos|cosine|tan|tangent)\s*(?:of|\()?\s*([0-9]+(?:\.[0-9]+)?)\s*\)?(?:\s*degrees)?', q)
    if m_trig:
        fn_raw = m_trig.group(1)
        angle_val = float(m_trig.group(2))
        
        if fn_raw in ("sin", "sine"):
            fn = "sin"
        elif fn_raw in ("cos", "cosine"):
            fn = "cos"
        else:
            fn = "tan"

        # Check special exact values in degrees
        angle_int = int(angle_val) if angle_val.is_integer() else None
        if angle_int is not None and (fn, angle_int % 360) in TRIG_SPECIAL:
            return TRIG_SPECIAL[(fn, angle_int % 360)]

        # Float calculation
        rad = math.radians(angle_val)
        if fn == "sin":
            val = math.sin(rad)
        elif fn == "cos":
            val = math.cos(rad)
        else:
            val = math.tan(rad)
        
        if math.isclose(val, 0, abs_tol=1e-9): return "0"
        if math.isclose(val, 1, abs_tol=1e-9): return "1"
        if math.isclose(val, -1, abs_tol=1e-9): return "-1"
        if math.isclose(val, 0.5, abs_tol=1e-9): return "0.5 or 1/2"
        if math.isclose(val, -0.5, abs_tol=1e-9): return "-0.5 or -1/2"
        return f"{val:.3f}"

    # 2. Linear algebra: solve ax + b = c or ax - b = c
    m_lin = re.search(r'(?:solve|whats|what is)?\s*([0-9]+)\s*x\s*([+-])\s*([0-9]+)\s*=\s*([0-9]+)', q)
    if m_lin:
        a = int(m_lin.group(1))
        op = m_lin.group(2)
        b = int(m_lin.group(3))
        c = int(m_lin.group(4))
        if op == '+':
            rhs = c - b
            ans = rhs / a
            ans_str = str(int(ans)) if ans.is_integer() else f"{ans:.2f}"
            return f"x = {ans_str}"
        else:
            rhs = c + b
            ans = rhs / a
            ans_str = str(int(ans)) if ans.is_integer() else f"{ans:.2f}"
            return f"x = {ans_str}"

    # Linear algebra: solve ax = b
    m_simple_lin = re.search(r'(?:solve|whats|what is)?\s*([0-9]+)\s*x\s*=\s*([0-9]+)', q)
    if m_simple_lin:
        a = int(m_simple_lin.group(1))
        b = int(m_simple_lin.group(2))
        ans = b / a
        ans_str = str(int(ans)) if ans.is_integer() else f"{ans:.2f}"
        return f"x = {ans_str}"

    # 3. Square roots: what is the square root of X
    m_sqrt = re.search(r'(?:what is the\s*)?square root of\s*([0-9]+(?:\.[0-9]+)?)', q)
    if m_sqrt:
        val = float(m_sqrt.group(1))
        res = math.isqrt(int(val)) if val.is_integer() and int(val) >= 0 and math.isqrt(int(val))**2 == int(val) else math.sqrt(val)
        return str(int(res)) if isinstance(res, int) or res.is_integer() else f"{res:.2f}"

    # 4. Basic arithmetic: X + Y, X - Y, X * Y, X / Y, X times Y, X plus Y, X minus Y, X divided by Y
    m_arith = re.search(r'(?:what is\s*)?([0-9]+)\s*(times|\*|x|divided by|\/|plus|\+|minus|\-)\s*([0-9]+)', q)
    if m_arith:
        n1 = int(m_arith.group(1))
        op_word = m_arith.group(2)
        n2 = int(m_arith.group(3))
        if op_word in ['times', '*', 'x']:
            return str(n1 * n2)
        elif op_word in ['plus', '+']:
            return str(n1 + n2)
        elif op_word in ['minus', '-']:
            return str(n1 - n2)
        elif op_word in ['divided by', '/'] and n2 != 0:
            res = n1 / n2
            return str(int(res)) if res.is_integer() else f"{res:.2f}"

    # 5. Percentages: X percent of Y
    m_pct = re.search(r'(?:what is\s*)?([0-9]+(?:\.[0-9]+)?)\s*percent of\s*([0-9]+(?:\.[0-9]+)?)', q)
    if m_pct:
        pct = float(m_pct.group(1))
        base = float(m_pct.group(2))
        res = (pct / 100.0) * base
        return str(int(res)) if res.is_integer() else f"{res:.2f}"

    # 6. Powers: X to the power of Y
    m_pow = re.search(r'(?:what is\s*)?([0-9]+)\s*(?:to the power of|\^)\s*([0-9]+)', q)
    if m_pow:
        base = int(m_pow.group(1))
        exp = int(m_pow.group(2))
        return str(base ** exp)

    return None

if __name__ == "__main__":
    print("Testing Smart Math with Trigonometry:")
    for q in [
        "what is sine 30",
        "sin(30)",
        "what is sin 30",
        "sine 30",
        "what is cosine 60",
        "what is tan 45",
        "solve 3x + 5 = 20",
        "what is the square root of 144",
        "what is 25 times 25"
    ]:
        print(f"[{q}] -> {solve_math_query(q)}")
