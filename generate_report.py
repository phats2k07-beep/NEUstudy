"""Generate a compact academic PDF report mimicking a technical course report."""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data" / "processed"
DELIVERABLES = ROOT / "deliverables"
FIGURES = DELIVERABLES / "figures"
PDF_PATH = DELIVERABLES / "NEU_Academic_Analytics_Technical_Report.pdf"
LOGO_PATH = DELIVERABLES / "assets" / "neu-logo.png"


def register_font():
    candidates = [
        Path("/usr/share/fonts/noto/NotoSerif-Regular.ttf"),
        Path("/usr/share/fonts/truetype/liberation2/LiberationSerif-Regular.ttf"),
        Path("/usr/share/fonts/TTF/DejaVuSerif.ttf"),
    ]
    bold_candidates = [
        Path("/usr/share/fonts/noto/NotoSerif-Bold.ttf"),
        Path("/usr/share/fonts/truetype/liberation2/LiberationSerif-Bold.ttf"),
        Path("/usr/share/fonts/TTF/DejaVuSerif-Bold.ttf"),
    ]
    regular = next((p for p in candidates if p.exists()), None)
    bold = next((p for p in bold_candidates if p.exists()), None)
    if regular and bold:
        pdfmetrics.registerFont(TTFont("ReportSerif", str(regular)))
        pdfmetrics.registerFont(TTFont("ReportSerif-Bold", str(bold)))
        return "ReportSerif", "ReportSerif-Bold"
    return "Helvetica", "Helvetica-Bold"


FONT, FONT_BOLD = register_font()


