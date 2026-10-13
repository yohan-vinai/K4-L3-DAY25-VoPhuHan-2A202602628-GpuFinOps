"""Vietnamese report sections for the measured Day 25 extensions."""
from __future__ import annotations


def build_details(r1: dict, r2: dict, r3: dict, levers: dict) -> str:
    reasoning = r2["reasoning"]
    schedule = r3["carbon_schedule"]
    rg, sg = reasoning["groups"]["reasoning"], reasoning["groups"]["standard"]
    lie_rows = [
        f"| {row['gpu_id']} | {row['gpu_type']} | {row['gpu_util_pct']:.1f}% | {row['mfu']:.3f} |"
        for row in r1["lies"]
    ] or ["| Không có | | | |"]
    region_rows = [
        f"| {region} | ${values['price_per_kwh']:.3f} | {values['carbon_g_per_kwh']} | "
        f"${values['cost_usd']:,.2f} | {values['carbon_kg']:,.2f} kgCO2e |"
        for region, values in schedule["regions"].items()
    ]
    ranked = sorted(levers.items(), key=lambda item: item[1], reverse=True)
    actions = [f"{i}. **{name}**: ưu tiên vì savings mô phỏng ${amount:,.0f}/tháng."
               for i, (name, amount) in enumerate(ranked[:3], start=1)]
    return f"""## Unit economics: chi phí trên một triệu token

| Kịch bản | Chi phí mỗi ngày | USD/1M token |
|---|---:|---:|
| Baseline | ${r2['baseline_daily']:,.2f} | ${r2['baseline_per_m']:.3f} |
| Cascade + cache + batch | ${r2['optimized_daily']:,.2f} | ${r2['optimized_per_m']:.3f} |

## GPU-Util Lie và tác động chi phí

GPU-Util ghi nhận thời gian GPU bận, còn MFU so sánh FLOPs thực đạt với mức đỉnh. GPU có thể bận chờ dữ liệu bộ nhớ hoặc chịu overhead kernel mà không tạo ra nhiều FLOPs; telemetry này không xác định nguyên nhân stall cụ thể. GPU-Util cao tự nó không chứng minh GPU chạy hiệu quả. Policy right-size trong M5 ước tính giảm **${levers['Right-size util-lies']:,.0f}/tháng**.

| GPU | Loại | GPU-Util trung bình | MFU |
|---|---|---:|---:|
{chr(10).join(lie_rows)}

## Extension 4: Ngân sách Reasoning

| Nhóm | Request | Tỷ lệ traffic | Chi phí | Tỷ lệ tổng chi phí | USD/1M token | Wh/1k token |
|---|---:|---:|---:|---:|---:|---:|
| Reasoning | {rg['requests']:,} | {reasoning['reasoning_share_pct']:.1f}% | ${rg['cost']:.4f} | {reasoning['reasoning_cost_share_pct']:.1f}% | ${rg['cost_per_million_tokens']:.3f} | {rg['wh_per_1k_tokens']:.3f} |
| Thường | {sg['requests']:,} | {100-reasoning['reasoning_share_pct']:.1f}% | ${sg['cost']:.4f} | {100-reasoning['reasoning_cost_share_pct']:.1f}% | ${sg['cost_per_million_tokens']:.3f} | {sg['wh_per_1k_tokens']:.3f} |

Giới hạn reasoning ở **{reasoning['cap_pct']:.0f}% tổng request**: giữ request có output dài nhất làm proxy nhu cầu, chuyển {reasoning['capped_requests']:,} request vượt ngưỡng sang tier `small` và tắt cờ reasoning. Mô phỏng giảm **${reasoning['cap_cost_savings']:.4f}** chi phí inference/ngày và **{reasoning['cap_wh_savings']:.2f} Wh/ngày**. Dataset không có nhãn độ phức tạp hoặc chất lượng để xác nhận request nào an toàn khi hạ tier.

## Extension 5: Carbon-aware Scheduling

So sánh áp dụng cho {schedule['jobs']} job interruptible, tổng điện năng ước tính **{schedule['energy_kwh']:,.1f} kWh**. Mỗi vùng dùng cùng lượng điện; giá điện và cường độ carbon khác nhau.

| Vùng | USD/kWh | gCO2/kWh | Chi phí điện | Phát thải |
|---|---:|---:|---:|---:|
{chr(10).join(region_rows)}

Rẻ nhất là **{schedule['cheapest_region']}**, sạch nhất là **{schedule['cleanest_region']}**, vùng cân bằng theo trung bình thứ hạng chuẩn hóa là **{schedule['balanced_region']}**. Chuyển từ `us-east-1` sang vùng sạch nhất giảm **{schedule['cleanest_carbon_saved_kg']:,.2f} kgCO2e ({schedule['cleanest_carbon_saved_pct']:.1f}%)**, thay đổi tiền điện **${schedule['cleanest_cost_delta_usd']:+,.2f}**. Mô hình chưa tính latency, truyền dữ liệu hoặc residency.

## Hành động ưu tiên

Các lever xếp theo savings mô phỏng, không phải cam kết production:

{chr(10).join(actions)}
"""


