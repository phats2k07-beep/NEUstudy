"""Clean enrollment data and generate course- and student-level features.

This dataset has no explicit midterm/final columns. `KTTX (TB)` is used as
continuous-assessment proxy, `Thi` as exam score, and `Điểm HP (thang 10)` as
official course grade. These are not treated as exact midterm/final equivalents.
"""

from pathlib import Path
import os
import pandas as pd
import numpy as np
from advanced_analysis import (
    make_adjusted_scores,
    make_class_anomaly_features,
    make_student_features as make_student_tci,
)


ROOT = Path(__file__).resolve().parent
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = Path(os.environ.get("FIT_OUTPUT_DIR", ROOT / "data" / "processed"))
INPUT_FILE = Path(os.environ.get("FIT_INPUT_FILE", RAW_DIR / "Du_lieu.csv"))
CLEAN_FILE = PROCESSED_DIR / "du_lieu_clean.csv"
COURSE_FEATURE_FILE = PROCESSED_DIR / "course_features.csv"
STUDENT_FEATURE_FILE = PROCESSED_DIR / "student_features.csv"
QUALITY_FILE = PROCESSED_DIR / "bao_cao_clean_data.csv"
ADJUSTED_SCORE_FILE = PROCESSED_DIR / "adjusted_scores.csv"

KEY_COLUMNS = ["Năm học", "Học kỳ", "Mã môn", "Mã lớp học phần", "Mã SV"]
SCORE_COLUMNS = ["CC", "KTTX1", "KTTX2", "KTTX (TB)", "Thi", "Điểm HP (thang 10)"]
CLASS_COLUMNS = ["Năm học", "Học kỳ", "Mã môn", "Mã lớp học phần"]
PASSING_SCORE = 4.5


