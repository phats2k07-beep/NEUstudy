# Kịch bản video demo (3–5 phút)

**Thời lượng mục tiêu:** 4 phút. Quay màn hình dashboard tại `http://127.0.0.1:8000`; dùng mã sinh viên đã ẩn danh hoặc crop khỏi video công khai.

| Thời gian | Hình ảnh / thao tác | Lời dẫn |
|---|---|---|
| 0:00–0:25 | Trang dashboard, KPI tổng quan | “Đây là prototype NEU Academic Integrity & True Competency Analytics. Hệ thống sàng lọc lớp học phần, trình bày điểm đã hiệu chỉnh và tổng hợp TCI; không tự kết luận vi phạm hay thay điểm chính thức.” |
| 0:25–0:55 | Chỉ các KPI lớp, sinh viên, lớp nghi vấn, TCI | “Dữ liệu được làm sạch theo khóa và miền điểm. Điểm thành phần thiếu được giữ thiếu; mẫu không đủ 5 môn và 3 kỳ được đánh dấu chưa đủ lịch sử.” |
| 0:55–1:35 | Đồ thị GPA danh nghĩa/Normalized GPA, phân loại TCI | “GPA mỗi môn được quy đổi theo bảng điểm chữ: từ 9 điểm là 4,0; 8,5 là A 4,0; 8 là B+ 3,5; 7 là B 3,0; 6,5 là C+ 2,5; 6 là C 2,0; 5,5 là D+ 1,5; 4,5 là D 1,0; dưới 4,5 là 0. Sau đó GPA được tính có trọng số tín chỉ.” |
| 1:35–2:20 | Bảng xếp hạng lớp; lọc lớp nghi vấn; mở/đọc score, nhãn, cờ Isolation Forest | “Lớp được so với lớp song song cùng môn, kỳ và loại lớp. Anomaly Score gồm độ lệch trung vị/MAD, độ lệch chuẩn/tỷ lệ A và tương quan với GPA lịch sử. Isolation Forest là kiểm tra độc lập. Nhãn chỉ đề xuất rà soát.” |
| 2:20–2:55 | Tải CSV lớp hoặc adjusted scores | “Với lớp nghi vấn, hệ thống chuẩn hóa Z nếu có peer và độ lệch chuẩn hợp lệ. Điểm gốc vẫn giữ nguyên; bảng điều chỉnh có alpha, khoảng tham chiếu và REVIEW_REQUIRED.” |
| 2:55–3:25 | Tìm mã SV giả lập/ẩn danh và mở bảng sinh viên | “Hồ sơ giải thích GPA gốc, Normalized GPA, TCI, môn bị chiết khấu và môn cần review. Chỉ sinh viên đủ tối thiểu 5 môn và 3 kỳ mới có TCI.” |
| 3:25–3:45 | Thẻ thời khóa biểu | “TKB được thống kê độc lập. Mã HP/LHP không có khóa đối chiếu chắc chắn với mã trong bảng điểm, nên prototype không ghép hai nguồn một cách suy đoán.” |
| 3:45–4:05 | Swagger `/docs`, endpoint analyze hoặc quay lại dashboard | “API nhận CSV, chạy pipeline trong thư mục tạm và trả các endpoint thống kê, lớp, sinh viên cùng file export. Đây là bản demo nội bộ; triển khai thật cần phân quyền và audit.” |

## Chuẩn bị quay

1. Chạy `python process_lop_analysis.py`, `python generate_report.py`, rồi `uvicorn platform_api:app --host 127.0.0.1 --port 8000`.
2. Mở dashboard và chuẩn bị một bản sao CSV; không upload/lộ danh tính sinh viên trong bản ghi công khai.
3. Nếu quay upload, dùng bản sao dữ liệu và đợi pipeline chạy xong; không dùng dữ liệu demo tự chế như bằng chứng độ chính xác.
4. Hiển thị cảnh báo “prototype / human review required” ở đoạn anomaly và remediation.
