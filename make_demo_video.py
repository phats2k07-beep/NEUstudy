"""Create a captioned 3.5-minute MP4 walkthrough from real processed outputs."""

from pathlib import Path
import subprocess
import tempfile

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import FancyBboxPatch

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data" / "processed"
OUTPUT = ROOT / "deliverables" / "NEU_Academic_Analytics_Demo.mp4"
GREEN = "#183e36"
GREEN2 = "#2b7662"
MINT = "#dcece3"
PAPER = "#f5f7f3"
INK = "#172b27"
MUTED = "#65746e"
ORANGE = "#c96b3b"
GOLD = "#e4b54a"
BLUE = "#5279a3"
FONT = "DejaVu Sans"


def load_data():
    return {
        "clean": pd.read_csv(DATA / "du_lieu_clean.csv"),
        "classes": pd.read_csv(DATA / "course_features.csv"),
        "adjusted": pd.read_csv(DATA / "adjusted_scores.csv"),
        "students": pd.read_csv(DATA / "student_features.csv"),
        "quality": pd.read_csv(DATA / "bao_cao_clean_data.csv"),
        "raw_rows": len(pd.read_csv(ROOT / "data" / "raw" / "Du_lieu.csv", usecols=["Mã SV"])),
    }


def canvas(title, kicker, page):
    fig = plt.figure(figsize=(12.8, 7.2), dpi=100, facecolor=PAPER)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.add_patch(FancyBboxPatch((0, .93), 1, .07, boxstyle="square,pad=0", facecolor=GREEN, edgecolor="none"))
    ax.text(.045, .965, "NEU  /  SMART CAMPUS", color="white", fontsize=12, weight="bold", va="center", family=FONT)
    ax.text(.955, .965, f"DEMO WALKTHROUGH  ·  {page}/7", color="#d5e5dc", fontsize=9, ha="right", va="center", family=FONT)
    ax.text(.055, .865, kicker.upper(), color=GREEN2, fontsize=9, weight="bold", family=FONT)
    ax.text(.055, .80, title, color=INK, fontsize=24, weight="bold", family=FONT)
    ax.plot([.055, .945], [.755, .755], color="#dce4de", lw=1)
    ax.text(.055, .035, "Prototype sàng lọc · Không thay thế đánh giá chuyên môn hoặc điểm chính thức", color=MUTED, fontsize=8, family=FONT)
    return fig, ax


def card(ax, x, y, width, height, label, value, note, accent=GREEN2):
    ax.add_patch(FancyBboxPatch((x, y), width, height, boxstyle="round,pad=.012,rounding_size=.012", facecolor="white", edgecolor="#e3e9e4", linewidth=1))
    ax.add_patch(FancyBboxPatch((x, y), .012, height, boxstyle="round,pad=.002,rounding_size=.008", facecolor=accent, edgecolor="none"))
    ax.text(x + .035, y + height - .055, label, color=MUTED, fontsize=9, family=FONT)
    ax.text(x + .035, y + height - .125, value, color=INK, fontsize=23, weight="bold", family=FONT)
    ax.text(x + .035, y + .035, note, color=MUTED, fontsize=8, family=FONT)


