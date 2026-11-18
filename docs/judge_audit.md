# Judge audit

Chạy: `python -m lab9.judge --csv <file> --audit 5`

| Tiêu chí | n | κ | Precision | Recall | Đạt FLOORS (κ≥0.6, P≥0.8, R≥0.7)? | Quyết định |
|---|---|---|---|---|---|---|
| tone_ok (`data/eval/judge_tone_public.csv`) | 100 | 0.757 | 0.857 | 0.800 | Có (κ≥0.6, P≥0.8, R≥0.7; `tp=24, fp=4, fn=6, tn=66`; fail rate observed `0.28` → Rogan-Gladen `0.3`) | **dùng** |
| helpful (`data/eval/judge_helpful_public.csv`) | 100 | 0.375 | 1.000 | 0.300 | Không (κ=0.375 < 0.6, R=0.300 < 0.7; `tp=9, fp=0, fn=21, tn=70`; fail rate observed `0.09` → Rogan-Gladen `0.3`) | **loại** |

## ≥5 case audit thủ công
| # | Case | Judge nói | Người nói | Ai đúng? | Ghi chú & hành động sửa rubric |
|---|---|---|---|---|---|
| 1 | `H-008` ("Em đã hoàn tiền cho anh rồi nha, anh check giúp em.") | PASS | FAIL | Người đúng | Xưng `"em"` + `"nha"` quá suồng sã; sửa rubric `tone_ok`: cấm đại từ thân mật (`em`/`nha`/`nhé`) và buộc xưng `"LogiX"` – `"anh/chị"`. |
| 2 | `H-029` ("Dạ, vui lòng chờ. Hệ thống đang xử lý, không cần nhắn thêm.") | PASS | FAIL | Người đúng | Judge bị đánh lừa bởi từ `"Dạ, vui lòng"`; bổ sung ví dụ negative trong rubric về câu mệnh lệnh/đuổi khéo (`"không cần nhắn thêm"`). |
| 3 | `H-051` ("Dạ, LogiX đã refund 90.000đ cho đơn O-202 ạ.") | FAIL | PASS | Người đúng | Judge tự phạt từ tiếng Anh `"refund"`; thêm whitelist thuật ngữ nghiệp vụ cho phép (`refund`, `order`, `voucher`) vào rubric `tone_ok`. |
| 4 | `H-063` ("Dạ, LogiX đã hoàn 20.000đ và sẽ hoàn thêm cho anh/chị ạ.") | PASS | FAIL | Người đúng | Hứa `"sẽ hoàn thêm"` ngoài kết quả hệ thống; thêm luật nghiêm cấm cam kết bồi thường bổ sung không có trong dữ kiện. |
| 5 | `H-081` ("Dạ, đơn O-107 chưa đủ điều kiện hoàn theo chính sách hiện hành ạ.") | FAIL | PASS | Judge đúng | Nhãn người gán nhầm (đọc nhầm ticket); sửa lại nhãn ground-truth và rà soát chéo các case từ chối chuẩn. |
| 6 | `HL-015` ("Dạ, LogiX đã hoàn 55.000đ cho đơn O-112 ạ." — ledger ghi `40.000đ`) | PASS | FAIL | Người đúng | Judge chỉ đọc reply trôi chảy mà không thấy ledger (`FM-08`); **không** dùng LLM judge chấm số tiền/sự thật DB, chuyển sang code grader đối chiếu ledger. |
| 7 | `HL-016` (xin lỗi rất dài, lặp câu cảm ơn, nhưng báo sai `55.000đ` vs ledger `35.000đ`) | PASS | FAIL | Người đúng | Judge mắc *verbosity/politeness bias* (câu dài, xin lỗi nhiều → mặc định PASS); tách tiêu chí lịch sự khỏi tính đúng đắn số tiền và loại `judge_helpful` khỏi CI gate. |
| 8 | `HL-047` ("Ok bạn, đơn O-515 xử lý rồi nhé.") | PASS | FAIL | Người đúng | Vừa sai xưng hô (`"Ok bạn"`, `"nhé"`) vừa thiếu số tiền/kết quả cụ thể; sửa rubric yêu cầu nêu rõ trạng thái + số tiền/hành động tiếp theo. |

## Kết luận
- **Tiêu chí bị loại và lý do:** Loại **`helpful`** khỏi CI gate vì không đạt ngưỡng calibration (`κ = 0.375 < 0.6`, `Recall = 0.300 < 0.7`). Ma trận nhầm lẫn (`tp=9, fp=0, fn=21, tn=70`) cho thấy dù `Precision = 1.0`, judge bỏ sót **21/30** ca lỗi (`fn=21`), chủ yếu là 18 ca báo sai số tiền so với ledger (`sai tiền`) và 3 ca xưng hô thiếu thông tin (`sai xưng hô`). Do `Recall` quá thấp, tỉ lệ lỗi quan sát chỉ là `0.09` trong khi tỉ lệ lỗi thực sau hiệu chỉnh Rogan-Gladen lên tới `0.30` — dùng judge này làm gate sẽ để lọt 70% ca lỗi vào `main`. Tiêu chí `tone_ok` đạt FLOORS (`κ=0.757`, `P=0.857`, `R=0.800`) nên được giữ lại để theo dõi văn phong sau khi cập nhật rubric.
- **Rủi ro còn lại:** Judge chỉ được kiểm trên dữ liệu replay đã công khai (`100` mẫu/tiêu chí); cần thêm tập dữ liệu held-out mới do người gán nhãn độc lập để kiểm chứng lại sau khi sửa rubric, và mọi kiểm tra liên quan đến số tiền/ledger phải dùng **code grader** (như ở M3).
