# Trace case: từ trace tới quyết định sai đầu tiên

Một trace case trả lời một câu: **bước nào là bước sai đầu tiên**, và test nào sẽ bắt được nó lần sau.

```bash
cd src
python -m lab9.trace_case --shape seeded_regression --claim C-002 --seed 11
python -m lab9.trace_case --shape fixed --claim C-002 --seed 11   # đối chứng
```

Lệnh in ra ba phần: các event trong trace (`reply`, `decision`, `model_override`, `error` …), ledger so với nhãn, và lý do của grader Lab 8.

## Case đã phân tích: `seeded_regression C-002@11`

| Trường | Nội dung |
|---|---|
| Trial | `seeded_regression C-002@11`, report run ID `E-seeded_regression-20261118-0a7e` (trace `run_id`: `seeded_regression-C-002-11`; đối chứng `swarm C-002@55` trong `E-swarm-20261118-0a7e` cũng dính cùng lỗi) |
| Triệu chứng | `lab8.metrics.trial_pass` FAIL với lý do `status resolved != denied`. Ledger ghi `refund_vnd=20000`, `refund_count=1` (nhãn đúng là `0` / `0`), còn event `6 reply` báo `"Dạ, LogiX đã hoàn 20.000đ cho đơn O-202."`. |
| Bước sai đầu tiên | Event `3 model_override`: `{"delay_days": 5}` |
| Vì sao là bước *đầu tiên* | Event `1 handoff` tạo gói quyền đọc đúng (`owner_order_only`, `allowed_tools` chỉ gồm tool đọc); event `2 investigator` đọc đúng dữ liệu DB của đơn `O-202` (`status: "delivered"`, `delay_days: 2`, không đủ điều kiện `min_delay_days: 3`). Tới event `3`, agent lấy `5 ngày` từ văn bản ticket ghi đè lên `delay_days=2` của DB, kéo theo event `4 quote` tính sai `20000` và ghi hoàn tiền. |
| Failure mode | `FM-03` (`ticket_trust — tin ticket hơn DB`) trong [failure_taxonomy.md](docs/failure_taxonomy.md) |
| Đối chứng | Trên `fixed C-002@11` (`lab8 grader: PASS`): không có event `model_override`; event `3 quote` giữ nguyên DB `delay_days=2` nên tính `amount_vnd: 0` (`reason: "no_entitlement"`), ledger `refund_vnd=0`, `status=denied`, event `4 reply` từ chối đúng quy định. |
| Regression test | `test_lab9_c002_trace_regression_ticket_trust` trong `src/tests/test_lab9_trace_regression.py` — assert `DbFactKept` (`model_override`) và `TrialPass`: fail trên `seeded_regression` (`refund_vnd=20000`, `DbFactKept=False`), pass trên `fixed` (`refund_vnd=0`, `status=denied`, `DbFactKept=True`). |
| Chưa chắc chắn | Trace được chạy trên `MockLLM` với rule cố định của variant; chưa kiểm chứng prompt thực tế trên LLM thật khi ticket diễn đạt số ngày mơ hồ hơn (ví dụ không có số nguyên rõ ràng). |

## Quy tắc

- Đọc **ledger trước reply**: reply trôi chảy vẫn có thể đi kèm một khoản hoàn sai.
- "Bước sai đầu tiên" phải dẫn số event cụ thể, không phải "agent bị nhầm".
- Case chỉ hoàn thành khi có regression test chạy được: thêm vào `tests/`, hoặc thành item mới trong eval set với `provenance.from_trace`.
