# Báo cáo làm sạch dữ liệu và tạo feature

## 1. Mục tiêu

Từ dữ liệu điểm theo từng sinh viên và lớp học phần, tạo dữ liệu sạch cùng hai bảng feature để phân tích ở hai mức:

- **Course feature:** đặc trưng của từng môn/lớp học phần trong một học kỳ.
- **Student feature:** đặc trưng học tập của từng sinh viên trong một học kỳ.

Pipeline nằm trong `process_lop_analysis.py`. Dữ liệu gốc được giữ trong `data/raw/`; dữ liệu sạch và kết quả được đặt trong `data/processed/`.

## 2. Làm sạch dữ liệu (TV2)

### Giá trị thiếu không đồng đều

Dữ liệu đầu vào có 38.342 dòng. `KTTX2` thiếu 37.772 dòng, tương đương 98,51%; cột cơ cấu trọng số thiếu 35,83%; `KTTX1` và `KTTX (TB)` thiếu 14,68%; `CC` thiếu 11,91%; `Thi` thiếu 7,37%; điểm học phần thiếu 2,66%.

Không điền điểm thiếu bằng 0 hoặc trung bình. Cột điểm bị thiếu vẫn để trống; riêng dòng thiếu `Điểm HP (thang 10)` bị loại khỏi bảng điểm sạch vì không có nhãn tổng kết. Báo cáo chất lượng vẫn ghi số dòng/ô thiếu trên dữ liệu nguồn. Lần chạy hiện tại loại 1.019 dòng thiếu Điểm HP; không phát hiện dòng thiếu khóa, trùng khóa, trùng toàn bộ hoặc điểm ngoài miền. Cột `KTTX2` gốc được giữ. Có 863/877 lớp không có TX2; ở các lớp này, khi tính điểm quá trình, pipeline dùng TX1 cho lượt thứ hai. Không sửa đè các cột điểm gốc.

### Không có nhãn rõ “giữa kỳ” và “cuối kỳ”

Các cột thực tế là `KTTX1`, `KTTX2`, `KTTX (TB)`, `Thi` và `Điểm HP (thang 10)`. `Thi` là điểm thi cuối kỳ theo từ điển dữ liệu. Điểm quá trình được lấy từ `KTTX (TB)`; nếu thiếu, tính từ hai lượt TX1/TX2 sau khi áp dụng quy tắc TX2 theo lớp. Chỉ số `chenh_thi_qua_trinh` là `Thi - diem_qua_trinh`; đây là chênh lệch giữa điểm thi cuối kỳ và điểm quá trình, không phải điểm giữa kỳ đơn lẻ.

### Làm sạch khóa và kiểm tra miền điểm

Khóa ghi danh gồm năm học, học kỳ, mã môn, mã lớp học phần và mã sinh viên. Dòng trùng toàn bộ được bỏ trước; dòng có ít nhất một điểm ngoài 0–10 hoặc không chuyển được sang số bị loại; sau đó loại dòng thiếu khóa, thiếu Điểm HP và trùng khóa ghi danh. Báo cáo chất lượng lưu số dòng bị loại theo từng nguyên nhân và số ô thiếu nguồn.

Các ô chữ được bỏ khoảng trắng đầu/cuối; chuỗi rỗng được đổi thành thiếu. Giá trị thiếu còn lại được giữ nguyên trong CSV sạch và các phép tổng hợp bỏ qua thiếu theo hành vi của pandas.

## 3. Tạo course feature

**Mức một dòng:** năm học + học kỳ + loại lớp + mã môn + mã lớp học phần. Có ba loại không chồng lấn: `EP`, `He_thuong`, `Do_an_thuc_tap_khoa_luan`; nếu cờ đồ án/thực tập/khóa luận là Có thì ưu tiên nhóm này. Đồ án/thực tập/khóa luận được tách khỏi mặt bằng lớp thường. Kết quả giữ đủ 877 lớp, kể cả lớp không còn điểm HP hợp lệ; các thống kê điểm của lớp như vậy để thiếu.