def make_charts():
    FIGURES.mkdir(parents=True, exist_ok=True)
    students = pd.read_csv(DATA / "student_features.csv")
    classes = pd.read_csv(DATA / "course_features.csv")

    fig, ax = plt.subplots(figsize=(8.2, 3.3))
    p = np.linspace(0, 4, 9)
    ax.hist(students["GPA_goc"].dropna(), bins=p, color="#C1C8C2", alpha=0.8, label="GPA gốc")
    ax.hist(students["Normalized_GPA"].dropna(), bins=p, color="#5E7F74", alpha=0.7, label="Normalized GPA")
    ax.set_title("Phân bố GPA", fontsize=10, fontweight="bold", loc="left")
    ax.set_xlabel("GPA hệ 4")
    ax.set_ylabel("Số sinh viên")
    ax.grid(axis="y", linestyle="-", alpha=0.2)
    ax.legend(frameon=False, fontsize=8)
    fig.tight_layout()
    chart1 = FIGURES / "gpa_distribution.png"
    fig.savefig(chart1, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(fig)

    labels = ["Advanced", "Proficient", "Intermediate", "At-Risk", "INSUFFICIENT_HISTORY"]
    counts = students["Phan_cap"].value_counts().reindex(labels, fill_value=0)
    fig, ax = plt.subplots(figsize=(8, 2.5))
    colors_bar = ["#1F4D45", "#6B8F83", "#CDBF63", "#BE704F", "#D7D9D7"]
    ax.bar(labels, counts.values, color=colors_bar, width=0.7)
    ax.set_title("Phân bố TCI", fontsize=10, fontweight="bold", loc="left")
    ax.set_ylabel("Số sinh viên")
    ax.grid(axis="y", linestyle="-", alpha=0.15)
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    chart2 = FIGURES / "tci_distribution.png"
    fig.savefig(chart2, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(fig)

    # anomaly summary bar
    levels = ["NOT_FLAGGED", "SUSPICIOUS_DISTRIBUTION", "UNUSUALLY_STEEP", "HIGH_INFLATION"]
    counts_cls = classes["Nhan_bat_thuong"].value_counts().reindex(levels, fill_value=0)
    fig, ax = plt.subplots(figsize=(8, 2.4))
    ax.bar(levels, counts_cls.values, color=["#B9C7BF", "#8AA39B", "#D3A96D", "#CF7A5E"])
    ax.set_title("Kết quả sàng lọc lớp", fontsize=10, fontweight="bold", loc="left")
    ax.set_ylabel("Số lớp")
    ax.grid(axis="y", linestyle="-", alpha=0.15)
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    chart3 = FIGURES / "class_flags.png"
    fig.savefig(chart3, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(fig)

    return chart1, chart2, chart3


def make_system_diagram():
    FIGURES.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(10, 3.5))
    ax.axis("off")
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 4)

    boxes = [
        (0.3, 2.2, 1.7, 0.9, "Dữ liệu gốc", "CSV điểm / TKB"),
        (2.3, 2.2, 1.7, 0.9, "Làm sạch", "điểm · khóa · si số"),
        (4.5, 2.2, 1.8, 0.9, "Analytics", "S1/S2/S3 + TCI"),
        (6.8, 2.2, 1.8, 0.9, "Đầu ra", "CSV báo cáo"),
        (8.8, 2.2, 1.0, 0.9, "Dashboard", "Web/API"),
        (4.5, 0.5, 2.0, 0.9, "Human review", "kiểm tra chuyên môn"),
    ]
    for x, y, w, h, title, text in boxes:
        ax.add_patch(plt.Rectangle((x, y), w, h, facecolor="#F3F4F1", edgecolor="#666666", linewidth=1.0))
        ax.text(x + w / 2, y + h * 0.64, title, ha="center", va="center", fontsize=8.5, fontweight="bold", color="#1F2A2A")
        ax.text(x + w / 2, y + h * 0.28, text, ha="center", va="center", fontsize=7, color="#4F5E5B")

    arrows = [
        ((2.0, 2.65), (2.3, 2.65)),
        ((4.0, 2.65), (4.5, 2.65)),
        ((6.3, 2.65), (6.8, 2.65)),
        ((8.6, 2.65), (8.8, 2.65)),
        ((5.5, 2.2), (5.5, 1.4)),
    ]
    for a, b in arrows:
        ax.annotate("", xy=b, xytext=a, arrowprops={"arrowstyle": "-|>", "lw": 1.2, "color": "#657D73"})

    fig.tight_layout()
    path = FIGURES / "system_architecture.png"
    fig.savefig(path, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return path


def load_stats():
    report = pd.read_csv(DATA / "bao_cao_clean_data.csv")
    classes = pd.read_csv(DATA / "course_features.csv")
    students = pd.read_csv(DATA / "student_features.csv")
    adjusted = pd.read_csv(DATA / "adjusted_scores.csv")
    raw = pd.read_csv(ROOT / "data" / "raw" / "Du_lieu.csv")
    return {
        "input_rows": len(raw),
        "clean_rows": len(pd.read_csv(DATA / "du_lieu_clean.csv")),
        "classes": len(classes),
        "students": len(students),
        "tcis": int(students["TCI"].notna().sum()),
        "review_count": int(adjusted["REVIEW_REQUIRED"].fillna(False).sum()),
        "flagged_classes": int(classes["nghi_van"].fillna(False).sum()),
        "model_name": "RandomForest",
    }


def P(text, style):
    return Paragraph(text, style)


def build_pdf():
    DELIVERABLES.mkdir(parents=True, exist_ok=True)
    if PDF_PATH.exists():
        PDF_PATH.unlink()
    chart1, chart2, chart3 = make_charts()
    system_path = make_system_diagram()
    stats = load_stats()

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="CoverMain", fontName=FONT_BOLD, fontSize=22, leading=28, alignment=TA_CENTER, textColor="#1B2B2A"))
    styles.add(ParagraphStyle(name="CoverSub", fontName=FONT, fontSize=11, leading=16, alignment=TA_CENTER, textColor="#4A5E58"))
    styles.add(ParagraphStyle(name="H1", fontName=FONT_BOLD, fontSize=16, leading=20, textColor="#1B2B2A", spaceBefore=10, spaceAfter=8))
    styles.add(ParagraphStyle(name="H2", fontName=FONT_BOLD, fontSize=10.5, leading=14, textColor="#1B2B2A", spaceBefore=8, spaceAfter=4))
    styles.add(ParagraphStyle(name="Body", fontName=FONT, fontSize=8.5, leading=13, textColor="#212B2A", spaceAfter=5))
    styles.add(ParagraphStyle(name="Small", fontName=FONT, fontSize=7, leading=10, textColor="#4A5E58", spaceAfter=4))
    styles.add(ParagraphStyle(name="Callout", fontName=FONT_BOLD, fontSize=8.7, leading=12, textColor="#1B2B2A", backColor="#F2F5F1", borderColor="#D7DCD5", borderWidth=0.7, borderPadding=8, spaceBefore=6, spaceAfter=8))
    styles.add(ParagraphStyle(name="TableHead", fontName=FONT_BOLD, fontSize=7, leading=9, textColor="#1B2B2A", backColor="#F0F3F0"))
    styles.add(ParagraphStyle(name="TableCell", fontName=FONT, fontSize=7, leading=9, textColor="#1B2B2A"))

    story = []

    def body(text):
        story.append(P(text, styles["Body"]))

    def h1(text):
        story.append(P(text, styles["H1"]))

    def h2(text):
        story.append(P(text, styles["H2"]))

    def add_table(headers, rows, widths):
        data = [[P(str(v), styles["TableHead"]) for v in headers]]
        data += [[P(str(v), styles["TableCell"]) for v in row] for row in rows]
        table = Table(data, colWidths=widths, repeatRows=1)
        table.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D9DEDA")),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F0F3F0")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(table)
        story.append(Spacer(1, 6))

    # Cover page
    story.append(Spacer(1, 8 * mm))
    if LOGO_PATH.exists():
        story.append(Image(str(LOGO_PATH), width=26 * mm, height=26 * mm, hAlign="CENTER"))
    story.append(Spacer(1, 2 * mm))
    story.append(P("FIT Chupby", styles["CoverMain"]))
    story.append(Spacer(1, 2 * mm))
    story.append(P("BÁO CÁO GIẢI PHÁP KỸ THUẬT", styles["CoverMain"]))
    story.append(Spacer(1, 2 * mm))
    story.append(P("HỆ THỐNG PHÂN TÍCH ĐIỂM SỐ VÀ ĐÁNH GIÁ NĂNG LỰC SINH VIÊN", styles["CoverSub"]))
    story.append(Spacer(1, 4 * mm))
    story.append(P("Academic Integrity & True Competency Analytics Platform", styles["CoverSub"]))
    story.append(Spacer(1, 4 * mm))
    story.append(P("HÀ NỘI, 2026", styles["CoverSub"]))
    story.append(PageBreak())

    story.append(PageBreak())

    h1("MỤC LỤC")
    add_table(["Chương", "Nội dung", "Trang"], [
        ["1", "Dữ liệu và quy trình làm sạch", "3"],
        ["2", "Quy đổi điểm và GPA", "4"],
        ["3", "Phát hiện lớp bất thường", "5"],
        ["4", "TCI và phân loại sinh viên", "7"],
        ["5", "Kiến trúc hệ thống và mô hình ML", "8"],
        ["6", "Kết luận", "9"],
    ], [20 * mm, 95 * mm, 20 * mm])
    story.append(PageBreak())

    # Chapter 1
    h1("CHƯƠNG 1. DỮ LIỆU VÀ QUY TRÌNH LÀM SẠCH")
    body(f"Nguồn dữ liệu ban đầu có {stats['input_rows']:,} dòng điểm. Sau khi loại các dòng thiếu khóa, thiếu điểm học phần, và các trường không hợp lệ, dữ liệu sạch còn lại {stats['clean_rows']:,} dòng. Số lớp được giữ lại trong dữ liệu Lớp/HP là {stats['classes']:,}; số sinh viên được đánh giá là {stats['students']:,}.")
    body("Quy trình làm sạch bao gồm: (i) chuẩn hóa khóa dữ liệu, (ii) loại dữ liệu thiếu hoặc không hợp lệ, (iii) kiểm tra trùng lặp, (iv) xác định lớp đủ điều kiện, (v) tính toán các thống kê lớp và giá trị vênh theo từng học phần. Kết quả là một bảng qui trình rõ ràng, dễ kiểm tra và dễ mở rộng khi dữ liệu mới được bổ sung.")
    body("Bộ dữ liệu không dựa vào TKB để khớp giả với điểm số, mà tính toán các chỉ số lớp độc lập trên cùng nhóm môn/kỳ. Điều này giúp giảm độ nhiễu khi so sánh giữa các lớp cùng nhánh học tập và cùng cấu trúc đánh giá.")
    body("Trong thực tế, các lỗi thường xuất hiện ở bốn dạng chính: giá trị thiếu do nhập liệu không đồng nhất, khóa trùng do sinh viên có nhiều lần đăng ký, mức điểm không hợp lệ ngoài thang [0,10], và số lượng sinh viên trong lớp không khớp với số mã sinh viên duy nhất. Các lỗi này không thể bỏ qua hoàn toàn nếu muốn đánh giá đúng và đảm bảo tính dẫn chứng trong phân tích. Cấu trúc pipeline vì vậy phải sớm tách dữ liệu sạch khỏi dữ liệu gốc để thực hiện các bước tiếp theo trên một nền vững chắc.")
    body("Việc tách riêng lớp thực hành, thực tập và đồ án tránh việc đánh đồng các bộ môn có cấu trúc đánh giá khác nhau. Nền dữ liệu do đó không bị “cùng một luật” với các lớp lý thuyết, từ đó giúp giảm tỷ lệ false positive khi sàng lọc các lớp bất thường. Điều này là quan trọng vì nhiều trường hợp lớp có điểm cao tập trung nhưng không hẳn là dấu hiệu vi phạm mà có thể là cấu trúc đánh giá riêng của môn học.")
    add_table(["Bước", "Xử lý"], [
        ["1", "Chuẩn hóa khóa và loại dòng trùng"],
        ["2", "Loại điểm không hợp lệ / thiếu điểm HP"],
        ["3", "Kiểm tra sĩ số và đồng nhất lớp"],
        ["4", "Tách lớp thực hành, thực tập, đồ án"],
        ["5", "Sinh ra đặc trưng lớp và đặc trưng sinh viên"],
    ], [20 * mm, 120 * mm])
    story.append(Image(str(chart1), width=150 * mm, height=50 * mm, hAlign="CENTER"))
    story.append(P("Hình 1. Phân bố GPA gốc và GPA chuẩn hóa.", styles["Small"]))
    story.append(PageBreak())

    h2("Đánh giá tổng hợp và ứng dụng thực tế")
    body("Trong bối cảnh quản lý đào tạo, dữ liệu điểm và lịch sử học tập của sinh viên thường có độ nhiễu cao do nhiều nguyên nhân: thay đổi cấu trúc đánh giá, điểm thành phần chưa đồng nhất giữa các lớp, hoặc khác biệt về quy mô lớp học. Vì vậy, hệ thống cần được xây dựng như một bộ hỗ trợ chuyên môn, không phải công cụ thay thế chuyên gia. Nền tảng này cho phép kiểm tra nhanh các lớp có tín hiệu lệch so với peer và giúp người phụ trách tập trung vào các trường hợp thực sự đáng xem lại.")
    body("Về mặt kỹ thuật, giải pháp kết hợp ba lớp thành phần: làm sạch và chuẩn hóa dữ liệu, phát hiện bất thường dựa trên tín hiệu thống kê và phát hiện kết hợp học máy, và tính toán chỉ số TCI để đánh giá năng lực thực chất. Sự kết hợp này tạo ra một đường đi minh bạch: dữ liệu gốc nhất quán -> lớp bất thường gắn nhãn -> điểm được hiệu chỉnh theo cơ chế cho phép truy vết -> sinh viên được phân loại theo năng lực. Đây là một mô hình phù hợp với dữ liệu học tập chu kỳ, nơi quá trình đánh giá cần tính đến lịch sử và sự ổn định trong thời gian.")
    body("Một điểm cần lưu ý là không thể căn cứ chỉ vào một chỉ số duy nhất để kết luận cuối cùng. Khi hệ thống báo lớp bất thường hoặc sinh viên có TCI thấp, người ra quyết định vẫn cần đối chiếu đề thi, rubric, bài tập và bối cảnh giảng dạy để xác định nguyên nhân thực sự. Nếu không có bước kiểm tra chuyên môn, mọi dấu hiệu thống kê sẽ chỉ là tín hiệu khởi đầu chứ không phải kết luận học vụ.")
    story.append(PageBreak())

    # Chapter 2
    h1("CHƯƠNG 2. QUY ĐỔI ĐIỂM VÀ GPA")
    body("Mỗi điểm thang 10 được quy đổi thành điểm chữ và điểm hệ 4 theo khoảng cụ thể. Đầu dưới đóng, đầu trên mở, riêng điểm 10 thuộc A+. Quy tắc này đảm bảo mỗi điểm chỉ thuộc đúng một khoảng và không có chồng lấn giữa các mức.")
    add_table(["Điểm thang 10", "Điểm chữ", "Điểm hệ 4"], [
        ["9,0 <= x <= 10,0", "A+", "4,0"],
        ["8,5 <= x < 9,0", "A", "4,0"],
        ["8,0 <= x < 8,5", "B+", "3,5"],
        ["7,0 <= x < 8,0", "B", "3,0"],
        ["6,5 <= x < 7,0", "C+", "2,5"],
        ["6,0 <= x < 6,5", "C", "2,0"],
        ["5,5 <= x < 6,0", "D+", "1,5"],
        ["4,5 <= x < 5,5", "D", "1,0"],
        ["0 <= x < 4,5", "F", "0,0"],
    ], [50 * mm, 32 * mm, 30 * mm])
    story.append(P("GPA_s = sum(c_i * g_i) / sum(c_i)", styles["Callout"]))
    body("Trong đó c_i là tín chỉ của học phần i và g_i là điểm hệ 4 tương ứng. Điểm chữ và hệ số tín chỉ được lưu riêng ở bảng chi tiết từng học phần, nên không có “một điểm chữ cho cả sinh viên” mà chỉ có điểm từng môn và GPA tổng hợp sau đó.")
    body("Một điểm quan trọng cần nhấn mạnh là quy đổi điểm thang 10 không được thực hiện bằng phép nhân tuyến tính 0,4. Quy trình đúng thực chất là ánh xạ từng khoảng điểm vào mức chữ tương ứng, rồi lấy giá trị hệ 4 tương ứng. Điều này làm cho kết quả GPA rõ ràng theo quy chế học vụ, đồng thời tránh sai lệch do việc gán một hệ số cố định cho toàn bộ dải điểm.")
    body("Sau khi tính toán variance và độ bất thường của lớp, hệ số alpha được áp dụng để giảm trọng số của lớp kê khai nghi vấn. Khi lớp bình thường thì alpha = 1; nếu lớp có mức bất thường cao, alpha giảm theo hàm 1 - 0.8 * AnomalyScore. Từ đó ta xác định Normalized_GPA theo một cấu trúc có tính minh bạch và dễ kiểm tra.")
    body("Về mặt triển khai, GPA gốc phản ánh thành tích học tập danh nghĩa, còn GPA sau hiệu chỉnh phản ánh nền thực chất khi xem xét các lớp có dấu hiệu lệch so với peer. Mức chênh lệch giữa hai chỉ số cho phép nhìn thấy rõ các trường hợp điểm cao quanh ngưỡng hoặc quá đồng đều có thể cần rà soát thêm ở cấp độ chuyên môn, nhưng không được coi là bằng chứng kết luận cuối cùng.")
    story.append(PageBreak())

    # Chapter 3
    h1("CHƯƠNG 3. PHÁT HIỆN LỚP BẤT THƯỜNG")
    body("Mỗi lớp được phân tích thông qua các thành phần S1, S2, S3: trung bình lệch, mức quá đều/độ lệch cao, và mức không tương ứng với xu hướng peer. Ba thành phần này được quy đổi về cùng thang [0,1] rồi kết hợp bằng trọng số 0.4, 0.3, 0.3 để có AnomalyScore.")
    story.append(P("AnomalyScore = 0.4*S1 + 0.3*S2 + 0.3*S3", styles["Callout"]))
    body("Trong thực thi, S1 đo mức độ lệch thống kê của lớp so với giá trị median của các lớp cùng dạng. S2 đánh giá mức độ “quá đều” hoặc tỷ lệ điểm A vượt ngưỡng bình thường. S3 làm rõ sự không khớp của lớp với hướng tăng/giảm điểm của sinh viên trong cùng tập peer. Các thành phần này không tự thay thế cho quy tắc đánh giá cộng đồng, nhưng khi đồng thời cùng lớn, chúng cho thấy rằng mẫu điểm của lớp đang lệch khỏi trạng thái kỳ vọng.")
    body("Các lớp được đánh dấu nếu có dấu hiệu khác biệt mạnh so với peer cùng môn và cùng giai đoạn. Kết quả nhãn không phải kết luận học vụ, mà là tín hiệu để chuyên gia kiểm tra lại dữ liệu, cấu trúc đánh giá, hoặc tính năng của kỳ học. Hệ thống không thay thế người đánh giá; nó chỉ giúp rút ngắn thời gian khởi đầu  cho quá trình rà soát. ")
    story.append(Image(str(chart3), width=150 * mm, height=42 * mm, hAlign="CENTER"))
    story.append(P("Hình 2. Số lớp theo nhãn bất thường.", styles["Small"]))
    story.append(PageBreak())

    # Chapter 4
    h1("CHƯƠNG 4. TCI VÀ PHÂN LOẠI SINH VIÊN")
    body("TCI là chỉ số kết hợp giữa hiệu suất học tập, tính ổn định và tiến bộ theo thời gian. Năng lực học tập được chuẩn hóa bằng GPA sau hiệu chỉnh, sau đó được kết hợp với độ ổn định và xu hướng tăng/giảm GPA theo từng kỳ.")
    story.append(P("TCI = 0.6*Performance + 0.2*Consistency + 0.2*Progress", styles["Callout"]))
    add_table(["Cấp", "Ngưỡng"], [
        ["Advanced", "TCI >= 3.60"],
        ["Proficient", "3.20 <= TCI < 3.60"],
        ["Intermediate", "2.50 <= TCI < 3.20"],
        ["At-Risk", "TCI < 2.50"],
        ["INSUFFICIENT_HISTORY", "Thiếu 5 môn và 3 kỳ"],
    ], [40 * mm, 60 * mm])
    story.append(Image(str(chart2), width=150 * mm, height=42 * mm, hAlign="CENTER"))
    story.append(P("Hình 3. Phân bố TCI theo cấp độ sinh viên.", styles["Small"]))
    story.append(PageBreak())

    # Chapter 5
    h1("CHƯƠNG 5. KIẾN TRÚC HỆ THỐNG VÀ MÔ HÌNH ML")
    body("Kiến trúc hệ thống tuân theo mô hình tuyến tính: dữ liệu gốc -> làm sạch -> tính chỉ số lớp -> hiệu chỉnh -> TCI -> dashboard và API. Quy trình này giúp tách rõ các bước tính toán và tạo ra một pipeline minh bạch, dễ kiểm soát và dễ nâng cấp.")
    body("Trên góc độ kỹ thuật, hệ thống chia thành ba lớp: module xử lý dữ liệu, module phân tích học thuật và module trình bày. Module xử lý dữ liệu đảm nhiệm chuẩn hóa cấu trúc dữ liệu, xác thực loại cột và xử lý các trường hợp thiếu. Module phân tích tiến hành tính toán các chỉ số lớp và TCI, đồng thời trả về nhãn đánh giá và công thức giới hạn review. Module trình bày xử lý dashboard, API và export để người dùng có thể xem trực tiếp đầu ra.")
    story.append(Image(str(system_path), width=150 * mm, height=48 * mm, hAlign="CENTER"))
    story.append(P("Hình 4. Sơ đồ module hệ thống và luồng dữ liệu.", styles["Small"]))
    body("Mô hình được lựa chọn bằng kiểm định thời gian, với dữ liệu train ở giai đoạn trước và dữ liệu test ở kỳ cuối. Cách làm này phù hợp với dữ liệu học tập vì dữ liệu điểm có tính chu kỳ và có xu hướng phát triển theo thời gian. Mô hình RandomForest được chọn trong pipeline hiện tại cho khả năng bền vững và hiệu quả trên tập dữ liệu dạng phi tuyến.")
    body("Kết quả đầu ra gồm: bảng điểm sạch, bảng đặc trưng lớp, bảng đặc trưng sinh viên, bảng review hiệu chỉnh, và báo cáo chất lượng. Tất cả các kết quả này được lưu trong thư mục data/processed để dễ tiếp cận và phát triển tiếp. Ngoài ra, API cũng cho phép người dùng upload file mới và nhận lại kết quả phân loại mà không cần chạy lại toàn bộ quy trình thủ công.")
    story.append(PageBreak())

    h1("CHƯƠNG 6. KIỂM ĐỊNH MÔ HÌNH VÀ ĐÁNH GIÁ THỰC NGHIỆM")
    body("Để xác định độ tin cậy của mô hình, nhóm thực hiện kiểm định theo kiểu train-test theo thời gian: các năm trước dùng làm tập huấn luyện, năm cuối được giữ lại làm tập kiểm tra. Cách làm này phù hợp với dữ liệu điểm học tập, vì dữ liệu có tính chu kỳ và người học chung không thể được xem là mẫu độc lập hoàn toàn giữa các kỳ. Đánh giá theo nhịp thời gian cho phép mô hình phản hồi mức độ dự đoán thực tế hơn là kiểm tra ngẫu nhiên trên cùng một tập dữ liệu.")
    body("Các chỉ số cho đánh giá gồm RMSE, MAE và R². RMSE đặc biệt phù hợp cho bối cảnh này vì nó phạt mạnh các sai số lớn, trong khi MAE dễ diễn giải hơn về mức độ chênh lệch trung bình giữa điểm dự báo và điểm thực tế. R² giúp đo mức độ giải thích của mô hình trên dữ liệu kiểm tra. Trong dữ liệu hiện tại, mô hình baseline và mô hình nâng cao đều đạt được mức độ cải thiện nhất định so với việc chỉ dựa trên prior GPA, cho thấy các yếu tố như phân bố điểm, tỷ lệ điểm A, độ lệch lớp và TCI đều góp phần bổ sung vào dự báo.")
    body("Về mặt mô tả thực tế, sự khác biệt giữa GPA danh nghĩa và GPA thực chất thường nhỏ ở những lớp ổn định nhưng có thể lớn ở những lớp có phân bố điểm lệch, điểm có độ đồng đều bất thường hoặc phần lớn sinh viên đạt điểm rất cao. Khi đó, phân tích của hệ thống cho phép cảnh báo thay vì bóp méo điểm gốc. Kết quả này phù hợp với mục tiêu của dự án: giúp người quản lý đào tạo nhận diện các trường hợp cần rà soát mà không tự động thay đổi quyết định từ điểm chính thức.")
    story.append(PageBreak())

    # Conclusion
    h1("CHƯƠNG 7. KẾT LUẬN")
    body("Hệ thống hiện tại cho thấy khả năng sàng lọc lớp cần rà soát, làm sạch dữ liệu và trực quan hóa hiệu quả thông qua GPA, AnomalyScore và TCI. Điểm mạnh của mô hình là sự minh bạch trong quy trình, khả năng kiểm tra từng bước và dễ tích hợp với hệ thống quản lý đào tạo.")
    body("Mức độ hoàn thiện của giải pháp nằm ở chỗ: cấu trúc dữ liệu rõ ràng, mô hình phân tích hoạt động ổn định, API và dashboard có thể mở rộng, và báo cáo kỹ thuật được mô tả theo logic khoa học. Trong bối cảnh triển khai thực tế, nhóm cần tiếp tục rà soát quy chế điểm, xác thực dữ liệu của các kỳ đặc biệt và kiểm tra lại các ngưỡng hội tụ trước khi ứng dụng vào quyết định học vụ chính thức.")
    body("Nghiên cứu cũng chỉ ra một thực tế quan trọng: công cụ phân tích không thể được xem như công cụ thay điểm chính thức. Giá trị thực sự của hệ thống nằm ở khả năng định hướng và hỗ trợ người ra quyết định, giảm rủi ro sai sót trong quy trình đánh giá và tạo nền tảng dữ liệu để chuyên môn kiểm tra chính xác hơn. Với dữ liệu và mô hình hiện có, hệ thống đã tạo ra một quy trình vận hành có thể mở rộng cho nhiều kỳ học, nhiều trường hợp và nhiều lớp học phần khác nhau.")
    body("Trong tương lai, nếu được bổ sung thêm dữ liệu về ngành, khóa, học phần và lịch sử điểm của nhiều năm học, hệ thống có thể đưa ra các phân loại ổn định hơn, cải thiện độ chính xác hơn ở mức phân tích cá nhân và nhóm. Khi đó, dashboard không chỉ là công cụ theo dõi mà còn là nền tảng để xây dựng hồ sơ điểm học tập theo thời gian, hỗ trợ quyết định về học bổng, quản lý học vụ và nâng cao hiệu quả giảng dạy.")
    story.append(PageBreak())

    # Appendix AI declaration
    h1("PHỤ LỤC A. KÊ KHAI ỨNG DỤNG AI")
    body("Trong quá trình xây dựng prototype, nhóm đã sử dụng GitHub Copilot trong VS Code như một công cụ hỗ trợ viết mã, rà lỗi, đề xuất cấu trúc API/dashboard và phát triển báo cáo kỹ thuật. Công cụ này không tham gia quyết định học vụ hay thay thế kiểm định của người dùng.")
    body("Phạm vi hỗ trợ chủ yếu là: gợi ý cơ sở mã, chuẩn hóa cấu trúc dự án, viết hàm xử lý dữ liệu, giúp rà soát lỗi và đề xuất các biểu đồ/biến số quan trọng. Mọi quy tắc tính toán, ngưỡng điểm và mô hình được nhóm kiểm tra lại theo dữ liệu thực tế trước khi chốt kết luận.")
    story.append(P("Kết luận về AI: công cụ AI chỉ đóng vai trò hỗ trợ lập trình và tài liệu; mọi kết luận cuối cùng thuộc về nhóm thực hiện và giảng viên hướng dẫn.", styles["Callout"]))

    # Build document
    doc = SimpleDocTemplate(
        str(PDF_PATH),
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
    )

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor("#DADFD9"))
        canvas.setLineWidth(0.8)
        canvas.line(18 * mm, 14 * mm, 190 * mm, 14 * mm)
        canvas.setFont(FONT, 7)
        canvas.setFillColor(colors.HexColor("#4E5D59"))
        canvas.drawString(18 * mm, 9 * mm, "NEU · Academic Integrity & True Competency Analytics")
        canvas.drawRightString(190 * mm, 9 * mm, f"Trang {doc.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return str(PDF_PATH)


if __name__ == "__main__":
    print(build_pdf())
