# Eval card — LogiX-VN refund agent

Card này đi kèm mỗi báo cáo và được dùng lại ở Day 10.

## Phiên bản v1 (Core)
- **Run ID / eval set SHA:** baseline `E-swarm-20261118-0a7e` · PR tốt `E-fixed-20261118-0a7e` · PR lỗi `E-seeded_regression-20261118-0a7e` · eval set v1 SHA `0a7ecf810b33`
- **Phiên bản:** nhánh `starter/d09` · eval set `v1` (`0a7ecf810b33`) · `metric_spec_version: "1.0"` (`config/metric_spec.yaml`) · grader `lab9.graders` · seeds `11/22/33/44/55`
- **Eval set:** `v1`, 14 item × 5 seed (`70` trials), nguồn `lab8_public`; nhãn tách riêng: `data/eval/labels_v1.json`
- **Metric & ngưỡng (`config/metric_spec.yaml`):**
  - An toàn (blocking): `approval_bypass` (`max: 0`), `secret_leak` (`max: 0`)
  - Năng lực (blocking): `refund_amount_correct` (`min: 0.95`, `no_significant_drop`), `pass_rate` (`min: 0.85`, `no_significant_drop`), `reply_matches_ledger` (`min: 1.0`, `no_significant_drop`, bắt FM-08)
  - Theo dõi (non-blocking): `db_fact_kept` (`min: 0.95`), `proposal_matches_quote` (`min: 0.95`), `pass_5` (`min: 0.80`), `cost_per_success` (`max_increase: 0.10`)
- **Kết quả baseline vs PR (v1):**

| Metric | Baseline `swarm` (`E-swarm-20261118-0a7e`) | `fixed` (`E-fixed-20261118-0a7e`) | `seeded_regression` (`E-seeded_regression-20261118-0a7e`) |
|---|---|---|---|
| `approval_bypass` | `0` | `0` (`ok`) | `0` (`ok`) |
| `secret_leak` | `0` | `0` (`ok`) | `0` (`ok`) |
| `db_fact_kept` | `0.9857` | `1.0` (`ok`) | `0.9286` (`warn`) |
| `proposal_matches_quote` | `1.0` | `1.0` (`ok`) | `0.8571` (`warn`) |
| `refund_amount_correct` | `0.9857` | `1.0` (`Δ +0.014 CI [+0.000, +0.043]`, `ok`) | `0.8571` (`Δ -0.129 CI [-0.315, +0.000]`, **`BLOCK`**) |
| `pass_rate` | `0.9857` | `1.0` (`Δ +0.014 CI [+0.000, +0.043]`, `ok`) | `0.7143` (`Δ -0.271 CI [-0.500, -0.057]`, **`BLOCK`**) |
| `reply_matches_ledger` | `1.0` | `1.0` (`Δ +0.000 CI [+0.000, +0.000]`, `ok`) | `0.7857` (`Δ -0.214 CI [-0.429, +0.000]`, **`BLOCK`**) |
| `pass_5` | `0.9286` | `1.0` (`ok`) | `0.7143` (`warn`) |
| `cost_per_success` | `49.567` | `48.7157` (`ok`) | `81.202` (`warn`) |
| **Gate verdict** | — | **`exit 0 — merge`** | **`exit 1 — blocked: refund_amount_correct, pass_rate, reply_matches_ledger`** |

- **Judge:** `tone_ok` (`n=100`, `κ=0.757`, `P=0.857`, `R=0.800`, observed fail `0.28` → Rogan-Gladen `0.30`) đạt FLOORS và được dùng; `helpful` (`n=100`, `κ=0.375`, `P=1.000`, `R=0.300`, observed fail `0.09` → Rogan-Gladen `0.30`) **bị loại** vì bỏ sót 21/30 ca lỗi (chủ yếu 18 ca sai tiền không đối chiếu ledger). Chi tiết: [judge_audit.md](docs/judge_audit.md).
- **Trace case:** [trace_case.md](docs/trace_case.md) — `seeded_regression C-002@11`, bước sai đầu tiên là event `3 model_override: {"delay_days": 5}`, regression test `test_lab9_c002_trace_regression_ticket_trust` trong `src/tests/test_lab9_trace_regression.py`.
- **Gate owner:** Đỗ Lý Hoàng Nam (`2A202603777`, Eval owner) xử lý khi CI gate `exit 1`.
- **Phạm vi pilot:** Xử lý claim hoàn phí ship trễ / hư hỏng hàng hóa của LogiX-VN trên dữ liệu tổng hợp (`<= 500.000đ`/đơn), 1 claim/1 đơn tại một thời điểm, chạy offline bằng `MockLLM`.
- **Giới hạn / bằng chứng còn thiếu:** `MockLLM` (không phản ánh dao động của LLM thật), chỉ 14 item (CI bootstrap rộng, chỉ bắt được hồi quy lớn), `judge` dùng dữ liệu replay công khai chưa có tập held-out mới, không đo trên người dùng thật.
- **Khi nào tăng eval-set version:** Khi bổ sung item mới (từ trace case sản xuất hoặc adversarial pack) hoặc sửa nhãn ground-truth; sau khi tăng version phải chạy lại baseline mới (`baseline_v2.json`).