Các feature gồm nhóm môn, số tín chỉ, sĩ số, số sinh viên có điểm thi/điểm HP, trung bình/trung vị/độ lệch chuẩn điểm HP, trung bình điểm quá trình và điểm thi, tỷ lệ thiếu điểm thi/điểm HP, cùng tỷ lệ HP từ 4,0, 4,5 và 8,5 trở lên. Pandas tính trung bình `Thi` trên các giá trị không null, nên người chưa có điểm thi không kéo trung bình xuống. Dữ liệu hiện có 35.518 điểm thi quan sát được và 2.824 null. Có 509 điểm thi bằng 0; từ điển nói điểm 0 có thể là vắng thi, nhưng không có cờ phân biệt nên không tự loại các số 0. Tỷ lệ đạt chỉ tính trên điểm HP quan sát được; điểm thiếu không bị tính là trượt.

Mặt bằng ngắn hạn được tính giữa lớp cùng môn, cùng kỳ, cùng loại lớp và cùng cơ cấu trọng số suy ra. Để tăng số mẫu, pipeline còn tạo mặt bằng gộp qua nhiều kỳ cho cùng môn + loại lớp + trọng số. Trước khi gộp, lấy điểm trung bình lớp trừ trung vị của các lớp song song cùng kỳ; nhờ vậy mô hình so mức lệch tương đối trong kỳ thay vì gộp trực tiếp điểm thô của nhiều năm. Chỉ dùng kỳ có ít nhất hai lớp song song để tạo phần lệch.

Trên phần lệch đã căn giữa theo kỳ, pipeline tính Z-score và robust Z-score (dùng median/MAD) khi có ít nhất 5 lớp đủ điều kiện ở tối thiểu 2 kỳ. `so_lop_cung_mon_trong_ky` và `so_lop_cung_mon_so_sanh` lần lượt cho biết số lớp trong kỳ và số lớp tham gia mặt bằng gộp; `trang_thai_mat_bang` nói rõ lý do nếu chưa thể so sánh. Mốc 5 là ngưỡng vận hành để tránh Z-score quá mong manh, không phải bảo đảm kết luận thống kê.

Trọng số trong dữ liệu là **trọng số suy ra từ điểm**, không phải trọng số chính thức. Bảng course feature vẫn giữ thống kê thô nếu không xác định được trọng số; trạng thái mặt bằng ghi rõ lý do không so sánh được.

## 4. Tạo student feature

`student_features.csv` là bảng TV4, một dòng cho mỗi sinh viên, gồm GPA gốc, Normalized_GPA, TCI, phân cấp và giải thích môn bị chiết khấu/điểm cần xem lại. Sinh viên chưa đủ 5 môn và 3 học kỳ vẫn có dòng nhưng TCI để thiếu và phân cấp là `INSUFFICIENT_HISTORY`.

Các chỉ số theo từng kỳ được dùng nội bộ để tính độ dốc tiến bộ; bảng bàn giao giữ một dòng tổng hợp cho mỗi sinh viên theo thiết kế gọn.

Không dùng thống kê cùng kỳ làm đầu vào dự đoán điểm của chính kỳ đó vì sẽ rò rỉ target.

## 5. Bảng dành cho mô hình dự đoán

`data/processed/prediction_dataset.csv` có 37.323 dòng với Điểm HP làm `target_diem_hp`. Feature chỉ sử dụng lịch sử có thứ tự trước kỳ hiện tại. Các dòng thiếu Điểm HP đã bị loại khỏi bảng điểm sạch và không thể tạo mẫu huấn luyện có target.

