"""M3 — Purchasing Strategy: break-even, tier choice, spot-checkpoint sim (deck §4).

Run: python missions/m3_purchasing.py
"""
from __future__ import annotations
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
from missions._common import load_csv, num, catalog_by_type
from finops import pricing, sustainability

DAYS = 30


def carbon_aware_schedule(jobs: list[dict], catalog: dict) -> dict:
    """Compare electricity cost and carbon for interruptible jobs across regions."""
    interruptible = [job for job in jobs if int(num(job["interruptible"])) == 1]
    total_kwh = 0.0
    for job in interruptible:
        gpu = catalog[job["gpu_type"]]
        hours = num(job["hours_per_day"]) * num(job["days"])
        count = int(num(job["num_gpus"]))
        total_kwh += num(gpu["watts"]) * hours * count / 1000.0

    regions = {}
    for region, carbon_intensity in sustainability.REGION_CARBON.items():
        price = sustainability.REGION_PRICE_KWH[region]
        regions[region] = {
            "price_per_kwh": price,
            "carbon_g_per_kwh": carbon_intensity,
            "energy_kwh": round(total_kwh, 2),
            "cost_usd": round(total_kwh * price, 2),
            "carbon_kg": round(total_kwh * carbon_intensity / 1000.0, 2),
        }

    cheapest = min(regions, key=lambda region: regions[region]["cost_usd"])
    cleanest = min(regions, key=lambda region: regions[region]["carbon_kg"])
    costs = [row["cost_usd"] for row in regions.values()]
    carbons = [row["carbon_kg"] for row in regions.values()]
    cost_span, carbon_span = max(costs) - min(costs), max(carbons) - min(carbons)

    def balanced_score(region: str) -> float:
        row = regions[region]
        cost_score = (row["cost_usd"] - min(costs)) / cost_span if cost_span else 0.0
        carbon_score = (row["carbon_kg"] - min(carbons)) / carbon_span if carbon_span else 0.0
        return (cost_score + carbon_score) / 2.0
    balanced = min(regions, key=balanced_score)
    base = regions["us-east-1"]
    destination = regions[cleanest]
    return {
        "jobs": len(interruptible), "energy_kwh": round(total_kwh, 2),
        "regions": regions, "baseline_region": "us-east-1",
        "cheapest_region": cheapest, "cleanest_region": cleanest,
        "balanced_region": balanced,
        "cleanest_cost_delta_usd": round(destination["cost_usd"] - base["cost_usd"], 2),
        "cleanest_carbon_saved_kg": round(base["carbon_kg"] - destination["carbon_kg"], 2),
        "cleanest_carbon_saved_pct": round((base["carbon_kg"] - destination["carbon_kg"])
                                           / base["carbon_kg"] * 100, 1) if base["carbon_kg"] else 0.0,
    }


def run(verbose: bool = True) -> dict:
    jobs = load_csv("workloads.csv")
    cat = catalog_by_type()
    on_demand_monthly = optimized_monthly = 0.0
    recs = []
    for j in jobs:
        gtype = j["gpu_type"]
        ngpu = int(num(j["num_gpus"]))
        hpd = num(j["hours_per_day"])
        interruptible = bool(int(num(j["interruptible"])))
        c = cat[gtype]
        gpu_hours = hpd * DAYS * ngpu
        od = num(c["on_demand_hr"])
        on_demand_cost = gpu_hours * od

        tier = pricing.recommend_tier(hpd, interruptible)
        if tier == "spot":
            sim = pricing.spot_checkpoint_cost(gpu_hours, num(c["spot_hr"]), od)
            opt_cost = sim["spot_cost"]
        elif tier == "reserved":
            opt_cost = gpu_hours * num(c["reserved_3yr_hr"])
        else:
            opt_cost = on_demand_cost

        on_demand_monthly += on_demand_cost
        optimized_monthly += opt_cost
        recs.append({"job_id": j["job_id"], "gpu_type": gtype, "tier": tier,
                     "on_demand": round(on_demand_cost), "optimized": round(opt_cost)})

    savings = on_demand_monthly - optimized_monthly
    savings_pct = savings / on_demand_monthly * 100 if on_demand_monthly else 0.0
    carbon_schedule = carbon_aware_schedule(jobs, cat)

    if verbose:
        print("== M3 Purchasing Strategy ==")
        print(f"break-even utilization @ 45% reserved discount = {pricing.break_even_utilization(0.45):.0%}")
        print(f"{'job':18}{'gpu':7}{'tier':11}{'on-demand':>12}{'optimized':>12}")
        for r in recs:
            print(f"{r['job_id']:18}{r['gpu_type']:7}{r['tier']:11}${r['on_demand']:>11,}${r['optimized']:>11,}")
        print(f"\nmonthly: on-demand ${on_demand_monthly:,.0f} -> optimized ${optimized_monthly:,.0f}  ({savings_pct:.1f}% saved)")
        print("\nCarbon-aware schedule for interruptible jobs:")
        print(f"  candidates={carbon_schedule['jobs']}  energy={carbon_schedule['energy_kwh']:,.1f} kWh")
        for region, metrics in carbon_schedule["regions"].items():
            print(f"  {region:17} ${metrics['cost_usd']:>9,.2f}  {metrics['carbon_kg']:>9,.2f} kgCO2e")
        print(f"  cheapest={carbon_schedule['cheapest_region']}; cleanest={carbon_schedule['cleanest_region']}; "
              f"balanced={carbon_schedule['balanced_region']}")
        print(f"  us-east-1 -> cleanest: {carbon_schedule['cleanest_carbon_saved_kg']:,.2f} kgCO2e "
              f"({carbon_schedule['cleanest_carbon_saved_pct']:.1f}% less), "
              f"electricity delta ${carbon_schedule['cleanest_cost_delta_usd']:,.2f}")

    return {"recommendations": recs, "on_demand_monthly": round(on_demand_monthly),
            "optimized_monthly": round(optimized_monthly), "savings_pct": round(savings_pct, 1),
            "carbon_schedule": carbon_schedule}


if __name__ == "__main__":
    run()
