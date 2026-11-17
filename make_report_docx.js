const fs = require('fs');
const { Document, Packer, Paragraph, TextRun, AlignmentType, HeadingLevel, ImageRun, Table, TableRow, TableCell, WidthType, BorderStyle } = require('docx');

const ROOT = __dirname;
const OUT = `${ROOT}/deliverables/NEU_Academic_Analytics_Technical_Report.docx`;
const LOGO = `${ROOT}/deliverables/assets/neu-logo.png`;

function paragraph(text, options = {}) {
  const children = typeof text === 'string'
    ? [new TextRun({ text, size: options.size || 22, bold: Boolean(options.bold), italic: Boolean(options.italic) })]
    : text;

  return new Paragraph({
    alignment: options.align || AlignmentType.LEFT,
    spacing: { before: options.before || 0, after: options.after || 80, line: 240 },
    indent: options.indent,
    children,
  });
}

function heading(title, level = HeadingLevel.HEADING_1) {
  return new Paragraph({
    heading: level,
    alignment: AlignmentType.LEFT,
    spacing: { before: 180, after: 100 },
    children: [new TextRun({ text: title, bold: true, size: 24 })],
  });
}

function bullet(text) {
  return new Paragraph({
    bullet: { level: 0 },
    indent: { left: 360 },
    spacing: { after: 60 },
    children: [new TextRun({ text, size: 22 })],
  });
}

function table(rows, widths) {
  const tableRows = rows.map((row, rowIndex) => new TableRow({
    children: row.map((cell, colIndex) => new TableCell({
      width: { size: widths[colIndex], type: WidthType.DXA },
      borders: {
        top: { style: BorderStyle.SINGLE, size: 1, color: 'D0D5D0', space: 0 },
        bottom: { style: BorderStyle.SINGLE, size: 1, color: 'D0D5D0', space: 0 },
        left: { style: BorderStyle.SINGLE, size: 1, color: 'D0D5D0', space: 0 },
        right: { style: BorderStyle.SINGLE, size: 1, color: 'D0D5D0', space: 0 },
      },
      children: [new Paragraph({
        alignment: rowIndex === 0 ? AlignmentType.CENTER : AlignmentType.LEFT,
        children: [new TextRun({ text: String(cell), bold: rowIndex === 0, size: 18 })],
        spacing: { before: 40, after: 40 },
      })],
    })),
  }));

  return [
    new Paragraph({ spacing: { after: 30 } }),
    new Table({
      width: { size: 9000, type: WidthType.DXA },
      rows: tableRows,
      layout: 'autofit',
    }),
    new Paragraph({ spacing: { after: 60 } }),
  ];
}

function imageRun(data, width, height) {
  return new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { before: 40, after: 60 },
    children: [new ImageRun({ data, type: 'png', transformation: { width, height } })],
  });
}

