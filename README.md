# NEU Academic Integrity & True Competency Analytics

Prototype phân tích kết quả học tập để sàng lọc lớp có phân phối điểm đáng rà soát, thử hiệu chỉnh minh bạch và tổng hợp TCI sinh viên. Đây là công cụ hỗ trợ phân tích, không kết luận gian lận và không tự thay thế điểm chính thức.

## Chạy nhanh

Tại thư mục dự án:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python process_lop_analysis.py
uvicorn platform_api:app --host 127.0.0.1 --port 8000
```

Mở dashboard tại `http://127.0.0.1:8000`; tài liệu API tại `http://127.0.0.1:8000/docs`.

Demo chạy local (sau khi khởi động API): [Dashboard](http://127.0.0.1:8000/) · [Swagger API](http://127.0.0.1:8000/docs) · [Health check](http://127.0.0.1:8000/api/health). Đây là link trên máy đang chạy ứng dụng, không phải deployment public.

## Nạp dữ liệu qua API

`POST /api/analyze` nhận `multipart/form-data` với trường `file` là CSV. File cần có tối thiểu các cột khóa và `Điểm HP (thang 10)`; pipeline kiểm tra các cột còn lại khi xử lý. Upload giới hạn 50 MB. Kết quả upload được tạo trong thư mục tạm, không ghi đè dữ liệu nguồn hay các CSV gốc trong `data/processed`.

Ví dụ:

```bash
curl -sS -F "file=@data/raw/Du_lieu.csv" http://127.0.0.1:8000/api/analyze
curl http://127.0.0.1:8000/api/summary
curl "http://127.0.0.1:8000/api/classes?flagged_only=true&page_size=20"
curl "http://127.0.0.1:8000/api/students?level=Advanced"
```

Phản hồi `POST /api/analyze` có `results.summary`, `results.classes`, `results.students` để truy vấn tiếp sau khi xử lý. Nhãn sàng lọc lớp nằm ở `Nhan_bat_thuong` trong `/api/classes`; phân loại TCI nằm ở `Phan_cap` trong `/api/students`. API có `GET /api/health`, `/api/summary`, `/api/classes`, `/api/students`, `/api/timetable/summary`, và `/api/exports/{filename}`. Swagger UI nằm ở `/docs`.

Mã nguồn và bộ dữ liệu có mã sinh viên đã mã hóa được lưu tại [GitHub](https://github.com/phats2k07-beep/NEUstudy). Dashboard/API chạy local; chưa có URL deployment public. PDF và video demo là deliverable riêng, giữ local và không đưa lên repository.

## Video demo

Tạo video 3 phút 30 giây từ dữ liệu đã xử lý:

```bash
python make_demo_video.py
```

Cần cài `ffmpeg` trên hệ điều hành. Video được lưu tại `deliverables/NEU_Academic_Analytics_Demo.mp4` và bị loại khỏi Git; ví dụ sinh viên trong video dùng nhãn ẩn danh.

## Đầu ra chính

| File | Nội dung |
|---|---|
| `data/processed/du_lieu_clean.csv` | Bảng điểm mức sinh viên-môn sau các quy tắc làm sạch. |
| `data/processed/course_features.csv` | Một dòng mỗi lớp: thống kê lớp, điểm vênh `Thi - KTTX (TB)` trên cặp đủ dữ liệu, các thành phần anomaly, nhãn và hạng. |
| `data/processed/adjusted_scores.csv` | Điểm gốc, điểm chữ và GPA hệ 4 gốc/điều chỉnh, `Adjusted_Score`, alpha và cờ review theo sinh viên-môn. |
| `data/processed/student_features.csv` | Một dòng mỗi sinh viên: GPA gốc, Normalized GPA, TCI, phân cấp và giải thích. |
| `data/processed/bao_cao_clean_data.csv` | Báo cáo chất lượng và metric kiểm định mô hình theo thời gian. |
| `deliverables/NEU_Academic_Analytics_Technical_Report.pdf` | Báo cáo kỹ thuật hiện có tại máy chạy dự án; không được commit lên GitHub. |

## Phương pháp và giới hạn dữ liệu

### Quy đổi điểm thang 10 sang GPA hệ 4

| Điểm thang 10 | Điểm chữ | Điểm hệ 4 |
|---|---:|---:|
| 9,0 đến 10,0 | A+ | 4,0 |
| 8,5 đến dưới 9,0 | A | 4,0 |
| 8,0 đến dưới 8,5 | B+ | 3,5 |
| 7,0 đến dưới 8,0 | B | 3,0 |
| 6,5 đến dưới 7,0 | C+ | 2,5 |
| 6,0 đến dưới 6,5 | C | 2,0 |
| 5,5 đến dưới 6,0 | D+ | 1,5 |
| 4,5 đến dưới 5,5 | D | 1,0 |
| Dưới 4,5 | F | 0,0 |

Đầu dưới mỗi khoảng được lấy, đầu trên không lấy; riêng 10 thuộc A+. GPA sinh viên là trung bình có trọng số tín chỉ trên điểm hệ 4. Điểm chữ và điểm hệ 4 của từng môn nằm trong `adjusted_scores.csv`; GPA là số tổng hợp, không có một điểm chữ duy nhất.

- Điểm trong [0,10]; điểm thiếu thành phần được giữ trống, không thay bằng 0. Dòng thiếu Điểm HP không có target để huấn luyện nên không vào bảng sạch có nhãn; báo cáo giữ số lượng thiếu.
- Lớp bị loại khi sĩ số ghi nhận không nhất quán/không bằng số mã sinh viên duy nhất. Lớp nhỏ nhưng sĩ số khớp không bị loại; gắn cờ mẫu nhỏ. Đồ án/thực tập/khóa luận tách khỏi mặt bằng lớp thường.
- Anomaly Score là `0.4*S1 + 0.3*S2 + 0.3*S3`, mỗi thành phần chuẩn hóa về [0,1]. Chỉ chấm lớp đủ kích thước/mức đầy đủ dữ liệu và có peer; Isolation Forest là kiểm tra bổ sung. Nhãn chỉ là danh sách review, không phải kết luận sai phạm.
- Điểm vênh chỉ tính `Thi - KTTX (TB)` khi có cả hai cột thật; không thay KTTX(TB) thiếu bằng TX1 cho phép tính vênh.
- Mô hình train trên năm trước, test ở năm học cuối có nhãn; baseline prior GPA được báo kèm. Khoảng `±1.96×RMSE` là dải sàng lọc thực dụng, không phải prediction interval có coverage được bảo đảm.
- Bảng điểm không có ngành. TKB dùng mã HP/LHP khác mã môn/lớp học phần, nên dashboard chỉ hiển thị thống kê TKB độc lập, không ghép giả.
- Quy đổi GPA dùng đúng bảng điểm chữ ở trên. Nhóm cần đối chiếu lần cuối với quy chế đào tạo chính thức trước khi áp dụng vào quyết định học vụ.
- Dashboard mặc định chỉ bind `127.0.0.1`. Trước khi triển khai mạng, cần xác thực, phân quyền, audit log, mã hóa và chính sách lưu trữ dữ liệu sinh viên.
- Phụ lục PDF kê khai GitHub Copilot trong VS Code đã hỗ trợ phát triển. Phiên làm việc không cung cấp tên backend model; nhóm cần bổ sung tên model hiển thị trong VS Code nếu thể lệ yêu cầu trước khi nộp chính thức.

## Kiểm tra

```bash
python -m unittest discover -s tests -v
```