def create_slides(data, folder):
    clean, classes, adjusted, students, quality = (data[key] for key in ("clean", "classes", "adjusted", "students", "quality"))
    total_classes = len(classes)
    flagged = classes[classes["nghi_van"].fillna(False)].sort_values("Anomaly_Rank", na_position="last")
    tci_students = students[students["TCI"].notna()]
    levels = students["Phan_cap"].value_counts()
    review_count = int(adjusted["REVIEW_REQUIRED"].fillna(False).sum())
    missing_grade = int(quality.loc[quality["chi_tieu"].eq("Dòng thiếu Điểm HP"), "so_luong"].iloc[0])
    model_rows = quality[quality["nhom_bao_cao"].eq("kiem_dinh_model")]
    chosen = model_rows[model_rows["ghi_chu"].astype(str).str.contains("duoc_chon=True", regex=False)]
    chosen_model = chosen.iloc[0]["chi_tieu"].replace("RMSE_", "") if not chosen.empty else "Chưa có"

    slides = []
    fig, ax = canvas("Phân tích công bằng điểm và năng lực thực chất", "Academic Integrity & True Competency Analytics", 1)
    ax.text(.06, .67, "Bộ dữ liệu kết quả học tập 2019–2026", fontsize=14, color=MUTED, family=FONT)
    card(ax, .06, .39, .25, .19, "Dòng điểm sau làm sạch", f"{len(clean):,}", "Tách dữ liệu nguồn và dữ liệu phân tích")
    card(ax, .37, .39, .25, .19, "Lớp học phần", f"{total_classes:,}", "Đối chiếu theo môn · kỳ · loại lớp")
    card(ax, .68, .39, .25, .19, "TCI đủ lịch sử", f"{len(tci_students):,}", "Ít nhất 5 môn và 3 học kỳ", GOLD)
    ax.text(.06, .25, "Ba bước: sàng lọc lớp  →  review/hiệu chỉnh  →  phân loại TCI", fontsize=13, weight="bold", color=GREEN, family=FONT)
    ax.text(.06, .19, "Mỗi cờ là tín hiệu cần kiểm tra, không phải kết luận vi phạm.", fontsize=11, color=MUTED, family=FONT)
    slides.append(fig)

    fig, ax = canvas("Làm sạch có kiểm soát, giữ nguyên nguồn", "01 / Data quality", 2)
    card(ax, .06, .48, .26, .18, "Dòng nguồn", f"{data['raw_rows']:,}", "CSV gốc không bị sửa")
    card(ax, .37, .48, .26, .18, "Thiếu điểm HP", f"{missing_grade:,}", "Không có target để huấn luyện", ORANGE)
    card(ax, .68, .48, .26, .18, "Dòng sạch có nhãn", f"{len(clean):,}", "Điểm thành phần thiếu vẫn để trống", GREEN2)
    ax.text(.07, .35, "Quy tắc chính", fontsize=13, weight="bold", color=GREEN, family=FONT)
    lines = ["• Điểm sai miền / không phải số: loại dòng", "• Trùng khóa hoặc thiếu khóa: loại và ghi báo cáo", "• Thiếu CC/KTTX/Thi: không thay bằng 0", "• Sĩ số nguồn lệch số mã SV: loại lớp; lớp nhỏ khớp sĩ số vẫn giữ"]
    for i, line in enumerate(lines): ax.text(.08, .29 - i * .052, line, fontsize=10, color=INK, family=FONT)
    slides.append(fig)

    fig, ax = canvas("So sánh phân phối trước và sau hiệu chỉnh", "02 / Remediation", 3)
    ax_hist = fig.add_axes([.09, .20, .58, .48], facecolor="white")
    bins = np.linspace(0, 4, 9)
    ax_hist.hist(students["GPA_goc"].dropna(), bins=bins, color="#b9c9c0", alpha=.85, label="GPA gốc")
    ax_hist.hist(students["Normalized_GPA"].dropna(), bins=bins, color=GREEN2, alpha=.72, label="Normalized GPA")
    ax_hist.set_xlabel("GPA hệ 4 theo điểm chữ và tín chỉ (khoảng 0,5)", family=FONT)
    ax_hist.set_ylabel("Số sinh viên", family=FONT)
    ax_hist.legend(frameon=False, loc="upper left")
    ax_hist.grid(axis="y", color="#edf0ec")
    ax_hist.spines[["top", "right", "left"]].set_visible(False)
    card(ax, .73, .49, .21, .16, "Mô hình test tốt nhất", chosen_model, "So với prior-GPA baseline", BLUE)
    card(ax, .73, .27, .21, .16, "Review yêu cầu", f"{review_count:,}", "Chỉ trên lớp bị gắn nghi vấn", ORANGE)
    ax.text(.09, .12, "Quy đổi môn: A+ 9–10=4,0 · A 8,5–<9=4,0 · B+ 8–<8,5=3,5 · B 7–<8=3,0 · C+ 6,5–<7=2,5 · C 6–<6,5=2,0 · D+ 5,5–<6=1,5 · D 4,5–<5,5=1,0 · F<4,5=0", fontsize=7.1, color=MUTED, family=FONT)
    ax.text(.73, .19, "Điểm gốc vẫn được lưu riêng.", fontsize=8, color=MUTED, family=FONT)
    slides.append(fig)

    fig, ax = canvas("Xếp hạng lớp cần rà soát", "03 / Grade anomaly", 4)
    ax.text(.07, .69, "Anomaly Score = 0,4·S1 + 0,3·S2 + 0,3·S3", fontsize=15, color=GREEN, weight="bold", family=FONT)
    ax.text(.07, .63, "S1: lệch robust-Z   ·   S2: độ phân tán / tỷ lệ A   ·   S3: tương quan với GPA lịch sử", fontsize=9, color=MUTED, family=FONT)
    headers = ["Hạng", "Môn / lớp", "TB HP", "% A", "Score", "Nhãn"]
    xs = [.08, .17, .45, .57, .70, .81]
    for x, text in zip(xs, headers): ax.text(x, .55, text, fontsize=9, weight="bold", color=MUTED, family=FONT)
    displayed = flagged.head(5)
    for index, (_, row) in enumerate(displayed.iterrows()):
        y = .48 - index * .065
        ax.add_patch(FancyBboxPatch((.065, y - .018), .87, .05, boxstyle="round,pad=.005,rounding_size=.006", facecolor="white", edgecolor="#e6ece7"))
        label = str(row.get("Nhan_bat_thuong", ""))
        vals = [str(row.get("Anomaly_Rank", "—")), f"{row.get('Mã môn','')} / {row.get('Mã lớp học phần','')}", f"{row.get('diem_hp_tb',np.nan):.2f}", f"{row.get('ty_le_diem_A',np.nan):.1f}%", f"{row.get('Anomaly_Score',np.nan):.3f}", label.replace("_", " ")]
        for x, text in zip(xs, vals): ax.text(x, y, text[:22], fontsize=8, color=INK, family=FONT, va="center")
    ax.text(.07, .10, f"{len(flagged):,} lớp được gắn cờ trong {total_classes:,}. Người phụ trách cần xem đề, rubric và hồ sơ điểm.", fontsize=10, color=ORANGE, family=FONT)
    slides.append(fig)

    fig, ax = canvas("Điểm điều chỉnh có thể truy vết", "04 / Review, not auto-judgment", 5)
    selected = adjusted[adjusted["REVIEW_REQUIRED"].fillna(False)].head(1)
    if selected.empty: selected = adjusted[adjusted["nghi_van"].fillna(False)].head(1)
    if not selected.empty:
        row = selected.iloc[0]
        card(ax, .07, .49, .25, .17, "Mã học phần", f"{row['Mã môn']} / {row['Mã lớp học phần']}", f"Học kỳ {row['Học kỳ']} · {row['Năm học']}", GREEN2)
        card(ax, .37, .49, .25, .17, "Điểm gốc", f"{row['diem_hp_goc']:.2f}", "Không sửa giá trị nguồn", BLUE)
        card(ax, .68, .49, .25, .17, "Adjusted Score", f"{row['Adjusted_Score']:.2f}", f"α = {row['alpha_chiet_khau']:.3f}", ORANGE)
        ax.text(.08, .36, f"Nhãn lớp: {row.get('Nhan_bat_thuong','—')}    ·    Anomaly Score: {row.get('Anomaly_Score',np.nan):.3f}", fontsize=11, color=GREEN, weight="bold", family=FONT)
        ax.text(.08, .29, f"REVIEW_REQUIRED: {bool(row['REVIEW_REQUIRED'])}", fontsize=12, color=ORANGE, weight="bold", family=FONT)
    else:
        ax.text(.08, .49, "Không có bản ghi review trong lượt chạy này.", fontsize=16, color=INK, family=FONT)
    ax.text(.08, .18, "Điểm được chuẩn hóa chỉ khi có đủ lớp đối chiếu; thiếu điều kiện thì giữ điểm gốc.", fontsize=10, color=MUTED, family=FONT)
    slides.append(fig)

    fig, ax = canvas("TCI tóm tắt năng lực theo lịch sử học tập", "05 / Student profiling", 6)
    order = ["Advanced", "Proficient", "Intermediate", "At-Risk", "INSUFFICIENT_HISTORY"]
    names = ["Advanced", "Proficient", "Intermediate", "At-Risk", "Chưa đủ lịch sử"]
    values = [int(levels.get(label, 0)) for label in order]
    bars = ax.barh([.60, .51, .42, .33, .24], values, height=.045, color=[GREEN2, "#78a78c", GOLD, ORANGE, "#c8d1cc"])
    for y, name, value, bar in zip([.60, .51, .42, .33, .24], names, values, bars):
        ax.text(.08, y, name, fontsize=10, color=INK, va="center", family=FONT)
        ax.add_patch(FancyBboxPatch((.31, y - .018), .44, .036, boxstyle="round,pad=.002,rounding_size=.01", facecolor="#e8ede9", edgecolor="none"))
        max_value = max(values + [1])
        ax.add_patch(FancyBboxPatch((.31, y - .018), .44 * value / max_value, .036, boxstyle="round,pad=.002,rounding_size=.01", facecolor=bar.get_facecolor(), edgecolor="none"))
        ax.text(.78, y, f"{value:,}", fontsize=10, weight="bold", color=INK, va="center", family=FONT)
    ax.text(.08, .12, "TCI = 0,6·Performance + 0,2·Consistency + 0,2·Progress", fontsize=12, weight="bold", color=GREEN, family=FONT)
    slides.append(fig)

    fig, ax = canvas("Dashboard, API và giới hạn triển khai", "06 / Demo handoff", 7)
    card(ax, .07, .49, .25, .17, "Dashboard", "Local web", "Lọc lớp · tra hồ sơ · biểu đồ", GREEN2)
    card(ax, .37, .49, .25, .17, "REST API", "/api/analyze", "Upload CSV → 5 đầu ra", BLUE)
    card(ax, .68, .49, .25, .17, "Thời khóa biểu", "Tách biệt", "Mã không có crosswalk tin cậy", ORANGE)
    ax.text(.08, .33, "Mở Swagger: /docs", fontsize=13, color=GREEN, weight="bold", family=FONT)
    ax.text(.08, .25, "Cần xác nhận quy chế điểm chữ, bảo mật/ủy quyền và ngưỡng nghiệp vụ trước triển khai trường.", fontsize=10, color=MUTED, family=FONT)
    ax.text(.08, .17, "AI hỗ trợ code/tài liệu; thống kê trong demo được tính trực tiếp từ CSV.", fontsize=10, color=MUTED, family=FONT)
    slides.append(fig)

    for number, figure in enumerate(slides, start=1):
        figure.savefig(folder / f"slide_{number:02d}.png", dpi=100, facecolor=PAPER)
        plt.close(figure)


def main():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    data = load_data()
    with tempfile.TemporaryDirectory(prefix="neu-demo-frames-") as temp:
        folder = Path(temp)
        create_slides(data, folder)
        concat_file = folder / "slides.txt"
        concat_file.write_text("".join(f"file '{folder / f'slide_{index:02d}.png'}'\nduration 30\n" for index in range(1, 8)) + f"file '{folder / 'slide_07.png'}'\n", encoding="utf-8")
        command = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_file),
            "-vf", "fps=24,format=yuv420p", "-c:v", "libx264", "-preset", "medium",
            "-crf", "24", "-movflags", "+faststart", "-t", "210", str(OUTPUT),
        ]
        subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    print(OUTPUT)


if __name__ == "__main__":
    main()
