"""Create a local 3.5-minute walkthrough of a real flagged class."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import FancyBboxPatch

from advanced_analysis import make_student_features

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data" / "processed"
OUTPUT = ROOT / "deliverables" / "NEU_Academic_Analytics_Demo.mp4"
WIDTH, HEIGHT, FPS = 1280, 720, 24
SLIDE_SECONDS = 26.25
COLORS = {
    "green": "#183e36",
    "green2": "#2b7662",
    "mint": "#dcece3",
    "paper": "#f5f7f3",
    "ink": "#172b27",
    "muted": "#65746e",
    "orange": "#c96b3b",
    "gold": "#e4b54a",
    "blue": "#5279a3",
    "line": "#dce4de",
    "white": "#ffffff",
}


def load_case():
    classes = pd.read_csv(DATA_DIR / "course_features.csv")
    adjusted = pd.read_csv(DATA_DIR / "adjusted_scores.csv")
    clean = pd.read_csv(DATA_DIR / "du_lieu_clean.csv")
    students = pd.read_csv(DATA_DIR / "student_features.csv")

    keys = ["Năm học", "Học kỳ", "Mã môn", "Mã lớp học phần", "Mã SV"]
    metadata = clean[keys + ["Số TC", "Khóa SV", "Khoa của SV"]]
    original = adjusted.merge(metadata, on=keys, how="left", validate="one_to_one")
    original_year = pd.to_numeric(original["Năm học"].astype(str).str[:4], errors="coerce")
    original["term_order"] = original_year * 10 + pd.to_numeric(original["Học kỳ"], errors="coerce")
    original["Adjusted_Score"] = original["diem_hp_goc"]
    original["alpha_chiet_khau"] = 1.0
    original["REVIEW_REQUIRED"] = False
    baseline, _ = make_student_features(original)
    baseline["rank_before"] = baseline["TCI"].rank(method="min", ascending=False)
    students["rank_after"] = students["TCI"].rank(method="min", ascending=False)
    comparison = baseline[["Mã SV", "TCI", "rank_before"]].rename(
        columns={"TCI": "TCI_before"}
    ).merge(
        students[["Mã SV", "TCI", "rank_after"]],
        on="Mã SV",
        how="inner",
        validate="one_to_one",
    )
    comparison = comparison[comparison["TCI_before"].notna() & comparison["TCI"].notna()].copy()
    comparison["rank_shift"] = comparison["rank_before"] - comparison["rank_after"]

    scenarios = []
    flagged = classes[
        classes["nghi_van"].fillna(False)
        & classes["Nhan_bat_thuong"].eq("HIGH_INFLATION")
    ]
    for _, course in flagged.iterrows():
        mask = (
            adjusted["Năm học"].eq(course["Năm học"])
            & adjusted["Học kỳ"].eq(course["Học kỳ"])
            & adjusted["Mã môn"].eq(course["Mã môn"])
            & adjusted["Mã lớp học phần"].eq(course["Mã lớp học phần"])
        )
        course_scores = adjusted[mask].copy()
        members = comparison[comparison["Mã SV"].isin(course_scores["Mã SV"])]
        reduced = course_scores[course_scores["Adjusted_Score"] < course_scores["diem_hp_goc"]]
        if len(members) >= 5 and not reduced.empty:
            scenarios.append((float(course["diem_hp_tb"]), course, course_scores, members, reduced))

    if not scenarios:
        raise RuntimeError("Không tìm thấy lớp HIGH_INFLATION đủ điều kiện để làm video.")

    _, course, course_scores, members, reduced = max(scenarios, key=lambda item: item[0])
    clean_mask = (
        clean["Năm học"].eq(course["Năm học"])
        & clean["Học kỳ"].eq(course["Học kỳ"])
        & clean["Mã môn"].eq(course["Mã môn"])
        & clean["Mã lớp học phần"].eq(course["Mã lớp học phần"])
    )
    class_clean = clean[clean_mask]
    movers = members[members["Mã SV"].isin(reduced["Mã SV"])].copy()
    movers = movers.sort_values("rank_shift", key=lambda values: values.abs(), ascending=False)
    example = movers.iloc[0]
    example_score = reduced[reduced["Mã SV"].eq(example["Mã SV"])].sort_values("Adjusted_Score").iloc[0]
    members["moved_down"] = members["rank_after"] > members["rank_before"]
    members["moved_up"] = members["rank_after"] < members["rank_before"]
    return {
        "course": course,
        "scores": course_scores,
        "clean": class_clean,
        "members": members,
        "example": example,
        "example_score": example_score,
        "eligible_total": len(comparison),
        "raw_mean": float(course_scores["diem_hp_goc"].mean()),
        "adjusted_mean": float(course_scores["Adjusted_Score"].mean()),
        "a_rate": float(class_clean["Điểm HP (thang 10)"].ge(8.5).mean() * 100),
        "reduced_count": len(reduced),
        "moved_down": int(members["moved_down"].sum()),
        "moved_up": int(members["moved_up"].sum()),
        "unchanged": int((~members["moved_down"] & ~members["moved_up"]).sum()),
        "member_count": len(course_scores),
        "eligible_members": len(members),
    }


def new_slide(title, section, page):
    figure = plt.figure(figsize=(WIDTH / 100, HEIGHT / 100), dpi=100, facecolor=COLORS["paper"])
    axis = figure.add_axes([0, 0, 1, 1])
    axis.set(xlim=(0, 1), ylim=(0, 1))
    axis.axis("off")
    axis.add_patch(plt.Rectangle((0, 0.925), 1, 0.075, color=COLORS["green"], transform=axis.transAxes))
    axis.text(0.045, 0.962, "NEU  /  ACADEMIC ANALYTICS", color="white", fontsize=12,
              weight="bold", va="center", family="DejaVu Sans")
    axis.text(0.955, 0.962, f"DEMO  ·  {page}/8", color="#d5e5dc", fontsize=9,
              ha="right", va="center", family="DejaVu Sans")
    axis.text(0.055, 0.875, section.upper(), color=COLORS["green2"], fontsize=9,
              weight="bold", family="DejaVu Sans")
    axis.text(0.055, 0.81, title, color=COLORS["ink"], fontsize=23,
              weight="bold", family="DejaVu Sans")
    axis.plot([0.055, 0.945], [0.765, 0.765], color=COLORS["line"], linewidth=1)
    axis.text(0.055, 0.035, "Dữ liệu sinh viên được ẩn danh trong video · Kết quả hỗ trợ rà soát, không kết luận vi phạm",
              color=COLORS["muted"], fontsize=8, family="DejaVu Sans")
    return figure, axis


def card(axis, x, y, width, height, label, value, note, accent=None):
    accent = accent or COLORS["green2"]
    axis.add_patch(FancyBboxPatch((x, y), width, height, boxstyle="round,pad=.012,rounding_size=.012",
                                  facecolor="white", edgecolor="#e3e9e4", linewidth=1))
    axis.add_patch(plt.Rectangle((x, y), 0.012, height, color=accent))
    axis.text(x + 0.03, y + height - 0.05, label, color=COLORS["muted"], fontsize=9, family="DejaVu Sans")
    axis.text(x + 0.03, y + height - 0.12, value, color=COLORS["ink"], fontsize=21,
              weight="bold", family="DejaVu Sans")
    axis.text(x + 0.03, y + 0.035, note, color=COLORS["muted"], fontsize=8, family="DejaVu Sans")


def create_slides(data, folder):
    course = data["course"]
    example = data["example"]
    example_score = data["example_score"]
    slides = []

    fig, ax = new_slide("Từ lớp điểm cao đến thứ hạng năng lực thực chất", "Academic Integrity & True Competency", 1)
    ax.text(0.06, 0.67, "Kịch bản minh họa trên kết quả phân tích thực tế", fontsize=16,
            color=COLORS["muted"], family="DejaVu Sans")
    card(ax, 0.06, 0.40, 0.25, 0.18, "Lớp được rà soát", f"{course['Mã môn']} / {course['Mã lớp học phần']}",
         f"{course['Năm học']} · Học kỳ {course['Học kỳ']}")
    card(ax, 0.375, 0.40, 0.25, 0.18, "Điểm trung bình lớp", f"{data['raw_mean']:.2f} → {data['adjusted_mean']:.2f}",
         "Trước và sau hiệu chỉnh", COLORS["orange"])
    card(ax, 0.69, 0.40, 0.25, 0.18, "Sinh viên đủ TCI", f"{data['eligible_total']:,}",
         "Thứ hạng toàn bộ nhóm đủ lịch sử", COLORS["blue"])
    ax.text(0.06, 0.25, "Phát hiện  →  kiểm tra tín hiệu  →  hiệu chỉnh có truy vết  →  tính lại TCI và thứ hạng",
            fontsize=12, weight="bold", color=COLORS["green"], family="DejaVu Sans")
    slides.append(fig)

    fig, ax = new_slide("Phát hiện lớp có tín hiệu điểm cao bất thường", "01 / Detection", 2)
    card(ax, 0.07, 0.52, 0.25, 0.16, "Mã lớp", f"{course['Mã môn']} / {course['Mã lớp học phần']}",
         f"{course['Năm học']} · HK{course['Học kỳ']}")
    card(ax, 0.375, 0.52, 0.25, 0.16, "Điểm HP trung bình", f"{data['raw_mean']:.2f} / 10", f"{data['member_count']} sinh viên trong lớp",
         COLORS["orange"])
    card(ax, 0.68, 0.52, 0.25, 0.16, "Điểm từ 8,5 trở lên", f"{data['a_rate']:.1f}%", "Tỷ lệ tính từ điểm gốc",
         COLORS["gold"])
    ax.text(0.08, 0.38, f"Nhãn: {course['Nhan_bat_thuong']}     ·     Anomaly Score: {course['Anomaly_Score']:.3f}",
            fontsize=13, weight="bold", color=COLORS["orange"], family="DejaVu Sans")
    ax.text(0.08, 0.29, f"Hạng rà soát lớp: {int(course['Anomaly_Rank'])}     ·     {data['reduced_count']} điểm trong lớp có hiệu chỉnh giảm",
            fontsize=11, color=COLORS["ink"], family="DejaVu Sans")
    ax.text(0.08, 0.20, "Cờ thống kê là tín hiệu để chuyên môn kiểm tra, không phải kết luận sai phạm.",
            fontsize=10, color=COLORS["muted"], family="DejaVu Sans")
    slides.append(fig)

    fig, ax = new_slide("Vì sao lớp được đưa vào danh sách rà soát?", "02 / Peer comparison", 3)
    ax.text(0.08, 0.65, "Anomaly Score = 0,4 × S1 + 0,3 × S2 + 0,3 × S3", fontsize=17,
            weight="bold", color=COLORS["green"], family="DejaVu Sans")
    labels = ["S1  ·  độ lệch trung bình", "S2  ·  độ phân tán / tỷ lệ điểm cao", "S3  ·  độ khớp với năng lực nền"]
    notes = ["So lớp với nhóm đối chiếu phù hợp", "Nhận diện phân phối có dấu hiệu khác biệt", "So sánh với xu hướng GPA lịch sử"]
    for index, (label, note) in enumerate(zip(labels, notes)):
        y = 0.49 - index * 0.105
        ax.add_patch(FancyBboxPatch((0.08, y - 0.02), 0.84, 0.075,
                                    boxstyle="round,pad=.01,rounding_size=.008",
                                    facecolor="white", edgecolor=COLORS["line"]))
        ax.text(0.11, y + 0.015, label, fontsize=11, weight="bold", color=COLORS["ink"], family="DejaVu Sans")
        ax.text(0.53, y + 0.015, note, fontsize=9, color=COLORS["muted"], family="DejaVu Sans")
    ax.text(0.08, 0.12, f"Lớp được gắn nhãn {course['Nhan_bat_thuong']} với điểm trung bình {data['raw_mean']:.2f}/10.",
            fontsize=11, color=COLORS["orange"], family="DejaVu Sans")
    slides.append(fig)

    fig, ax = new_slide("Hiệu chỉnh điểm, vẫn giữ nguyên điểm gốc", "03 / Traceable adjustment", 4)
    chart = fig.add_axes([0.10, 0.23, 0.52, 0.42], facecolor="white")
    bars = chart.bar([0, 1], [data["raw_mean"], data["adjusted_mean"]], width=0.55,
                     color=["#8ca99a", COLORS["orange"]])
    chart.set_xticks([0, 1], ["Điểm gốc TB", "Adjusted Score TB"])
    chart.set_ylim(0, 10)
    chart.set_ylabel("Điểm thang 10")
    chart.grid(axis="y", color="#edf0ec")
    chart.set_axisbelow(True)
    chart.spines[["top", "right"]].set_visible(False)
    for bar, value in zip(bars, [data["raw_mean"], data["adjusted_mean"]]):
        chart.text(bar.get_x() + bar.get_width() / 2, value + 0.18, f"{value:.2f}",
                   ha="center", fontsize=12, weight="bold", color=COLORS["ink"])
    card(ax, 0.69, 0.48, 0.22, 0.17, "Bản ghi được giảm", f"{data['reduced_count']} / {data['member_count']}",
         "Điểm gốc vẫn lưu riêng", COLORS["orange"])
    ax.text(0.69, 0.34, "Hệ số α được lưu theo từng sinh viên–môn để truy vết.",
            fontsize=10, color=COLORS["muted"], wrap=True, family="DejaVu Sans")
    ax.text(0.10, 0.13, "Điểm sau hiệu chỉnh chỉ hỗ trợ phân tích; không tự thay điểm chính thức.",
            fontsize=10, color=COLORS["muted"], family="DejaVu Sans")
    slides.append(fig)

    fig, ax = new_slide("Một bản ghi minh họa, mã sinh viên đã ẩn", "04 / Student example", 5)
    ax.text(0.08, 0.65, "Sinh viên minh họa: SV ẩn danh", fontsize=16, weight="bold",
            color=COLORS["green"], family="DejaVu Sans")
    card(ax, 0.08, 0.38, 0.25, 0.18, "Điểm học phần gốc", f"{example_score['diem_hp_goc']:.2f}",
         f"{course['Mã môn']} / {course['Mã lớp học phần']}", COLORS["blue"])
    card(ax, 0.375, 0.38, 0.25, 0.18, "Điểm sau hiệu chỉnh", f"{example_score['Adjusted_Score']:.2f}",
         f"α = {example_score['alpha_chiet_khau']:.3f}", COLORS["orange"])
    card(ax, 0.67, 0.38, 0.25, 0.18, "TCI sau hiệu chỉnh", f"{example['TCI']:.3f}",
         "Tính từ GPA, ổn định và tiến bộ", COLORS["green2"])
    ax.text(0.08, 0.23, "Không hiển thị mã SV hoặc thông tin nhận diện cá nhân trong video.",
            fontsize=11, color=COLORS["muted"], family="DejaVu Sans")
    slides.append(fig)

    fig, ax = new_slide("TCI được tính lại sau khi có điểm điều chỉnh", "05 / Recalculation", 6)
    labels = ["Trước hiệu chỉnh", "Sau hiệu chỉnh"]
    values = [float(example["TCI_before"]), float(example["TCI"])]
    chart = fig.add_axes([0.22, 0.33, 0.65, 0.34], facecolor="white")
    bars = chart.barh([1, 0], values, height=0.38, color=["#8ca99a", COLORS["green2"]])
    chart.set_xlim(0, 4)
    chart.set_yticks([1, 0], labels)
    chart.set_xlabel("TCI (0–4)")
    chart.grid(axis="x", color="#edf0ec")
    chart.set_axisbelow(True)
    chart.spines[["top", "right", "left"]].set_visible(False)
    for bar, value in zip(bars, values):
        chart.text(value + 0.05, bar.get_y() + bar.get_height() / 2, f"{value:.3f}", va="center",
                   fontsize=12, weight="bold", color=COLORS["ink"])
    ax.text(0.08, 0.18, "TCI = 0,6 × hiệu suất + 0,2 × ổn định + 0,2 × tiến bộ",
            fontsize=12, weight="bold", color=COLORS["green"], family="DejaVu Sans")
    slides.append(fig)

    fig, ax = new_slide("Thứ hạng thay đổi theo TCI sau hiệu chỉnh", "06 / Before-after ranking", 7)
    rank_values = [int(example["rank_before"]), int(example["rank_after"])]
    chart = fig.add_axes([0.12, 0.38, 0.78, 0.31], facecolor="white")
    chart.plot(rank_values, [0.5, 0.5], color=COLORS["line"], linewidth=8, solid_capstyle="round")
    chart.scatter(rank_values, [0.5, 0.5], s=260, color=["#8ca99a", COLORS["orange"]], zorder=3)
    chart.annotate(f"Trước · hạng {rank_values[0]}", (rank_values[0], 0.5), xytext=(0, 30),
                   textcoords="offset points", ha="center", fontsize=11, weight="bold", color=COLORS["ink"])
    chart.annotate(f"Sau · hạng {rank_values[1]}", (rank_values[1], 0.5), xytext=(0, -30),
                   textcoords="offset points", ha="center", fontsize=11, weight="bold", color=COLORS["ink"])
    chart.set_xlim(0, max(rank_values) + 120)
    chart.set_ylim(0.2, 0.8)
    chart.set_yticks([])
    chart.set_xlabel(f"Thứ hạng TCI trong {data['eligible_total']:,} sinh viên đủ lịch sử · hạng 1 là cao nhất")
    chart.spines[["top", "right", "left"]].set_visible(False)
    ax.text(0.08, 0.18, f"Trong {data['eligible_members']} thành viên lớp đủ TCI: {data['moved_down']} hạng giảm, "
            f"{data['moved_up']} hạng tăng, {data['unchanged']} không đổi.",
            fontsize=11, color=COLORS["green"], family="DejaVu Sans")
    slides.append(fig)

    fig, ax = new_slide("Kết quả hỗ trợ rà soát, không tự động kết luận", "07 / API handoff", 8)
    card(ax, 0.08, 0.49, 0.25, 0.17, "Nhận CSV điểm", "POST /api/analyze", "Kiểm tra cột và chạy pipeline", COLORS["blue"])
    card(ax, 0.375, 0.49, 0.25, 0.17, "Xem lớp", "GET /api/classes", "Nhãn, điểm và hạng bất thường", COLORS["orange"])
    card(ax, 0.67, 0.49, 0.25, 0.17, "Xem TCI", "GET /api/students", "Phân loại năng lực sau điều chỉnh", COLORS["green2"])
    ax.text(0.08, 0.31, "Người phụ trách cần xem lại đề thi, rubric và bối cảnh giảng dạy trước khi quyết định.",
            fontsize=11, color=COLORS["ink"], family="DejaVu Sans")
    ax.text(0.08, 0.22, "Demo dùng dữ liệu đã xử lý; định danh cá nhân được ẩn trên các màn hình minh họa.",
            fontsize=10, color=COLORS["muted"], family="DejaVu Sans")
    slides.append(fig)

    for index, figure in enumerate(slides, start=1):
        figure.savefig(folder / f"slide_{index:02d}.png", dpi=100, facecolor=COLORS["paper"])
        plt.close(figure)


def main():
    ffmpeg = shutil.which("ffmpeg") or next(
        (path for path in ("/usr/bin/ffmpeg", "/bin/ffmpeg") if Path(path).is_file()),
        None,
    )
    if not ffmpeg:
        raise RuntimeError("Cần cài ffmpeg để xuất video MP4.")
    case = load_case()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="neu-demo-") as temporary:
        folder = Path(temporary)
        create_slides(case, folder)
        concat = folder / "slides.txt"
        entries = [f"file '{folder / f'slide_{index:02d}.png'}'\nduration {SLIDE_SECONDS}\n" for index in range(1, 9)]
        entries.append(f"file '{folder / 'slide_08.png'}'\n")
        concat.write_text("".join(entries), encoding="utf-8")
        command = [
            ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", str(concat),
            "-vf", f"scale={WIDTH}:{HEIGHT},fps={FPS},format=yuv420p",
            "-c:v", "libx264", "-preset", "medium", "-crf", "23",
            "-t", "210", "-movflags", "+faststart", str(OUTPUT),
        ]
        subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    print(OUTPUT)


if __name__ == "__main__":
    main()