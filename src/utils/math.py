import math
from typing import Optional

def normal_cdf(x: float) -> float:
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))

def normal_pdf(x: float) -> float:
    return math.exp(-0.5 * x * x) / math.sqrt(2 * math.pi)

def black_scholes_greeks(
    S: float, K: float, T: float, r: float, sigma: float, option_type: str = "call"
) -> dict:
    if T <= 0:
        intrinsic = max(S - K, 0) if option_type == "call" else max(K - S, 0)
        return {"price": intrinsic, "delta": 1.0 if option_type == "call" else -1.0, "gamma": 0, "theta": 0, "vega": 0, "rho": 0}
    
    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    
    if option_type == "call":
        price = S * normal_cdf(d1) - K * math.exp(-r * T) * normal_cdf(d2)
        delta = normal_cdf(d1)
        rho = K * T * math.exp(-r * T) * normal_cdf(d2) / 100
    else:
        price = K * math.exp(-r * T) * normal_cdf(-d2) - S * normal_cdf(-d1)
        delta = normal_cdf(d1) - 1
        rho = -K * T * math.exp(-r * T) * normal_cdf(-d2) / 100
    
    gamma = normal_pdf(d1) / (S * sigma * math.sqrt(T))
    theta = (-(S * normal_pdf(d1) * sigma) / (2 * math.sqrt(T)) - r * K * math.exp(-r * T) * normal_cdf(d2 if option_type == "call" else -d2)) / 365
    vega = S * normal_pdf(d1) * math.sqrt(T) / 100
    
    return {"price": round(price, 2), "delta": round(delta, 4), "gamma": round(gamma, 6), "theta": round(theta, 2), "vega": round(vega, 2), "rho": round(rho, 4)}

def implied_volatility(market_price: float, S: float, K: float, T: float, r: float, option_type: str = "call", max_iter: int = 100) -> float:
    if T <= 0:
        return 0.0
    sigma = 0.3
    for _ in range(max_iter):
        result = black_scholes_greeks(S, K, T, r, sigma, option_type)
        diff = result["price"] - market_price
        if abs(diff) < 0.001:
            return round(sigma, 4)
        vega = result["vega"] * 100
        if abs(vega) < 1e-10:
            break
        sigma -= diff / vega
        sigma = max(0.01, min(sigma, 5.0))
    return round(sigma, 4)

def calculate_sip(future_value: float, rate: float, periods: int) -> float:
    monthly_rate = rate / 12
    if monthly_rate == 0:
        return future_value / periods
    return future_value * monthly_rate / ((1 + monthly_rate) ** periods - 1)

def calculate_xirr(cashflows: list[tuple[str, float]], guess: float = 0.1) -> float:
    from datetime import datetime
    dates = [datetime.strptime(cf[0], "%Y-%m-%d") for cf in cashflows]
    amounts = [cf[1] for cf in cashflows]
    d0 = dates[0]
    days = [(d - d0).days / 365.0 for d in dates]
    
    def npv(rate):
        return sum(a / (1 + rate) ** t for a, t in zip(amounts, days))
    
    def npv_deriv(rate):
        return sum(-t * a / (1 + rate) ** (t + 1) for a, t in zip(amounts, days))
    
    rate = guess
    for _ in range(200):
        f = npv(rate)
        fp = npv_deriv(rate)
        if abs(fp) < 1e-12:
            break
        rate -= f / fp
        if abs(f) < 0.001:
            break
    return round(rate * 100, 2)