def clean_data(path: Path):
    df = pd.read_csv(path)
    source_columns = df.columns.tolist()
    original_rows = len(df)

    string_columns = [col for col in df.columns if str(df[col].dtype) in {"object", "str", "string"}]
    for col in string_columns:
        df[col] = df[col].map(lambda value: value.strip() if isinstance(value, str) else value)
        df[col] = df[col].replace("", np.nan)

    missing_key_rows = int(df[KEY_COLUMNS].isna().any(axis=1).sum())
    df = df.dropna(subset=KEY_COLUMNS).copy()

    exact_duplicate_rows = int(df.duplicated(keep="first").sum())
    df = df.drop_duplicates(keep="first").copy()

    invalid_cells = pd.DataFrame(False, index=df.index, columns=SCORE_COLUMNS)
    for col in SCORE_COLUMNS + ["Số TC", "Sĩ số lớp (trong dữ liệu)"]:
        if col in df.columns:
            original = df[col]
            numeric = pd.to_numeric(original, errors="coerce")
            if col in SCORE_COLUMNS:
                invalid_cells[col] = (original.notna() & numeric.isna()) | numeric.lt(0) | numeric.gt(10)
            df[col] = numeric

    df["loai_lop"] = np.select(
        [
            df["Là đồ án/thực tập/khóa luận"].eq("Có"),
            df["Lớp mang mã EP"].eq("Có"),
        ],
        ["Do_an_thuc_tap_khoa_luan", "EP"],
        default="He_thuong",
    )
    quality_score_columns = ["CC", "KTTX1", "KTTX (TB)", "Thi", "Điểm HP (thang 10)"]
    quality_missing = df[quality_score_columns].isna() | invalid_cells[quality_score_columns]
    class_quality = df.assign(_quality_missing=quality_missing.sum(axis=1)).groupby(
        CLASS_COLUMNS + ["loai_lop"], dropna=False
    ).agg(
        so_dong_goc_lop=("Mã SV", "nunique"),
        _missing_score_cells=("_quality_missing", "sum"),
        nhom_mon=("Nhóm môn", "first"),
        so_tin_chi=("Số TC", "first"),
        co_cau_trong_so=("Cơ cấu trọng số suy ra (CC/KTTX/Thi, %)", "first"),
        si_so_min=("Sĩ số lớp (trong dữ liệu)", "min"),
        si_so_max=("Sĩ số lớp (trong dữ liệu)", "max"),
    ).reset_index()
    class_quality["ty_le_thieu_diem_lop_pct"] = (
        100 * class_quality["_missing_score_cells"]
        / (class_quality["so_dong_goc_lop"] * len(quality_score_columns))
    )
    class_quality["ty_le_thieu_diem_hp_goc_pct"] = 100 * df.groupby(
        CLASS_COLUMNS + ["loai_lop"], dropna=False
    )["Điểm HP (thang 10)"].apply(lambda values: values.isna().mean()).to_numpy()
    class_quality = class_quality.drop(columns="_missing_score_cells")

    class_quality["sai_lech_si_so"] = (
        class_quality["si_so_min"].notna()
        & (
            class_quality["si_so_min"].ne(class_quality["si_so_max"])
            | class_quality["si_so_min"].ne(class_quality["so_dong_goc_lop"])
        )
    )
    mismatched_classes = class_quality.loc[class_quality["sai_lech_si_so"], CLASS_COLUMNS].drop_duplicates()
    mismatched_class_count = len(mismatched_classes)
    mismatched_keys = pd.MultiIndex.from_frame(mismatched_classes)
    row_keys = pd.MultiIndex.from_frame(df[CLASS_COLUMNS])
    mismatched_rows = row_keys.isin(mismatched_keys)
    mismatched_row_count = int(mismatched_rows.sum())
    df = df.loc[~mismatched_rows].copy()
    class_quality = class_quality.loc[~class_quality["sai_lech_si_so"]].copy()
    class_quality["si_so_ghi_nhan"] = class_quality["si_so_min"]
    class_quality = class_quality.drop(columns=["si_so_min", "si_so_max", "sai_lech_si_so"])

    student_meta = df.groupby("Mã SV", dropna=False).agg(
        khoa_sv=("Khóa SV", "first"),
        khoa_faculty=("Khoa của SV", "first"),
    ).reset_index()

    invalid_rows = invalid_cells.any(axis=1)
    invalid_score_rows = int(invalid_rows.sum())
    invalid_scores = {col: int(invalid_cells[col].sum()) for col in SCORE_COLUMNS}
    df = df.loc[~invalid_rows].copy()

    missing_final_grade = df["Điểm HP (thang 10)"].isna()
    missing_final_grade_rows = int(missing_final_grade.sum())
    df = df.loc[~missing_final_grade].copy()

    duplicate_rows = int(df.duplicated(KEY_COLUMNS).sum())
    df = df.drop_duplicates(KEY_COLUMNS, keep="first").copy()

    has_tx2 = df.groupby(CLASS_COLUMNS, dropna=False)["KTTX2"].transform("count").gt(0)
    df["KTTX2_su_dung"] = df["KTTX2"].where(has_tx2, df["KTTX1"])
    df["KTTX2_duoc_thay_bang_TX1"] = ~has_tx2 & df["KTTX1"].notna()
    calculated_process_score = (df["KTTX1"] + df["KTTX2_su_dung"]) / 2
    df["diem_qua_trinh"] = df["KTTX (TB)"].combine_first(calculated_process_score)
    df["chenh_thi_kttx_tb"] = df["Thi"] - df["KTTX (TB)"]

    report_rows = []
    for col in pd.read_csv(path, nrows=0).columns:
        source = pd.read_csv(path, usecols=[col])[col]
        if col in SCORE_COLUMNS:
            action = "Điểm ngoài [0,10] chuyển thành thiếu; không tự điền giá trị."
            if col == "KTTX2":
                action += " Cột gốc giữ nguyên; ở lớp không có TX2, TX1 được dùng thay lần 2 khi tính điểm quá trình."
        elif col in KEY_COLUMNS:
            action = "Dòng thiếu khóa bị loại; khóa trùng giữ bản ghi đầu tiên."
        else:
            action = "Giữ nguyên; feature tổng hợp bỏ qua giá trị thiếu."
        report_rows.append({
            "cot": col,
            "so_gia_tri_thieu_goc": int(source.isna().sum()),
            "ty_le_thieu_goc_pct": round(float(source.isna().mean() * 100), 3),
            "xu_ly": action,
        })

    report_rows.extend([
        {"cot": "KTTX2_su_dung / diem_qua_trinh", "so_gia_tri_thieu_goc": int(df["diem_qua_trinh"].isna().sum()),
         "ty_le_thieu_goc_pct": round(float(df["diem_qua_trinh"].isna().mean() * 100), 3),
         "xu_ly": "Trong lớp không có TX2: dùng TX1 cho cả hai lượt, điểm quá trình=(TX1+TX1)/2=TX1. Trong lớp có TX2: dùng KTTX(TB), tương đương (TX1+TX2)/2 khi có đủ điểm."},
        {"cot": "loai_lop", "so_gia_tri_thieu_goc": 0,
         "ty_le_thieu_goc_pct": 0.0,
         "xu_ly": "Phân thành EP, He_thuong, Do_an_thuc_tap_khoa_luan; ưu tiên nhóm đồ án nếu cờ đồ án là Có."},
        {"cot": "Dòng thiếu khóa", "so_gia_tri_thieu_goc": missing_key_rows,
         "ty_le_thieu_goc_pct": round(missing_key_rows / max(original_rows, 1) * 100, 3),
         "xu_ly": "Đã loại dòng thiếu khóa định danh."},
        {"cot": "Dòng trùng khóa ghi danh", "so_gia_tri_thieu_goc": duplicate_rows,
         "ty_le_thieu_goc_pct": 0.0,
         "xu_ly": "Đã loại bản ghi trùng theo năm học, học kỳ, môn, lớp học phần, sinh viên."},
        {"cot": "Dòng trùng hoàn toàn", "so_gia_tri_thieu_goc": exact_duplicate_rows,
         "ty_le_thieu_goc_pct": round(exact_duplicate_rows / max(original_rows, 1) * 100, 3),
         "xu_ly": "Giữ bản ghi xuất hiện đầu tiên; loại các dòng giống toàn bộ cột."},
        {"cot": "Dòng có điểm ngoài [0,10] hoặc không phải số", "so_gia_tri_thieu_goc": invalid_score_rows,
         "ty_le_thieu_goc_pct": round(invalid_score_rows / max(original_rows, 1) * 100, 3),
         "xu_ly": "Loại toàn bộ dòng nếu có ít nhất một điểm sai miền hoặc không chuyển được sang số."},
        {"cot": "Dòng thiếu Điểm HP", "so_gia_tri_thieu_goc": missing_final_grade_rows,
         "ty_le_thieu_goc_pct": round(missing_final_grade_rows / max(original_rows, 1) * 100, 3),
         "xu_ly": "Loại khỏi bảng điểm sạch và dữ liệu có nhãn; số thiếu ban đầu vẫn được ghi trong báo cáo."},
        {"cot": "Số lớp dưới 15 sinh viên", "so_gia_tri_thieu_goc": int(class_quality["so_dong_goc_lop"].lt(15).sum()),
         "ty_le_thieu_goc_pct": round(class_quality["so_dong_goc_lop"].lt(15).mean() * 100, 3),
         "xu_ly": "Gắn cờ mẫu nhỏ; không tự loại lớp."},
        {"cot": "Lớp sai lệch sĩ số ghi nhận", "so_gia_tri_thieu_goc": mismatched_class_count,
         "ty_le_thieu_goc_pct": round(mismatched_class_count / max(mismatched_class_count + len(class_quality), 1) * 100, 3),
         "xu_ly": f"Loại {mismatched_row_count} dòng thuộc lớp có sĩ số ghi nhận không khớp số mã SV duy nhất trong file; không loại lớp chỉ vì sĩ số nhỏ."},
        {"cot": "Số lớp thiếu trên 30% dữ liệu điểm", "so_gia_tri_thieu_goc": int(class_quality["ty_le_thieu_diem_lop_pct"].gt(30).sum()),
         "ty_le_thieu_goc_pct": round(class_quality["ty_le_thieu_diem_lop_pct"].gt(30).mean() * 100, 3),
         "xu_ly": "Tỷ lệ thiếu tính trên ô điểm CC, KTTX1, KTTX(TB), Thi và Điểm HP; gắn cờ, không tự loại lớp."},
    ])
    for col, count in invalid_scores.items():
        report_rows.append({
            "cot": f"Điểm không hợp lệ: {col}",
            "so_gia_tri_thieu_goc": count,
            "ty_le_thieu_goc_pct": round(count / max(original_rows, 1) * 100, 3),
            "xu_ly": "Điểm ngoài [0,10] được chuyển thành thiếu.",
        })

    report = pd.DataFrame(report_rows)
    report.attrs["original_rows"] = original_rows
    report.attrs["missing_key_rows"] = missing_key_rows
    report.attrs["duplicate_rows"] = duplicate_rows
    report.attrs["exact_duplicate_rows"] = exact_duplicate_rows
    report.attrs["invalid_score_rows"] = invalid_score_rows
    report.attrs["missing_final_grade_rows"] = missing_final_grade_rows
    report.attrs["mismatched_class_count"] = mismatched_class_count
    report.attrs["mismatched_row_count"] = mismatched_row_count
    report.attrs["class_quality"] = class_quality
    report.attrs["student_meta"] = student_meta
    report.attrs["source_columns"] = source_columns
    return df, report