def build_writeup(baseline: float, optimized: float, total_pct: float,
                  r1: dict, r2: dict, r3: dict, levers: dict) -> str:
    reasoning, schedule = r2["reasoning"], r3["carbon_schedule"]
    rg, sg = reasoning["groups"]["reasoning"], reasoning["groups"]["standard"]
    ranked = sorted(levers.items(), key=lambda item: item[1], reverse=True)
    lever_table = [f"| {name} | ${amount:,.0f} |" for name, amount in ranked]
    lies = ", ".join(row["gpu_id"] for row in r1["lies"])
    return f"""# Phân tích Lab 25: Tối ưu chi phí GPU cho NimbusAI

## Kết quả chính

Pipeline ước tính chi phí tháng giảm từ **${baseline:,.0f}** xuống **${optimized:,.0f}**, tiết kiệm **${baseline-optimized:,.0f} ({total_pct:.1f}%)**. Riêng inference, chi phí giảm từ **${r2['baseline_per_m']:.3f}** xuống **${r2['optimized_per_m']:.3f} trên mỗi 1M token**, tương ứng **{r2['savings_pct']:.1f}%**. Đây là mô phỏng theo catalog tháng 6/2026.

## Các đòn bẩy và GPU-Util Lie

| Đòn bẩy | Tiết kiệm ước tính/tháng |
|---|---:|
{chr(10).join(lever_table)}

Đòn bẩy lớn nhất là **{ranked[0][0]}**, với ${ranked[0][1]:,.0f}/tháng theo giả định lab. Telemetry gắn cờ {lies}: GPU-Util cao nhưng MFU thấp. GPU-Util đo thời gian thiết bị bận, không đo tỷ lệ FLOPs đỉnh đã đạt; memory stall hoặc overhead có thể khiến GPU bận mà throughput tính toán thấp. Dataset không ghi nguyên nhân stall nên đây là giải thích cơ chế, không phải chẩn đoán phần cứng.

## Hai extension đã triển khai

**Ngân sách Reasoning.** Có {rg['requests']:,}/{reasoning['requests']:,} request reasoning ({reasoning['reasoning_share_pct']:.1f}% traffic), chiếm {reasoning['reasoning_cost_share_pct']:.1f}% chi phí inference. Nhóm này dùng {rg['wh_per_1k_tokens']:.3f} Wh/1k token, so với {sg['wh_per_1k_tokens']:.3f} Wh/1k token ở nhóm thường, đúng hệ số 80× trong mô hình khi so cùng số token. Giới hạn ở {reasoning['cap_pct']:.0f}% request chuyển {reasoning['capped_requests']:,} request reasoning dư sang `small`, tiết kiệm ${reasoning['cap_cost_savings']:.4f} và {reasoning['cap_wh_savings']:.2f} Wh mỗi ngày. Mô phỏng giữ request có output dài nhất làm proxy vì dataset thiếu nhãn độ phức tạp; cần kiểm tra chất lượng trước khi áp dụng.

**Carbon-aware Scheduling.** {schedule['jobs']} job interruptible dùng khoảng {schedule['energy_kwh']:,.1f} kWh. `{schedule['cheapest_region']}` rẻ nhất theo tiền điện, `{schedule['cleanest_region']}` sạch nhất, còn `{schedule['balanced_region']}` cân bằng theo trung bình thứ hạng chuẩn hóa. Chuyển từ `us-east-1` sang vùng sạch nhất giảm {schedule['cleanest_carbon_saved_kg']:,.2f} kgCO2e ({schedule['cleanest_carbon_saved_pct']:.1f}%) và thay đổi tiền điện ${schedule['cleanest_cost_delta_usd']:+,.2f}. Cần cân nhắc latency, truyền dữ liệu và residency.

## Ba khuyến nghị cho NimbusAI

1. Ưu tiên **{ranked[0][0]}**, lever có savings mô phỏng lớn nhất, rồi đo lại cost/token trên traffic thật.
2. Theo dõi MFU/MBU cùng GPU-Util và xác minh bottleneck trước khi đổi GPU hoặc tắt capacity.
3. Thử reasoning cap và lịch carbon với guardrail chất lượng/latency; theo dõi tiền điện riêng với tiền thuê GPU.

## Giới hạn diễn giải

Dữ liệu và giá tổng hợp, không phải hóa đơn production. Ước tính reasoning dùng hệ số 80× và proxy output length, không có đánh giá chất lượng câu trả lời. Carbon schedule dùng công suất nameplate và thời lượng job, không gồm PUE, tải thực tế hoặc network. Re-baseline trước khi áp dụng.
"""