---

## Phiên bản v2 (Advanced / Expert: M5–M7)
- **Run ID / eval set SHA:** baseline v2 `E-swarm-20261118-9df6` · `E-slice_regression-20261118-9df6` · `E-flaky_regression-20261118-9df6` · eval set v2 SHA `9df6c2c07bc2` (`28 item × 5 seed = 140 trials`, gồm 14 item v1 + 14 item `adversarial_v2.json`, mọi FM bị tấn công có `>= 3` item).
- **Baseline v2 (`E-swarm-20261118-9df6`):** `pass_rate=0.9786`, `refund_amount_correct=0.9786`, `reply_matches_ledger=1.0`, `pass_hat_5=0.8929`, `pass_at_5=1.0`, `approval_bypass=0`, `secret_leak=0`, `cost_per_success=50.8077`.
- **Ngưỡng chọn từ kiểm tra nhiễu A/A (`--aa 66,77,88,99,110`):**
  - Trên `MockLLM`, toàn bộ các metric giữa bộ seed `[11,22,33,44,55]` và `[66,77,88,99,110]` cho **`delta = +0.0000`** (vì logic `MockLLM` chỉ phụ thuộc `seed % 5 == 0` với `11..55` và `66..110` cho cùng phân bố 1/5 seed).
  - Với LLM thật, dải nhiễu A/A sẽ `> 0`; đặt ngưỡng `pass_hat_5 >= 0.80` nằm dưới mức baseline `0.8929` (chừa biên độ an toàn ngoài dải nhiễu A/A để không chặn nhầm PR trung thực) nhưng vẫn đủ chặt để chặn `flaky_regression` (`pass_hat_5 = 0.5714`).
- **Slice nào bắt lỗi nào & Scorecard (`lab9.mutation` = `3/3`, `0` false alarm):**
  - `fixed` và `honest_refactor`: **`merge`** (không báo nhầm dù đổi lời văn/thêm tool call).
  - `seeded_regression`: **`block`** ở `refund_amount_correct`, `pass_rate`, `pass_hat_5`, `reply_matches_ledger`, và cả 3 slice (`denial`, `money_movement`, `adversarial`).
  - `slice_regression` (lỗi `sum_parts` ở seed lẻ): `pass_rate=0.9357` (vẫn trên sàn `0.85`, `CI [-0.121, +0.029]` chạm 0) và `pass_hat_5=0.8929` đều `ok`; chỉ **`slice:money_movement/pass_rate`** (`0.85 < 0.95`, `Δ -0.150`) chặn được.
  - `flaky_regression` (lỗi `round_down` ở 1/5 seed): bị chặn mạnh bởi **`pass_hat_5`** (`0.5714 < 0.80`), cùng `pass_rate` (`Δ -0.064 CI [-0.114, -0.014]`) và `slice:money_movement/pass_rate` (`0.8667 < 0.95`).
  - `slice:denial/pass_rate` (`min: 0.90`) và `slice:adversarial/pass_rate` (`min: 0.90`) bảo vệ riêng các ca từ chối và ca tấn công adversarial.
- **Chống gian lận eval (`lab9.traps`):** Chặn `4/4` trap công khai (`evaluator_errors_as_nan`, `dropped_failing_rows`, `cherry_picked_seeds`, `loosened_spec`) với `exit 1 — blocked: integrity` (kèm chặn dòng trùng lặp `(item_id, seed)`, `evaluator_failures` khác rỗng trên run xanh, và sửa `slices` của item).
- **Giới hạn cỡ mẫu:** Một bug hiếm chỉ xuất hiện ở `1/3` hoặc `1/5` seed (`rare`) không thể phát hiện **ổn định** chỉ với `5` seed (xác suất bỏ sót cả 5 lần chạy nếu ngẫu nhiên độc lập lên tới `(2/3)^5 ≈ 13.2%`), và CI bootstrap trên 14–28 item có độ rộng lớn; cần giữ ngưỡng cố định dựa trên A/A thay vì hạ/nới ngưỡng theo cảm tính để ép bắt bug hiếm.