def make_course_features(df: pd.DataFrame):
    keys = ["Năm học", "Học kỳ", "loai_lop", "Mã môn", "Mã lớp học phần"]
    features = df.groupby(keys, dropna=False).agg(
        nhom_mon=("Nhóm môn", "first"),
        so_tin_chi=("Số TC", "first"),
        co_cau_trong_so=("Cơ cấu trọng số suy ra (CC/KTTX/Thi, %)", "first"),
        so_sinh_vien=("Mã SV", "nunique"),
        so_sinh_vien_co_diem_thi=("Thi", "count"),
        so_sinh_vien_co_diem_hp=("Điểm HP (thang 10)", "count"),
        diem_qua_trinh_tb=("diem_qua_trinh", "mean"),
        diem_thi_tb=("Thi", "mean"),
        diem_hp_tb=("Điểm HP (thang 10)", "mean"),
        diem_hp_std=("Điểm HP (thang 10)", "std"),
        so_sinh_vien_co_venh=("chenh_thi_kttx_tb", "count"),
        chenh_thi_kttx_tb=("chenh_thi_kttx_tb", "mean"),
        ty_le_dat=("Điểm HP (thang 10)", lambda s: (s.dropna() >= PASSING_SCORE).mean() if s.notna().any() else np.nan),
        ty_le_diem_A=("Điểm HP (thang 10)", lambda s: (s.dropna() >= 8.5).mean() if s.notna().any() else np.nan),
    ).reset_index()
    rate_columns = ["ty_le_dat", "ty_le_diem_A"]
    features[rate_columns] *= 100
    features["diem_hp_std"] = features["diem_hp_std"].fillna(0)
    return features


