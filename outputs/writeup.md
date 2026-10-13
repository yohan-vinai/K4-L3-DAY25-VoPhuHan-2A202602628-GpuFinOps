# Phân tích Lab 25: Tối ưu chi phí GPU cho NimbusAI

## Kết quả chính

Pipeline ước tính chi phí tháng giảm từ **$27,133** xuống **$14,626**, tiết kiệm **$12,507 (46.1%)**. Riêng inference, chi phí giảm từ **$6.488** xuống **$1.126 trên mỗi 1M token**, tương ứng **82.6%**. Đây là mô phỏng theo catalog tháng 6/2026.

## Các đòn bẩy và GPU-Util Lie

| Đòn bẩy | Tiết kiệm ước tính/tháng |
|---|---:|
| Purchasing (spot/reserved) | $10,040 |
| Inference (cascade/cache/batch) | $1,212 |
| Right-size util-lies | $655 |
| Kill idle GPUs | $600 |

Đòn bẩy lớn nhất là **Purchasing (spot/reserved)**, với $10,040/tháng theo giả định lab. Telemetry gắn cờ gpu-h100-4, gpu-a10g-1: GPU-Util cao nhưng MFU thấp. GPU-Util đo thời gian thiết bị bận, không đo tỷ lệ FLOPs đỉnh đã đạt; memory stall hoặc overhead có thể khiến GPU bận mà throughput tính toán thấp. Dataset không ghi nguyên nhân stall nên đây là giải thích cơ chế, không phải chẩn đoán phần cứng.

## Hai extension đã triển khai

**Ngân sách Reasoning.** Có 201/2,400 request reasoning (8.4% traffic), chiếm 16.5% chi phí inference. Nhóm này dùng 24.000 Wh/1k token, so với 0.300 Wh/1k token ở nhóm thường, đúng hệ số 80× trong mô hình khi so cùng số token. Giới hạn ở 5% request chuyển 81 request reasoning dư sang `small`, tiết kiệm $0.2970 và 7833.56 Wh mỗi ngày. Mô phỏng giữ request có output dài nhất làm proxy vì dataset thiếu nhãn độ phức tạp; cần kiểm tra chất lượng trước khi áp dụng.

**Carbon-aware Scheduling.** 5 job interruptible dùng khoảng 1,789.0 kWh. `us-east-wa` rẻ nhất theo tiền điện, `europe-north1` sạch nhất, còn `us-east-wa` cân bằng theo trung bình thứ hạng chuẩn hóa. Chuyển từ `us-east-1` sang vùng sạch nhất giảm 626.15 kgCO2e (92.1%) và thay đổi tiền điện $-53.67. Cần cân nhắc latency, truyền dữ liệu và residency.

## Ba khuyến nghị cho NimbusAI

1. Ưu tiên **Purchasing (spot/reserved)**, lever có savings mô phỏng lớn nhất, rồi đo lại cost/token trên traffic thật.
2. Theo dõi MFU/MBU cùng GPU-Util và xác minh bottleneck trước khi đổi GPU hoặc tắt capacity.
3. Thử reasoning cap và lịch carbon với guardrail chất lượng/latency; theo dõi tiền điện riêng với tiền thuê GPU.

## Giới hạn diễn giải

Dữ liệu và giá tổng hợp, không phải hóa đơn production. Ước tính reasoning dùng hệ số 80× và proxy output length, không có đánh giá chất lượng câu trả lời. Carbon schedule dùng công suất nameplate và thời lượng job, không gồm PUE, tải thực tế hoặc network. Re-baseline trước khi áp dụng.