(async () => {
  const logoData = fs.existsSync(LOGO) ? fs.readFileSync(LOGO) : null;
  const children = [];

  children.push(paragraph('ĐẠI HỌC KINH TẾ QUỐC DÂN', { align: AlignmentType.CENTER, bold: true, size: 24, before: 140, after: 40 }));
  if (logoData) children.push(imageRun(logoData, 120, 120));
  children.push(paragraph('PHƯƠNG PHÁP TÍNH', { align: AlignmentType.CENTER, bold: true, size: 22, before: 20, after: 40 }));
  children.push(paragraph('CHỦ ĐỀ: XÂY DỰNG HỆ THỐNG PHÂN TÍCH ĐIỂM SỐ', { align: AlignmentType.CENTER, bold: true, size: 28, before: 20, after: 20 }));
  children.push(paragraph('VÀ ĐÁNH GIÁ NĂNG LỰC SINH VIÊN', { align: AlignmentType.CENTER, bold: true, size: 28, before: 0, after: 40 }));
  children.push(paragraph('NEU Academic Integrity & True Competency Analytics Platform', { align: AlignmentType.CENTER, italic: true, size: 19, after: 30 }));
  children.push(paragraph('Giảng viên hướng dẫn: TS. Nguyễn Ngọc Tuấn', { align: AlignmentType.CENTER, size: 19, after: 10 }));
  children.push(paragraph('Sinh viên thực hiện: Nhóm FIT Innovation', { align: AlignmentType.CENTER, size: 19, after: 200 }));
  children.push(paragraph('HÀ NỘI, 2026', { align: AlignmentType.CENTER, bold: true, size: 20, before: 20, after: 40 }));
  children.push(new Paragraph({ pageBreakBefore: true }));

  children.push(heading('LỜI CẢM ƠN'));
  children.push(paragraph('Trong quá trình thực hiện dự án, nhóm đã nhận được sự hướng dẫn, hỗ trợ và động viên từ giảng viên hướng dẫn và các bạn sinh viên. Những góp ý này giúp nhóm xác định rõ mục tiêu phân tích, kiểm tra dữ liệu và xây dựng hệ thống hỗ trợ đánh giá năng lực sinh viên theo logic khoa học.', { after: 60 }));
  children.push(paragraph('Nhóm xin chân thành cảm ơn giảng viên bộ môn và Đại học Kinh tế Quốc dân vì đã tạo môi trường học tập thuận lợi và khuyến khích nghiên cứu thực tế. Dù đã cố gắng hết sức, báo cáo vẫn có thể tồn tại một số hạn chế; chúng tôi rất mong nhận được phản hồi để cải thiện trong các bước tiếp theo.', { after: 80 }));

  children.push(heading('LỜI CAM ĐOAN'));
  children.push(paragraph('Nhóm cam đoan báo cáo này là kết quả nghiên cứu, phân tích và triển khai của nhóm. Mọi số liệu, biểu đồ và mô hình được xây dựng trên dữ liệu đã làm sạch trong thư mục dữ liệu xử lý, và không sao chép nguyên văn từ bất kỳ tài liệu nào khác mà không ghi rõ nguồn gốc.', { after: 80 }));

  children.push(heading('MỤC LỤC'));
  ['1. Dữ liệu và quy trình làm sạch', '2. Quy đổi điểm và GPA', '3. Phát hiện lớp bất thường', '4. TCI và phân loại sinh viên', '5. Kiến trúc hệ thống và mô hình ML', '6. Kết luận', '7. Phụ lục AI'].forEach((line) => children.push(paragraph(line, { after: 20 })));

  children.push(heading('CHƯƠNG 1. DỮ LIỆU VÀ QUY TRÌNH LÀM SẠCH'));
  children.push(paragraph('Nguồn dữ liệu đầu vào gồm nhiều dòng điểm học phần, thông tin lịch học và các trường dữ liệu khác. Sau khi xử lý, nhóm giữ lại dữ liệu sạch, loại các dòng thiếu khóa, thiếu điểm học phần và các hàng không hợp lệ. Mục tiêu là đảm bảo pipeline có thể chạy ổn định trên dữ liệu mới mà không bẻ luật đánh giá hoặc tự sửa điểm chính thức.', { after: 80 }));
  children.push(bullet('Chuẩn hóa khóa và loại bản ghi trùng.'));
  children.push(bullet('Loại điểm không hợp lệ hoặc ngoài khoảng [0, 10].'));
  children.push(bullet('Giữ lại những lớp đủ điều kiện, tách lớp thực hành/đồ án/thực tập khỏi lớp thường.'));
  children.push(bullet('Không gán điểm bằng 0 cho dữ liệu thiếu; dữ liệu thiếu được báo cáo riêng và không được coi là bằng chứng chính thức.'));
  children.push(paragraph('Quy trình làm sạch giúp cho các chỉ số lớp và chỉ số sinh viên được tính trên một nền dữ liệu nhất quán, dễ kiểm soát và dễ mở rộng khi dữ liệu mới được cập nhật.', { after: 80 }));

  children.push(heading('CHƯƠNG 2. QUY ĐỔI ĐIỂM VÀ GPA'));
  children.push(paragraph('Mỗi điểm học phần thang 10 được ánh xạ sang điểm chữ và điểm hệ 4 theo khoảng xác định. Quy ước đầu dưới đóng, đầu trên mở, riêng điểm 10 thuộc A+.', { after: 80 }));
  children.push(...table([
    ['Điểm thang 10', 'Điểm chữ', 'Điểm hệ 4'],
    ['9,0 <= x <= 10,0', 'A+', '4,0'],
    ['8,5 <= x < 9,0', 'A', '4,0'],
    ['8,0 <= x < 8,5', 'B+', '3,5'],
    ['7,0 <= x < 8,0', 'B', '3,0'],
    ['6,5 <= x < 7,0', 'C+', '2,5'],
    ['6,0 <= x < 6,5', 'C', '2,0'],
    ['5,5 <= x < 6,0', 'D+', '1,5'],
    ['4,5 <= x < 5,5', 'D', '1,0'],
    ['0 <= x < 4,5', 'F', '0,0'],
  ], [2800, 2600, 2600]));
  children.push(paragraph('Công thức GPA danh nghĩa: GPA_s = Σ(c_i × g_i) / Σ c_i. Trong đó c_i là tín chỉ và g_i là điểm hệ 4 của học phần i. Sau quá trình hiệu chỉnh, Normalized_GPA được tính theo trọng số tín chỉ đã điều chỉnh bằng hệ số alpha.', { after: 80 }));
  children.push(paragraph('Ví dụ: hai môn mỗi môn 3 tín chỉ, điểm 9,2 được A+ (4,0), điểm 8,2 được B+ (3,5). GPA danh nghĩa = (3×4,0 + 3×3,5)/(3+3) = 3,75.', { after: 80 }));

  children.push(heading('CHƯƠNG 3. PHÁT HIỆN LỚP BẤT THƯỜNG'));
  children.push(paragraph('Mỗi lớp được đánh giá bằng các thành phần S1, S2, S3. Ba thành phần này được chuẩn hóa về cùng khoảng [0,1], sau đó kết hợp bằng hệ số 0,4; 0,3; 0,3 để tạo ra Anomaly Score.', { after: 80 }));
  children.push(paragraph('Anomaly Score = 0,4 × S1 + 0,3 × S2 + 0,3 × S3.', { bold: true, size: 22, after: 70 }));
  children.push(bullet('S1: độ lệch trung bình của lớp so với peer.'));
  children.push(bullet('S2: mức độ quá đều hoặc có quá nhiều điểm A.'));
  children.push(bullet('S3: mức độ không tương ứng với xu hướng học tập của peer.'));
  children.push(paragraph('Các lớp có nhãn nghi vấn không được xem là kết luận về gian lận; chúng chỉ là tín hiệu để cán bộ chuyên môn kiểm tra lại dữ liệu đánh giá và cấu trúc kỳ học.', { after: 80 }));

  children.push(heading('CHƯƠNG 4. TCI VÀ PHÂN LOẠI SINH VIÊN'));
  children.push(paragraph('TCI là chỉ số tổng hợp phản ánh hiệu suất, tính ổn định và tiến bộ của sinh viên theo thời gian. Khi đủ điều kiện về lịch sử và số môn học, sinh viên được phân vào các nhóm Advanced, Proficient, Intermediate và At-Risk.', { after: 100 }));
  children.push(paragraph('TCI = 0,6 × Performance + 0,2 × Consistency + 0,2 × Progress.', { bold: true, size: 22, after: 60 }));
  children.push(...table([
    ['Cấp', 'Ngưỡng'],
    ['Advanced', 'TCI >= 3,60'],
    ['Proficient', '3,20 <= TCI < 3,60'],
    ['Intermediate', '2,50 <= TCI < 3,20'],
    ['At-Risk', 'TCI < 2,50'],
    ['INSUFFICIENT_HISTORY', 'Thiếu đủ 5 môn và 3 kỳ'],
  ], [3200, 5600]));

  children.push(heading('CHƯƠNG 5. KIẾN TRÚC HỆ THỐNG VÀ MÔ HÌNH ML'));
  children.push(paragraph('Hệ thống bao gồm các module chính: dữ liệu gốc, làm sạch, phân tích lớp, hiệu chỉnh điểm, mô hình dự báo và dashboard. Mỗi module có nhiệm vụ riêng và được nối bằng luồng dữ liệu rõ ràng để dễ kiểm soát và dễ mở rộng.', { after: 80 }));
  children.push(bullet('Dữ liệu gốc: file CSV điểm và TKB.'));
  children.push(bullet('Làm sạch: chuẩn hóa, xác thực, loại dữ liệu không hợp lệ và gắn nhãn lớp đủ điều kiện.'));
  children.push(bullet('Phân tích: tính Anomaly Score, GPA, TCI và phân cấp sinh viên.'));
  children.push(bullet('Dự báo: RandomForest/LinearRegression để đánh giá trung bình và điểm review.'));
  children.push(bullet('Dashboard/API: hiển thị KPI, phân phối và bảng dữ liệu.'));

  children.push(heading('CHƯƠNG 6. KẾT LUẬN'));
  children.push(paragraph('Hệ thống hiện tại cho thấy khả năng hỗ trợ phát hiện lớp bất thường, tổng hợp GPA và điểm thực chất của sinh viên, đồng thời giữ tính minh bạch và dễ kiểm tra. Điểm mạnh là pipeline không tự thay điểm, mà chỉ sinh tín hiệu và hỗ trợ chuyên gia kiểm tra lại.', { after: 80 }));
  children.push(paragraph('Để triển khai thực tế, nhóm cần tiếp tục đối chiếu quy chế điểm chính thức, kiểm tra dữ liệu thực tế và bổ sung cấu trúc crosswalk giữa TKB và bảng điểm trước khi đưa vào quyết định học vụ chính thức.', { after: 100 }));

  children.push(heading('PHỤ LỤC A. KÊ KHAI ỨNG DỤNG AI'));
  children.push(paragraph('Trong quá trình phát triển, nhóm sử dụng GitHub Copilot trong VS Code như công cụ hỗ trợ lập trình và rà soát mã. Công cụ này giúp đề xuất cấu trúc, sửa lỗi và chuẩn hóa báo cáo, nhưng không thay thế kiểm định của người dùng.', { after: 80 }));
  children.push(paragraph('Tuyên bố: AI chỉ đóng vai trò hỗ trợ lập trình và tài liệu; mọi quyết định học vụ, đánh giá và xác nhận tính đúng đắn thuộc về nhóm thực hiện và giảng viên hướng dẫn.', { after: 80 }));

  const doc = new Document({
    creator: 'FIT Innovation',
    title: 'NEU Academic Integrity & True Competency Analytics',
    description: 'Technical report with GPA and TCI analysis',
    sections: [{
      properties: {
        page: { margin: { top: 720, right: 720, bottom: 720, left: 720 } },
      },
      children,
    }],
  });

  const buffer = await Packer.toBuffer(doc);
  fs.mkdirSync(`${ROOT}/deliverables`, { recursive: true });
  fs.writeFileSync(OUT, buffer);
  console.log(`Generated ${OUT}`);
})();