def make_prediction_dataset(df: pd.DataFrame):
    """Build supervised rows using only information available before each term."""
    data = df.copy()
    data["nam_bat_dau"] = pd.to_numeric(data["Năm học"].astype(str).str[:4], errors="coerce")
    data["term_order"] = data["nam_bat_dau"] * 10 + pd.to_numeric(data["Học kỳ"], errors="coerce")
    data["credit_weight"] = pd.to_numeric(data["Số TC"], errors="coerce")
    data.loc[data["credit_weight"] <= 0, "credit_weight"] = np.nan
    data["credit_weight"] = data["credit_weight"].fillna(1)
    grade = data["Điểm HP (thang 10)"]
    data["weighted_grade"] = grade * data["credit_weight"]
    data["graded_credits"] = data["credit_weight"].where(grade.notna(), 0)
    data["graded_course_count"] = grade.notna().astype(int)
    data["passed_count"] = (grade >= PASSING_SCORE).fillna(False).astype(int)

    term = data.groupby(["Mã SV", "term_order"], as_index=False, dropna=False).agg(
        weighted_grade=("weighted_grade", "sum"),
        graded_credits=("graded_credits", "sum"),
        graded_course_count=("graded_course_count", "sum"),
        passed_count=("passed_count", "sum"),
    ).sort_values(["Mã SV", "term_order"])
    term["gpa_term"] = term["weighted_grade"] / term["graded_credits"].replace(0, np.nan)
    by_student = term.groupby("Mã SV", sort=False)
    term["prior_weighted_grade"] = by_student["weighted_grade"].cumsum() - term["weighted_grade"]
    term["prior_graded_credits"] = by_student["graded_credits"].cumsum() - term["graded_credits"]
    term["prior_graded_course_count"] = by_student["graded_course_count"].cumsum() - term["graded_course_count"]
    term["prior_passed_count"] = by_student["passed_count"].cumsum() - term["passed_count"]
    term["prior_gpa_credit_weighted"] = (
        term["prior_weighted_grade"] / term["prior_graded_credits"].replace(0, np.nan)
    )
    term["prior_pass_rate"] = (
        100 * term["prior_passed_count"] / term["prior_graded_course_count"].replace(0, np.nan)
    )
    term["prior_gpa_last_term"] = by_student["gpa_term"].transform(lambda values: values.ffill().shift())
    history = term[[
        "Mã SV", "term_order", "prior_gpa_credit_weighted", "prior_gpa_last_term",
        "prior_graded_course_count", "prior_graded_credits", "prior_pass_rate",
    ]]

    same_course = data.groupby(["Mã SV", "Mã môn", "term_order"], as_index=False, dropna=False).agg(
        weighted_grade=("weighted_grade", "sum"),
        graded_credits=("graded_credits", "sum"),
        graded_course_count=("graded_course_count", "sum"),
    ).sort_values(["Mã SV", "Mã môn", "term_order"])
    by_student_course = same_course.groupby(["Mã SV", "Mã môn"], sort=False)
    same_course["prior_same_course_weighted_grade"] = (
        by_student_course["weighted_grade"].cumsum() - same_course["weighted_grade"]
    )
    same_course["prior_same_course_credits"] = (
        by_student_course["graded_credits"].cumsum() - same_course["graded_credits"]
    )
    same_course["prior_same_course_count"] = (
        by_student_course["graded_course_count"].cumsum() - same_course["graded_course_count"]
    )
    same_course["prior_same_course_gpa"] = (
        same_course["prior_same_course_weighted_grade"]
        / same_course["prior_same_course_credits"].replace(0, np.nan)
    )

    result = data.merge(history, on=["Mã SV", "term_order"], how="left")
    result = result.merge(
        same_course[["Mã SV", "Mã môn", "term_order", "prior_same_course_count", "prior_same_course_gpa"]],
        on=["Mã SV", "Mã môn", "term_order"],
        how="left",
    )
    result["co_du_lieu_lich_su"] = result["prior_graded_course_count"].gt(0).astype(int)
    prediction_columns = [
        "Mã SV", "Năm học", "Học kỳ", "term_order", "Mã môn", "Mã lớp học phần", "loai_lop",
        "Nhóm môn", "Số TC", "Khóa SV", "Khoa của SV", "prior_gpa_credit_weighted",
        "prior_gpa_last_term", "prior_graded_course_count", "prior_graded_credits",
        "prior_pass_rate", "prior_same_course_count", "prior_same_course_gpa",
        "co_du_lieu_lich_su", "Điểm HP (thang 10)",
    ]
    result = result.loc[result["Điểm HP (thang 10)"].notna(), prediction_columns].copy()
    return result.rename(columns={"Điểm HP (thang 10)": "target_diem_hp"})