Feature lịch sử gồm GPA có trọng số tín chỉ của các kỳ trước, GPA kỳ gần nhất trước đó, số môn/số tín chỉ đã có điểm, tỷ lệ đạt trước đó, và lịch sử của cùng môn nếu sinh viên từng học môn đó. Mỗi feature chỉ tổng hợp các kỳ có thứ tự trước kỳ hiện tại. Điểm hiện tại chỉ xuất hiện trong cột target; không có CC, TX, Thi hay điểm HP hiện tại trong các cột feature. `Mã SV` chỉ để truy vết kết quả, không đưa làm predictor. TV3 cần chia train/test theo thời gian (kỳ cũ để train, kỳ mới để test), xử lý thiếu lịch sử trong pipeline và so với baseline GPA lịch sử.

Không ghép `Thoi_khoa_bieu.csv` vào dữ liệu điểm ở bước này: từ điển xác nhận `Mã HP`/`Mã LHP` không trùng với `Mã môn`/`Mã lớp học phần`, chưa có khóa đối chiếu đáng tin cậy.

## 6. Phát hiện lớp bất thường và hiệu chỉnh điểm (TV1/TV3)

Mặt bằng anomaly so sánh các lớp song song cùng môn, năm học, học kỳ và loại lớp. Dữ liệu không có ngành; hiện dùng cùng học phần và tách loại lớp. Khoa/khóa có trong dữ liệu nhưng không đủ thông tin để kết luận ngành của từng lớp. Lớp dưới 15 sinh viên và lớp có trên 30% ô điểm thành phần thiếu được gắn cờ; không tự loại.

`S1` là trị tuyệt đối của robust Z giữa điểm trung bình lớp và trung vị mặt bằng, chặn ở 6 rồi chia 6. `S2` là giá trị lớn hơn giữa `1 - SD_lớp / SD_mặt_bằng` và `(% điểm >= 8,5 - 0,6) / 0,4`, chặn về [0,1]. `S3` là `(r_mặt_bằng - r_lớp) / r_mặt_bằng`, chặn về [0,1], trong đó `r` là tương quan điểm HP với GPA lịch sử trước kỳ. Khi không có tương quan đủ dữ liệu hoặc tương quan trung vị không dương, S3 được đặt 0 và có cờ `S3_thieu_du_lieu`; không diễn giải giá trị này như đã đo được sự không khớp.

`Anomaly_Score = 0,4*S1 + 0,3*S2 + 0,3*S3`. So sánh cần ít nhất hai lớp song song; Isolation Forest chỉ chạy trên lớp có đủ mặt bằng, ít nhất 15 sinh viên, không thiếu trên 30% và không phải đồ án/thực tập/khóa luận. `nghi_van_kep` cho biết cả luật điểm và Isolation Forest cùng đánh dấu. Z hiệu chỉnh trên 3,5 gắn `HIGH_INFLATION`, dưới -3,5 gắn `UNUSUALLY_STEEP`; các lớp nghi vấn khác gắn `SUSPICIOUS_DISTRIBUTION`.

Ngưỡng 0,3 được kiểm tra trên profile mô phỏng có kiểm soát, không phải nhãn thật: 200 profile bình thường có 0% bị gắn cờ; profile bất thường vừa có 74% ở ngưỡng 0,3 và 0% ở 0,6; profile bất thường mạnh có 100% ở 0,3 và 99,5% ở 0,6. Đây chỉ là sanity check theo kịch bản giả lập, không phải độ chính xác phát hiện trên dữ liệu thật.

Chỉ lớp nghi vấn mới được chuẩn hóa Z: điểm cá nhân được chuyển thành Z trong lớp, rồi quy về trung bình/độ lệch chuẩn điểm của các lớp không nghi vấn cùng môn/kỳ/loại lớp. Nếu không đủ mặt bằng hoặc độ lệch chuẩn bằng 0 thì giữ điểm gốc và gắn cờ không chuẩn hóa được. Điểm chuẩn hóa bị chặn trong [0,10]. Linear Regression và Random Forest được huấn luyện trên lớp không nghi vấn; test theo năm học cuối. Lần chạy hiện tại kiểm tra 5.956 mẫu ở năm 2025: Random Forest RMSE 1,452, Linear Regression 1,485 và baseline GPA lịch sử 1,515. Khoảng `dự báo ± 1,96*RMSE` dùng để gắn `REVIEW_REQUIRED`; đây là khoảng thực dụng dựa trên RMSE holdout, không phải khoảng tin cậy thống kê bảo đảm.

