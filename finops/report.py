"""Report assembly — the lab's deliverable: baseline vs optimized + savings chart."""
from __future__ import annotations


def build_report(baseline_usd: float, optimized_usd: float, levers: dict,
                 sustainability: dict | None = None, period: str = "monthly",
                 details: str = "") -> str:
    """Return a markdown cost-optimization report."""
    savings = baseline_usd - optimized_usd
    pct = (savings / baseline_usd * 100.0) if baseline_usd > 0 else 0.0
    lines = [
        "# NimbusAI — Báo cáo Tối ưu Chi phí GPU",
        "",
        f"**Kỳ báo cáo (Period):** {period}",
        f"**Chi phí cơ sở (Baseline spend):** ${baseline_usd:,.0f}",
        f"**Chi phí sau tối ưu (Optimized spend):** ${optimized_usd:,.0f}",
        f"**Projected savings / Tiết kiệm dự kiến:** ${savings:,.0f}  (**{pct:.0f}%**)",
        "",
        "## Savings by lever / Tiết kiệm theo đòn bẩy",
        "",
        "| Đòn bẩy (Lever) | Tiết kiệm (USD/tháng) |",
        "|---|---|",
    ]
    for name, amount in levers.items():
        lines.append(f"| {name} | ${amount:,.0f} |")
    if sustainability:
        lines += [
            "",
            "## Sustainability / Bền vững",
            "",
            f"- Năng lượng mỗi truy vấn (Energy per query): {sustainability.get('wh_per_query', 0):.2f} Wh",
            f"- Carbon mỗi truy vấn (Carbon per query): {sustainability.get('carbon_g', 0):.3f} gCO2e",
            f"- Vùng sạch nhất theo carbon: {sustainability.get('best_region', 'n/a')}",
        ]
    if details:
        lines += ["", details.rstrip()]
    lines += ["", "_Các số liệu giá là snapshot tháng 6/2026; cần đo lại trước khi áp dụng thực tế._"]
    return "\n".join(lines)


def savings_waterfall(levers: dict, path: str) -> str:
    """Write a cumulative savings waterfall PNG. Returns the path or empty if unavailable."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        return ""
    names = list(levers.keys())
    vals = [levers[n] for n in names]
    fig, ax = plt.subplots(figsize=(9, 5))
    cumulative = 0.0
    for i, value in enumerate(vals):
        after = cumulative + value
        bottom = min(cumulative, after)
        height = abs(value)
        ax.bar(i, height, bottom=bottom, color="#2e548a" if value >= 0 else "#b84a4a", width=0.68)
        ax.text(i, max(cumulative, after) + max(vals) * 0.015, f"${value:,.0f}",
                ha="center", va="bottom", fontsize=8)
        if i < len(vals) - 1:
            ax.plot([i + 0.34, i + 0.66], [after, after], color="#666666", linewidth=0.8)
        cumulative = after
    ax.set_xticks(range(len(names)), names)
    ax.set_ylabel("Tiết kiệm lũy kế (USD/tháng)")
    ax.set_title("GPU FinOps: savings waterfall / Phân rã tiết kiệm")
    plt.xticks(rotation=20, ha="right")
    ax.set_ylim(0, cumulative + max(vals) * 0.14)
    plt.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)
    return path