def main():
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    clean, report = clean_data(INPUT_FILE)
    print(f"Cleaned {len(clean)} labeled rows", flush=True)
    course_features = make_course_features(clean)
    print(f"Built course features: {len(course_features)}", flush=True)
    prediction_dataset = make_prediction_dataset(clean)
    print(f"Built prediction dataset: {len(prediction_dataset)}", flush=True)
    class_quality = report.attrs["class_quality"]
    quality_columns = [
        "Năm học", "Học kỳ", "loai_lop", "Mã môn", "Mã lớp học phần",
        "ty_le_thieu_diem_lop_pct", "ty_le_thieu_diem_hp_goc_pct", "so_dong_goc_lop",
        "nhom_mon", "so_tin_chi", "co_cau_trong_so", "si_so_ghi_nhan",
    ]
    class_base = class_quality[quality_columns]
    course_features = class_base.merge(
        course_features.drop(columns=["nhom_mon", "so_tin_chi", "co_cau_trong_so"]),
        on=["Năm học", "Học kỳ", "loai_lop", "Mã môn", "Mã lớp học phần"],
        how="left",
        validate="one_to_one",
    )
    course_features["so_sinh_vien"] = course_features["so_dong_goc_lop"]
    course_features["so_sinh_vien_co_diem_thi"] = course_features["so_sinh_vien_co_diem_thi"].fillna(0).astype(int)
    course_features["so_sinh_vien_co_diem_hp"] = course_features["so_sinh_vien_co_diem_hp"].fillna(0).astype(int)
    class_anomalies = make_class_anomaly_features(course_features, prediction_dataset, class_quality)
    print(f"Scored anomalous classes: {len(class_anomalies)}", flush=True)
    adjusted_scores, model_validation, selected_model = make_adjusted_scores(
        clean, prediction_dataset, class_anomalies
    )
    print(f"Adjusted scores with {selected_model or 'no available'} model", flush=True)
    student_features, _ = make_student_tci(adjusted_scores)
    print(f"Computed TCI for {student_features['TCI'].notna().sum()} students", flush=True)
    student_meta = report.attrs["student_meta"]
    student_features = student_meta.merge(
        student_features,
        left_on="Mã SV",
        right_on="Mã SV",
        how="left",
        validate="one_to_one",
    )
    student_features["Khóa SV"] = student_features["Khóa SV"].combine_first(student_features["khoa_sv"])
    student_features["Khoa của SV"] = student_features["Khoa của SV"].combine_first(student_features["khoa_faculty"])
    student_features = student_features.drop(columns=["khoa_sv", "khoa_faculty"])
    student_features["so_mon"] = student_features["so_mon"].fillna(0).astype(int)
    student_features["so_hoc_ky"] = student_features["so_hoc_ky"].fillna(0).astype(int)
    student_features["Phan_cap"] = student_features["Phan_cap"].fillna("INSUFFICIENT_HISTORY")
    course_columns = [
        "Năm học", "Học kỳ", "loai_lop", "Mã môn", "Mã lớp học phần", "nhom_mon",
        "so_tin_chi", "co_cau_trong_so", "si_so_ghi_nhan", "so_sinh_vien",
        "so_sinh_vien_co_diem_thi", "so_sinh_vien_co_diem_hp", "diem_qua_trinh_tb",
        "diem_thi_tb", "diem_hp_tb", "diem_hp_std", "ty_le_dat", "ty_le_diem_A",
        "so_sinh_vien_co_venh", "chenh_thi_kttx_tb", "ty_le_thieu_diem_lop_pct",
        "ty_le_thieu_diem_hp_goc_pct", "so_lop_cung_hoc_phan", "z_hieu_chinh",
        "S1_lech_trung_binh", "S2_qua_deu_hoac_nhieu_A", "tuong_quan_nang_luc_nen",
        "tuong_quan_trung_vi_mat_bang", "S3_khong_khop_nang_luc_nen", "S3_thieu_du_lieu",
        "Anomaly_Score", "co_mau_nho", "thieu_tren_30_phan_tram", "du_mat_bang_so_sanh",
        "nghi_van_theo_cong_thuc", "Isolation_Forest_nghi_van", "nghi_van", "nghi_van_kep",
        "Nhan_bat_thuong", "Anomaly_Rank", "ly_do_can_xem_xet",
    ]
    course_output = class_anomalies[course_columns].copy()
    course_output = course_output.sort_values(
        ["nghi_van", "Anomaly_Rank", "Anomaly_Score"],
        ascending=[False, True, False],
        na_position="last",
    )
    adjusted_columns = [
        "Mã SV", "Năm học", "Học kỳ", "Mã môn", "Mã lớp học phần", "loai_lop",
        "diem_hp_goc", "diem_chu_goc", "diem_he4_goc", "Adjusted_Score",
        "diem_chu_dieu_chinh", "diem_he4_dieu_chinh", "alpha_chiet_khau", "Anomaly_Score", "nghi_van",
        "Nhan_bat_thuong", "da_chuan_hoa_z", "khong_co_mat_bang_chuan_hoa", "diem_du_doan",
        "khoang_duoi_95", "khoang_tren_95", "REVIEW_REQUIRED",
    ]
    adjusted_output = adjusted_scores[adjusted_columns].copy()

    quality_report = report.rename(columns={
        "cot": "chi_tieu",
        "so_gia_tri_thieu_goc": "so_luong",
        "ty_le_thieu_goc_pct": "gia_tri",
        "xu_ly": "ghi_chu",
    }).copy()
    quality_report.insert(0, "nhom_bao_cao", "chat_luong_du_lieu")
    if model_validation.empty:
        model_rows = [{
            "nhom_bao_cao": "kiem_dinh_model",
            "chi_tieu": "trang_thai",
            "so_luong": 0,
            "gia_tri": np.nan,
            "ghi_chu": "Không đủ mẫu train/test để kiểm định theo thời gian.",
        }]
    else:
        model_rows = [{
            "nhom_bao_cao": "kiem_dinh_model",
            "chi_tieu": f"RMSE_{row['mo_hinh']}",
            "so_luong": int(row["so_mau_test"]),
            "gia_tri": float(row["RMSE"]),
            "ghi_chu": (
                f"ky_test={row['ky_test']}; MAE={row['MAE']:.4f}; R2={row['R2']:.4f}; "
                f"duoc_chon={bool(row['mo_hinh_duoc_chon'])}"
            ),
        } for _, row in model_validation.iterrows()]
    quality_report = pd.concat([quality_report, pd.DataFrame(model_rows)], ignore_index=True)

    clean[report.attrs["source_columns"]].to_csv(CLEAN_FILE, index=False)
    course_output.to_csv(COURSE_FEATURE_FILE, index=False)
    student_features.to_csv(STUDENT_FEATURE_FILE, index=False)
    quality_report.to_csv(QUALITY_FILE, index=False)
    adjusted_output.to_csv(ADJUSTED_SCORE_FILE, index=False)

    print(f"Rows: {len(clean)} (input {report.attrs['original_rows']}; missing-key rows removed {report.attrs['missing_key_rows']}; exact duplicates removed {report.attrs['exact_duplicate_rows']}; invalid-score rows removed {report.attrs['invalid_score_rows']}; missing-final-grade rows removed {report.attrs['missing_final_grade_rows']}; duplicate keys removed {report.attrs['duplicate_rows']})")
    print(f"Clean data: {CLEAN_FILE}")
    print(f"Course features and anomaly flags: {len(course_output)} rows -> {COURSE_FEATURE_FILE}")
    print(f"Student TCI features: {len(student_features)} rows -> {STUDENT_FEATURE_FILE}")
    print(f"Prediction samples used internally: {len(prediction_dataset)}")
    print(f"Quality and model report: {QUALITY_FILE}")
    print(f"Adjusted score review table: {len(adjusted_output)} rows -> {ADJUSTED_SCORE_FILE}")
    print(f"Model selected by temporal validation: {selected_model or 'none'}")
    print("\nCourse feature sample:")
    print(course_features.head(3).to_string(index=False))
    print("\nStudent feature sample:")
    print(student_features.head(3).to_string(index=False))


if __name__ == "__main__":
    main()