`alpha = 1 - 0,8*Anomaly_Score`. Điểm gốc được giữ trong `adjusted_scores.csv`; điểm hiệu chỉnh và alpha là trường riêng để có thể truy vết.

## 7. TCI và giới hạn diễn giải (TV1/TV4)

GPA được quy đổi theo bảng điểm chữ do nhóm cung cấp: A+ [9,10] = 4,0; A [8,5,9) = 4,0; B+ [8,8,5) = 3,5; B [7,8) = 3,0; C+ [6,5,7) = 2,5; C [6,6,5) = 2,0; D+ [5,5,6) = 1,5; D [4,5,5,5) = 1,0; F <4,5 = 0. Đầu dưới đóng, đầu trên mở, riêng 10 thuộc A+. GPA danh nghĩa là trung bình điểm hệ 4 có trọng số tín chỉ. Normalized_GPA dùng điểm hệ 4 sau hiệu chỉnh và trọng số tín chỉ nhân alpha. Consistency là `clip(4*(1-SD/2), 0, 4)` trên điểm hệ 4. Progress là Normalized_GPA cộng độ dốc GPA theo thứ tự học kỳ, chặn [0,4]. `TCI = 0,6*Performance + 0,2*Consistency + 0,2*Progress`; chỉ tính khi có ít nhất 5 môn và 3 học kỳ. Phân cấp: Advanced từ 3,60; Proficient từ 3,20; Intermediate từ 2,50; dưới 2,50 là At-Risk.

`student_features.csv` giải thích từng sinh viên bằng GPA gốc, Normalized_GPA, TCI, số/mã môn bị chiết khấu và số/mã môn `REVIEW_REQUIRED`. `course_features.csv` gộp thống kê lớp và anomaly; `adjusted_scores.csv` có điểm chữ/GPA trước-sau theo từng học phần.

## 8. Công thức tham khảo

Chênh lệch điểm thi với điểm quá trình:

$$\Delta_i = \text{Thi}_i - \text{ĐiểmQuáTrình}_i$$

Chuẩn hóa Z-score cho giá trị $X$:

$$Z = \frac{X - \mu}{\sigma}$$

Quy về thang 10:

$$\text{ĐiểmChuẩnHóa}_{10} = \min(10, \max(0, 5 + 1.5Z))$$

Z-score của course feature và student feature được tính riêng theo năm học, học kỳ và loại lớp để so sánh các lớp/sinh viên cùng nhóm. Đây là chuẩn hóa phục vụ so sánh mô tả, không thay thế điểm chính thức.

## 9. Kết quả và giới hạn diễn giải

Pipeline chạy trên dữ liệu hiện tại tạo 37.323 dòng điểm sạch, 877 course feature, 5.067 student feature (một dòng/sinh viên) và 37.323 mẫu dự đoán có target xử lý nội bộ. Mô hình và anomaly là công cụ sàng lọc, không kết luận gian lận hay thay đổi điểm chính thức. Cần xác nhận bảng quy đổi điểm chữ, ngưỡng nghiệp vụ và khoảng dự báo với nhóm chuyên môn trước khi dùng trong quyết định học vụ.

Các cột mã sinh viên là dữ liệu cần bảo vệ; không đưa dữ liệu thật lên GitHub công khai. Bảng `prediction_dataset.csv` được thiết kế để tách target khỏi feature, nhưng TV3 vẫn cần kiểm tra danh sách cột đầu vào trước khi huấn luyện.
