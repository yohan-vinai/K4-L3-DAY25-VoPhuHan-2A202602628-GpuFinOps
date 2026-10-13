"""M2 — Inference Cost Levers: $/1M-token, batch x cache x cascade (deck §7).

Run: python missions/m2_inference_levers.py
"""
from __future__ import annotations
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
from missions._common import load_csv, num
from finops import pricing, sustainability

# $/1M tokens (input, output) — illustrative 2026.
MODEL_PRICES = {"small": (0.20, 0.40), "large": (3.00, 15.00)}
REASONING_CAP_FRACTION = 0.05


def _request_cost(row: dict, tier: str | None = None) -> float:
    input_tokens = int(num(row["input_tokens"]))
    output_tokens = int(num(row["output_tokens"]))
    cached = int(num(row["cached_input_tokens"]))
    batch = bool(int(num(row["is_batch"])))
    price_in, price_out = MODEL_PRICES[tier or row["route_tier"]]
    return pricing.request_cost(input_tokens, output_tokens, price_in, price_out,
                                cached_in=cached, batch=batch)


def reasoning_budget(rows: list[dict], cap_fraction: float = REASONING_CAP_FRACTION) -> dict:
    """Measure reasoning traffic and simulate a cap by rerouting excess to small."""
    cap_fraction = min(1.0, max(0.0, cap_fraction))
    total_requests = len(rows)
    max_reasoning = int(total_requests * cap_fraction)
    reasoning_indices = [i for i, row in enumerate(rows)
                         if int(num(row["is_reasoning"])) == 1]
    # Preserve reasoning for requests with the largest output demand as a transparent proxy.
    kept = set(sorted(reasoning_indices,
                      key=lambda i: (num(rows[i]["output_tokens"]), num(rows[i]["input_tokens"])),
                      reverse=True)[:max_reasoning])

    groups = {"reasoning": {"requests": 0, "tokens": 0, "cost": 0.0, "wh": 0.0},
              "standard": {"requests": 0, "tokens": 0, "cost": 0.0, "wh": 0.0}}
    cap_cost = 0.0
    cap_wh = 0.0
    all_cost = 0.0
    all_wh = 0.0
    for i, row in enumerate(rows):
        inp, out = int(num(row["input_tokens"])), int(num(row["output_tokens"]))
        tokens = inp + out
        is_reasoning = bool(int(num(row["is_reasoning"])))
        group = groups["reasoning" if is_reasoning else "standard"]
        cost = _request_cost(row)
        wh = sustainability.wh_per_query(tokens, is_reasoning=is_reasoning)
        group["requests"] += 1
        group["tokens"] += tokens
        group["cost"] += cost
        group["wh"] += wh
        all_cost += cost
        all_wh += wh

        capped_reasoning = is_reasoning and i not in kept
        cap_cost += _request_cost(row, tier="small" if capped_reasoning else None)
        cap_wh += sustainability.wh_per_query(tokens, is_reasoning=is_reasoning and not capped_reasoning)

    for group in groups.values():
        group["cost"] = round(group["cost"], 4)
        group["wh"] = round(group["wh"], 2)
        group["cost_per_million_tokens"] = round(
            group["cost"] / (group["tokens"] / 1_000_000), 3) if group["tokens"] else 0.0
        group["wh_per_1k_tokens"] = round(
            group["wh"] / (group["tokens"] / 1_000), 3) if group["tokens"] else 0.0
    reasoning_cost_share = groups["reasoning"]["cost"] / all_cost * 100 if all_cost else 0.0
    return {
        "groups": groups,
        "requests": total_requests,
        "reasoning_share_pct": round(groups["reasoning"]["requests"] / total_requests * 100, 1)
            if total_requests else 0.0,
        "reasoning_cost_share_pct": round(reasoning_cost_share, 1),
        "total_cost": round(all_cost, 4), "total_wh": round(all_wh, 2),
        "cap_pct": round(cap_fraction * 100, 1),
        "capped_requests": sum(1 for i in reasoning_indices if i not in kept),
        "cap_cost": round(cap_cost, 4), "cap_wh": round(cap_wh, 2),
        "cap_cost_savings": round(all_cost - cap_cost, 4),
        "cap_wh_savings": round(all_wh - cap_wh, 2),
    }


def run(verbose: bool = True) -> dict:
    rows = load_csv("token_usage.csv")
    base_cost = opt_cost = 0.0
    total_tokens = 0
    for r in rows:
        inp, out = int(num(r["input_tokens"])), int(num(r["output_tokens"]))
        cached = int(num(r["cached_input_tokens"]))
        is_batch = bool(int(num(r["is_batch"])))
        total_tokens += inp + out
        # BASELINE: naive deployment — everything on the large model, no cache, no batch
        lin, lout = MODEL_PRICES["large"]
        base_cost += pricing.request_cost(inp, out, lin, lout)
        # OPTIMIZED: cascade (route_tier), prompt caching, batch API
        pin, pout = MODEL_PRICES[r["route_tier"]]
        opt_cost += pricing.request_cost(inp, out, pin, pout, cached_in=cached, batch=is_batch)

    base_pm = pricing.dollars_per_million(base_cost, total_tokens)
    opt_pm = pricing.dollars_per_million(opt_cost, total_tokens)
    savings_pct = (1 - opt_cost / base_cost) * 100 if base_cost else 0.0
    reasoning = reasoning_budget(rows)

    if verbose:
        print("== M2 Inference Cost Levers ==")
        print(f"requests={len(rows)}  tokens={total_tokens:,}")
        print(f"baseline  : ${base_cost:,.2f}/day   ${base_pm:.3f}/1M-token")
        print(f"optimized : ${opt_cost:,.2f}/day   ${opt_pm:.3f}/1M-token")
        print(f"savings   : {savings_pct:.1f}%  (cascade + caching + batch)")
        print(f"discount stack (batch + 100% cache): {pricing.discount_stack(batch=True, cache_hit_frac=1.0):.3f} of naive")
        rg = reasoning["groups"]["reasoning"]
        sg = reasoning["groups"]["standard"]
        print(f"reasoning: {rg['requests']}/{len(rows)} requests ({reasoning['reasoning_share_pct']:.1f}%), "
              f"{reasoning['reasoning_cost_share_pct']:.1f}% of cost, ${rg['cost']:.4f}, "
              f"{rg['wh']:.2f} Wh ({rg['wh_per_1k_tokens']:.3f} Wh/1k tokens)")
        print(f"standard : {sg['requests']}/{len(rows)} requests, ${sg['cost']:.4f}, "
              f"{sg['wh']:.2f} Wh ({sg['wh_per_1k_tokens']:.3f} Wh/1k tokens)")
        print(f"{reasoning['cap_pct']:.0f}% cap   : reroute {reasoning['capped_requests']} excess requests to small; "
              f"save ${reasoning['cap_cost_savings']:.4f} and {reasoning['cap_wh_savings']:.2f} Wh")

    return {
        "baseline_daily": round(base_cost, 2), "optimized_daily": round(opt_cost, 2),
        "baseline_per_m": round(base_pm, 3), "optimized_per_m": round(opt_pm, 3),
        "savings_pct": round(savings_pct, 1), "total_tokens": total_tokens,
        "reasoning": reasoning,
    }


if __name__ == "__main__":
    run()
