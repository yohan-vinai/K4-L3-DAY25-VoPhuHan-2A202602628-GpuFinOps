# NimbusAI — Báo cáo Tối ưu Chi phí GPU

**Kỳ báo cáo (Period):** monthly
**Chi phí cơ sở (Baseline spend):** $27,133
**Chi phí sau tối ưu (Optimized spend):** $14,626
**Projected savings / Tiết kiệm dự kiến:** $12,507  (**46%**)

## Savings by lever / Tiết kiệm theo đòn bẩy

| Đòn bẩy (Lever) | Tiết kiệm (USD/tháng) |
|---|---|
| Inference (cascade/cache/batch) | $1,212 |
| Purchasing (spot/reserved) | $10,040 |
| Right-size util-lies | $655 |
| Kill idle GPUs | $600 |

## Sustainability / Bền vững

- Năng lượng mỗi truy vấn (Energy per query): 0.24 Wh
- Carbon mỗi truy vấn (Carbon per query): 0.091 gCO2e
- Vùng sạch nhất theo carbon: europe-north1

## Unit economics: chi phí trên một triệu token

| Kịch bản | Chi phí mỗi ngày | USD/1M token |
|---|---:|---:|
| Baseline | $48.87 | $6.488 |
| Cascade + cache + batch | $8.48 | $1.126 |

## GPU-Util Lie và tác động chi phí

GPU-Util ghi nhận thời gian GPU bận, còn MFU so sánh FLOPs thực đạt với mức đỉnh. GPU có thể bận chờ dữ liệu bộ nhớ hoặc chịu overhead kernel mà không tạo ra nhiều FLOPs; telemetry này không xác định nguyên nhân stall cụ thể. GPU-Util cao tự nó không chứng minh GPU chạy hiệu quả. Policy right-size trong M5 ước tính giảm **$655/tháng**.

| GPU | Loại | GPU-Util trung bình | MFU |
|---|---|---:|---:|
| gpu-h100-4 | H100 | 98.2% | 0.194 |
| gpu-a10g-1 | A10G | 96.9% | 0.268 |

## Extension 4: Ngân sách Reasoning

| Nhóm | Request | Tỷ lệ traffic | Chi phí | Tỷ lệ tổng chi phí | USD/1M token | Wh/1k token |
|---|---:|---:|---:|---:|---:|---:|
| Reasoning | 201 | 8.4% | $1.3965 | 16.5% | $1.125 | 24.000 |
| Thường | 2,199 | 91.6% | $7.0882 | 83.5% | $1.127 | 0.300 |

Giới hạn reasoning ở **5% tổng request**: giữ request có output dài nhất làm proxy nhu cầu, chuyển 81 request vượt ngưỡng sang tier `small` và tắt cờ reasoning. Mô phỏng giảm **$0.2970** chi phí inference/ngày và **7833.56 Wh/ngày**. Dataset không có nhãn độ phức tạp hoặc chất lượng để xác nhận request nào an toàn khi hạ tier.

## Extension 5: Carbon-aware Scheduling

So sánh áp dụng cho 5 job interruptible, tổng điện năng ước tính **1,789.0 kWh**. Mỗi vùng dùng cùng lượng điện; giá điện và cường độ carbon khác nhau.

| Vùng | USD/kWh | gCO2/kWh | Chi phí điện | Phát thải |
|---|---:|---:|---:|---:|
| us-east-1 | $0.120 | 380 | $214.68 | 679.82 kgCO2e |
| us-west-2 | $0.070 | 120 | $125.23 | 214.68 kgCO2e |
| europe-north1 | $0.090 | 30 | $161.01 | 53.67 kgCO2e |
| europe-central2 | $0.180 | 660 | $322.02 | 1,180.74 kgCO2e |
| us-east-wa | $0.055 | 90 | $98.39 | 161.01 kgCO2e |

Rẻ nhất là **us-east-wa**, sạch nhất là **europe-north1**, vùng cân bằng theo trung bình thứ hạng chuẩn hóa là **us-east-wa**. Chuyển từ `us-east-1` sang vùng sạch nhất giảm **626.15 kgCO2e (92.1%)**, thay đổi tiền điện **$-53.67**. Mô hình chưa tính latency, truyền dữ liệu hoặc residency.

## Hành động ưu tiên

Các lever xếp theo savings mô phỏng, không phải cam kết production:

1. **Purchasing (spot/reserved)**: ưu tiên vì savings mô phỏng $10,040/tháng.
2. **Inference (cascade/cache/batch)**: ưu tiên vì savings mô phỏng $1,212/tháng.
3. **Right-size util-lies**: ưu tiên vì savings mô phỏng $655/tháng.

_Các số liệu giá là snapshot tháng 6/2026; cần đo lại trước khi áp dụng thực tế._
