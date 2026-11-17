"""Class anomaly checks, score adjustment, and student TCI outputs."""

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import IsolationForest, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


CLASS_KEYS = ["Năm học", "Học kỳ", "loai_lop", "Mã môn", "Mã lớp học phần"]
PEER_KEYS = ["Năm học", "Học kỳ", "loai_lop", "Mã môn"]
GPA_BANDS = [
    (9.0, 10.0, 4.0, "A+"),
    (8.5, 9.0, 4.0, "A"),
    (8.0, 8.5, 3.5, "B+"),
    (7.0, 8.0, 3.0, "B"),
    (6.5, 7.0, 2.5, "C+"),
    (6.0, 6.5, 2.0, "C"),
    (5.5, 6.0, 1.5, "D+"),
    (4.5, 5.5, 1.0, "D"),
]


def score_to_grade_point(scores):
    """Map 0-10 score bands to the requested letter-grade GPA scale."""
    values = pd.to_numeric(scores, errors="coerce")
    result = pd.Series(np.nan, index=values.index, dtype=float)
    result.loc[values.lt(4.5)] = 0.0
    for lower, upper, points, _ in reversed(GPA_BANDS):
        mask = values.ge(lower) & values.lt(upper)
        result.loc[mask] = points
    result.loc[values.eq(10.0)] = 4.0
    return result


def score_to_letter(scores):
    """Map scores to letter grades using lower-inclusive, upper-exclusive bands."""
    values = pd.to_numeric(scores, errors="coerce")
    result = pd.Series(pd.NA, index=values.index, dtype="string")
    result.loc[values.lt(4.5)] = "F"
    for lower, upper, _, letter in reversed(GPA_BANDS):
        result.loc[values.ge(lower) & values.lt(upper)] = letter
    result.loc[values.eq(10.0)] = "A+"
    return result


PROJECT_TYPE = "Do_an_thuc_tap_khoa_luan"


def _safe_corr(frame):
    valid = frame[["target_diem_hp", "prior_gpa_credit_weighted"]].dropna()
    if len(valid) < 5 or valid["prior_gpa_credit_weighted"].nunique() < 2:
        return np.nan
    return valid["target_diem_hp"].corr(valid["prior_gpa_credit_weighted"])


def make_class_anomaly_features(course_features, prediction_dataset, class_quality):
    """Score class-level anomalies against parallel sections of the same course."""
    result = course_features.copy()
    if class_quality is not None and not class_quality.empty:
        quality_columns = [
            column for column in class_quality.columns
            if column in CLASS_KEYS or column not in result.columns
        ]
        result = result.merge(
            class_quality[quality_columns], on=CLASS_KEYS, how="left", validate="one_to_one"
        )
    elif "ty_le_thieu_diem_lop_pct" not in result:
        result["ty_le_thieu_diem_lop_pct"] = np.nan
    result["ty_le_diem_A"] = result["ty_le_diem_A"] / 100

    peer = result.groupby(PEER_KEYS, dropna=False)
    result["so_lop_cung_hoc_phan"] = peer["diem_hp_tb"].transform("count")
    peer_median = peer["diem_hp_tb"].transform("median")
    peer_mad = peer["diem_hp_tb"].transform(
        lambda values: (values - values.median()).abs().median()
    )
    grade_delta = result["diem_hp_tb"] - peer_median
    result["z_hieu_chinh"] = 0.6745 * grade_delta / peer_mad.replace(0, np.nan)
    zero_mad_outlier = peer_mad.eq(0) & grade_delta.ne(0)
    result.loc[zero_mad_outlier, "z_hieu_chinh"] = np.sign(grade_delta.loc[zero_mad_outlier]) * np.inf
    result.loc[peer_mad.eq(0) & grade_delta.eq(0), "z_hieu_chinh"] = 0
    result["S1_lech_trung_binh"] = (result["z_hieu_chinh"].abs().clip(upper=6) / 6)

    peer_sd_median = peer["diem_hp_std"].transform("median")
    too_consistent = (1 - result["diem_hp_std"] / peer_sd_median.replace(0, np.nan)).clip(0, 1)
    excess_a = ((result["ty_le_diem_A"] - 0.60) / 0.40).clip(0, 1)
    result["S2_qua_deu_hoac_nhieu_A"] = pd.concat(
        [too_consistent.fillna(0), excess_a.fillna(0)], axis=1
    ).max(axis=1)

    correlations = prediction_dataset.groupby(CLASS_KEYS, dropna=False).apply(
        _safe_corr, include_groups=False
    ).rename("tuong_quan_nang_luc_nen").reset_index()
    result = result.merge(correlations, on=CLASS_KEYS, how="left", validate="one_to_one")
    result["tuong_quan_trung_vi_mat_bang"] = result.groupby(
        PEER_KEYS, dropna=False
    )["tuong_quan_nang_luc_nen"].transform("median")
    valid_r = result["tuong_quan_trung_vi_mat_bang"].gt(0)
    result["S3_khong_khop_nang_luc_nen"] = (
        (result["tuong_quan_trung_vi_mat_bang"] - result["tuong_quan_nang_luc_nen"])
        / result["tuong_quan_trung_vi_mat_bang"].where(valid_r)
    ).clip(0, 1)
    result["S3_thieu_du_lieu"] = result["S3_khong_khop_nang_luc_nen"].isna()
    result["S3_khong_khop_nang_luc_nen"] = result["S3_khong_khop_nang_luc_nen"].fillna(0)
    eligible_for_scoring = (
        result["so_lop_cung_hoc_phan"].ge(2)
        & result["so_sinh_vien"].ge(15)
        & result["ty_le_thieu_diem_lop_pct"].le(30)
        & result["loai_lop"].ne(PROJECT_TYPE)
    )
    result["Anomaly_Score"] = (
        0.4 * result["S1_lech_trung_binh"]
        + 0.3 * result["S2_qua_deu_hoac_nhieu_A"]
        + 0.3 * result["S3_khong_khop_nang_luc_nen"]
    ).where(eligible_for_scoring)

    result["co_mau_nho"] = result["so_sinh_vien"] < 15
    result["thieu_tren_30_phan_tram"] = result["ty_le_thieu_diem_lop_pct"].gt(30)
    result["du_mat_bang_so_sanh"] = result["so_lop_cung_hoc_phan"].ge(5)

    robust_z = result["z_hieu_chinh"]
    result["nghi_van_theo_cong_thuc"] = (
        eligible_for_scoring
        & ((result["Anomaly_Score"] >= 0.30) | (robust_z.abs() > 3.5))
    )

    model_columns = [
        "Anomaly_Score", "S1_lech_trung_binh", "S2_qua_deu_hoac_nhieu_A",
        "S3_khong_khop_nang_luc_nen", "z_hieu_chinh", "diem_hp_std", "ty_le_diem_A",
        "tuong_quan_nang_luc_nen",
    ]
    eligible = eligible_for_scoring & result["du_mat_bang_so_sanh"]
    result["Isolation_Forest_nghi_van"] = False
    if int(eligible.sum()) >= 10:
        from sklearn.ensemble import IsolationForest

        values = result.loc[eligible, model_columns].replace([np.inf, -np.inf], np.nan)
        imputer = SimpleImputer(strategy="median", keep_empty_features=True)
        transformed = imputer.fit_transform(values)
        detector = IsolationForest(random_state=42, contamination="auto", n_estimators=300)
        result.loc[eligible, "Isolation_Forest_nghi_van"] = detector.fit_predict(transformed) == -1

    result["nghi_van"] = result["nghi_van_theo_cong_thuc"] | result["Isolation_Forest_nghi_van"]
    result["nghi_van_kep"] = result["nghi_van_theo_cong_thuc"] & result["Isolation_Forest_nghi_van"]
    result["Nhan_bat_thuong"] = np.select(
        [
            eligible_for_scoring & robust_z.gt(3.5),
            eligible_for_scoring & robust_z.lt(-3.5),
            result["nghi_van"],
        ],
        ["HIGH_INFLATION", "UNUSUALLY_STEEP", "SUSPICIOUS_DISTRIBUTION"],
        default="NOT_FLAGGED",
    )
    result["Anomaly_Rank"] = (
        result["Anomaly_Score"].where(result["nghi_van"]).rank(method="dense", ascending=False).astype("Int64")
    )
    result["ly_do_can_xem_xet"] = np.select(
        [result["co_mau_nho"] & result["thieu_tren_30_phan_tram"], result["co_mau_nho"], result["thieu_tren_30_phan_tram"]],
        ["mau_nho_va_thieu_du_lieu", "mau_nho_duoi_15_sinh_vien", "thieu_tren_30_phan_tram_du_lieu"],
        default="",
    )
    return result


def _make_regression_pipeline(model_name, numeric_columns, categorical_columns):
    numeric = Pipeline([
        ("imputer", SimpleImputer(strategy="median", add_indicator=True)),
        ("scale", StandardScaler()),
    ])
    categorical = Pipeline([
        ("imputer", SimpleImputer(strategy="most_frequent")),
        ("encode", OneHotEncoder(handle_unknown="ignore")),
    ])
    preprocessing = ColumnTransformer([
        ("numeric", numeric, numeric_columns),
        ("categorical", categorical, categorical_columns),
    ])
    estimator = (
        LinearRegression()
        if model_name == "LinearRegression"
        else RandomForestRegressor(n_estimators=150, min_samples_leaf=3, random_state=42, n_jobs=-1)
    )
    return Pipeline([("preprocess", preprocessing), ("model", estimator)])


def make_adjusted_scores(clean, prediction_dataset, class_anomalies):
    """Normalize flagged classes, evaluate temporal models, and review intervals."""
    class_status = class_anomalies[CLASS_KEYS + ["nghi_van", "Anomaly_Score"]]
    class_status = class_status.merge(
        class_anomalies[CLASS_KEYS + ["Nhan_bat_thuong"]],
        on=CLASS_KEYS,
        how="left",
        validate="one_to_one",
    )
    data = prediction_dataset.merge(class_status, on=CLASS_KEYS, how="left", validate="many_to_one")
    data["nghi_van"] = data["nghi_van"].fillna(False)
    data["Anomaly_Score"] = data["Anomaly_Score"].fillna(0)
    data["diem_hp_goc"] = data["target_diem_hp"]
    data["diem_hp_dieu_chinh"] = data["target_diem_hp"]
    data["da_chuan_hoa_z"] = False
    data["khong_co_mat_bang_chuan_hoa"] = False

    ordinary = data.loc[~data["nghi_van"] & data["loai_lop"].ne(PROJECT_TYPE)]
    reference = ordinary.groupby(PEER_KEYS, dropna=False)["target_diem_hp"].agg(
        diem_tb_mat_bang="mean", diem_sd_mat_bang="std", so_diem_mat_bang="count"
    ).reset_index()
    data = data.merge(reference, on=PEER_KEYS, how="left", validate="many_to_one")
    class_stats = data.groupby(CLASS_KEYS, dropna=False)["target_diem_hp"].agg(
        diem_tb_lop="mean", diem_sd_lop="std"
    ).reset_index()
    data = data.merge(class_stats, on=CLASS_KEYS, how="left", validate="many_to_one")
    can_normalize = (
        data["nghi_van"]
        & data["loai_lop"].ne(PROJECT_TYPE)
        & data["diem_sd_lop"].gt(0)
        & data["diem_sd_mat_bang"].gt(0)
        & data["so_diem_mat_bang"].ge(5)
    )
    normalized = data["diem_tb_mat_bang"] + (
        (data["diem_hp_goc"] - data["diem_tb_lop"]) / data["diem_sd_lop"]
    ) * data["diem_sd_mat_bang"]
    data.loc[can_normalize, "diem_hp_dieu_chinh"] = normalized.loc[can_normalize].clip(0, 10)
    data["da_chuan_hoa_z"] = can_normalize
    data["khong_co_mat_bang_chuan_hoa"] = data["nghi_van"] & ~can_normalize

    numeric_columns = [
        "term_order", "Số TC", "prior_gpa_credit_weighted", "prior_gpa_last_term",
        "prior_graded_course_count", "prior_graded_credits", "prior_pass_rate",
        "prior_same_course_count", "prior_same_course_gpa",
    ]
    categorical_columns = ["Mã môn", "loai_lop", "Khóa SV", "Khoa của SV"]
    excluded = set(class_anomalies.loc[class_anomalies["nghi_van"], CLASS_KEYS].itertuples(index=False, name=None))
    keys = list(data[CLASS_KEYS].itertuples(index=False, name=None))
    data["lop_nghi_van"] = [key in excluded for key in keys]
    train_mask = ~data["lop_nghi_van"] & data["loai_lop"].ne(PROJECT_TYPE)
    terms = sorted(data.loc[train_mask, "term_order"].dropna().unique())
    evaluations = []
    selected_name = None
    interval_rmse = np.nan

    if len(terms) >= 2:
        test_year = int(max(terms) // 10)
        term_year = data["term_order"] // 10
        train = data.loc[train_mask & term_year.lt(test_year)]
        test = data.loc[train_mask & term_year.eq(test_year)]
        if len(train) >= 30 and len(test) >= 10:
            baseline_prediction = data.loc[test.index, "prior_gpa_credit_weighted"].fillna(
                train["target_diem_hp"].mean()
            )
            evaluations.append({
                "mo_hinh": "Baseline_prior_GPA",
                "ky_test": f"nam_hoc_{test_year}",
                "so_mau_train": len(train),
                "so_mau_test": len(test),
                "RMSE": float(np.sqrt(mean_squared_error(test["target_diem_hp"], baseline_prediction))),
                "MAE": float(mean_absolute_error(test["target_diem_hp"], baseline_prediction)),
                "R2": float(r2_score(test["target_diem_hp"], baseline_prediction)),
            })
            for model_name in ["LinearRegression", "RandomForest"]:
                pipeline = _make_regression_pipeline(model_name, numeric_columns, categorical_columns)
                pipeline.fit(train[numeric_columns + categorical_columns], train["target_diem_hp"])
                prediction = pipeline.predict(test[numeric_columns + categorical_columns])
                rmse = float(np.sqrt(mean_squared_error(test["target_diem_hp"], prediction)))
                evaluations.append({
                    "mo_hinh": model_name,
                    "ky_test": f"nam_hoc_{test_year}",
                    "so_mau_train": len(train),
                    "so_mau_test": len(test),
                    "RMSE": rmse,
                    "MAE": float(mean_absolute_error(test["target_diem_hp"], prediction)),
                    "R2": float(r2_score(test["target_diem_hp"], prediction)),
                })
            ml_evaluations = [row for row in evaluations if row["mo_hinh"] != "Baseline_prior_GPA"]
            selected_name = min(ml_evaluations, key=lambda row: row["RMSE"])["mo_hinh"]
            interval_rmse = next(row["RMSE"] for row in ml_evaluations if row["mo_hinh"] == selected_name)

    data["diem_du_doan"] = np.nan
    data["khoang_duoi_95"] = np.nan
    data["khoang_tren_95"] = np.nan
    if selected_name is not None and int(train_mask.sum()) >= 30:
        final_model = _make_regression_pipeline(selected_name, numeric_columns, categorical_columns)
        final_model.fit(data.loc[train_mask, numeric_columns + categorical_columns], data.loc[train_mask, "target_diem_hp"])
        data["diem_du_doan"] = final_model.predict(data[numeric_columns + categorical_columns])
        data["khoang_duoi_95"] = (data["diem_du_doan"] - 1.96 * interval_rmse).clip(0, 10)
        data["khoang_tren_95"] = (data["diem_du_doan"] + 1.96 * interval_rmse).clip(0, 10)

    data["REVIEW_REQUIRED"] = False
    has_interval = data["khoang_duoi_95"].notna() & data["khoang_tren_95"].notna()
    outside = data["nghi_van"] & has_interval & (
        data["diem_hp_dieu_chinh"].lt(data["khoang_duoi_95"])
        | data["diem_hp_dieu_chinh"].gt(data["khoang_tren_95"])
    )
    data.loc[outside, "REVIEW_REQUIRED"] = True
    data.loc[outside, "diem_hp_dieu_chinh"] = data.loc[outside, "diem_hp_dieu_chinh"].clip(
        lower=data.loc[outside, "khoang_duoi_95"], upper=data.loc[outside, "khoang_tren_95"]
    )
    data["Adjusted_Score"] = data["diem_hp_dieu_chinh"]
    data["diem_he4_goc"] = score_to_grade_point(data["diem_hp_goc"])
    data["diem_he4_dieu_chinh"] = score_to_grade_point(data["Adjusted_Score"])
    data["diem_chu_goc"] = score_to_letter(data["diem_hp_goc"])
    data["diem_chu_dieu_chinh"] = score_to_letter(data["Adjusted_Score"])
    data["alpha_chiet_khau"] = np.where(
        data["nghi_van"],
        1 - 0.8 * data["Anomaly_Score"].fillna(0).clip(0, 1),
        1.0,
    )

    metrics = pd.DataFrame(evaluations)
    if not metrics.empty:
        metrics["mo_hinh_duoc_chon"] = metrics["mo_hinh"].eq(selected_name)
    return data, metrics, selected_name


def make_student_features(adjusted_scores):
    """Produce one explainable TCI row per student and retain term detail separately."""
    data = adjusted_scores.copy()
    if "diem_he4_goc" not in data:
        data["diem_he4_goc"] = score_to_grade_point(data["diem_hp_goc"])
    if "diem_he4_dieu_chinh" not in data:
        data["diem_he4_dieu_chinh"] = score_to_grade_point(data["Adjusted_Score"])
    if "diem_chu_goc" not in data:
        data["diem_chu_goc"] = score_to_letter(data["diem_hp_goc"])
    if "diem_chu_dieu_chinh" not in data:
        data["diem_chu_dieu_chinh"] = score_to_letter(data["Adjusted_Score"])
    data["diem_thang_4_goc"] = data["diem_he4_goc"]
    data["diem_thang_4_dieu_chinh"] = data["diem_he4_dieu_chinh"]
    data["diem_thang_4_chiet_khau"] = data["diem_thang_4_dieu_chinh"] * data["alpha_chiet_khau"]
    data["tin_chi_tinh"] = pd.to_numeric(data["Số TC"], errors="coerce").where(lambda values: values.gt(0), 1)

    data["term_order"] = pd.to_numeric(data["term_order"], errors="coerce")
    unique_terms = {term: index for index, term in enumerate(sorted(data["term_order"].dropna().unique()))}
    data["term_index"] = data["term_order"].map(unique_terms)
    data["goc_nhan_tin_chi"] = data["diem_thang_4_goc"] * data["tin_chi_tinh"]
    data["chuan_nhan_tin_chi"] = data["diem_thang_4_dieu_chinh"] * data["tin_chi_tinh"] * data["alpha_chiet_khau"]
    data["tin_chi_chiet_khau"] = data["tin_chi_tinh"] * data["alpha_chiet_khau"]
    term_features = data.groupby(["Mã SV", "term_order"], dropna=False).agg(
        term_index=("term_index", "first"),
        weighted_grade=("chuan_nhan_tin_chi", "sum"),
        weighted_credits=("tin_chi_chiet_khau", "sum"),
    ).reset_index()
    term_features["GPA_ky_chuan_hoa"] = (
        term_features["weighted_grade"] / term_features["weighted_credits"].replace(0, np.nan)
    )
    term_group = term_features.groupby("Mã SV", sort=False)
    term_features["_x_centered"] = term_features["term_index"] - term_group["term_index"].transform("mean")
    term_features["_y_centered"] = term_features["GPA_ky_chuan_hoa"] - term_group["GPA_ky_chuan_hoa"].transform("mean")
    term_features["_xy"] = term_features["_x_centered"] * term_features["_y_centered"]
    term_features["_xx"] = term_features["_x_centered"] ** 2
    slopes = term_features.groupby("Mã SV").agg(
        slope_numerator=("_xy", "sum"), slope_denominator=("_xx", "sum")
    )
    slopes["toc_do_tang_GPA_moi_ky"] = slopes["slope_numerator"] / slopes["slope_denominator"].replace(0, np.nan)

    students = data.groupby("Mã SV", dropna=False).agg(
        khoa_sv=("Khóa SV", "first"),
        khoa_faculty=("Khoa của SV", "first"),
        so_mon=("Mã môn", "nunique"),
        so_hoc_ky=("term_order", "nunique"),
        raw_weighted_grade=("goc_nhan_tin_chi", "sum"),
        total_credits=("tin_chi_tinh", "sum"),
        adjusted_weighted_grade=("chuan_nhan_tin_chi", "sum"),
        discounted_credits=("tin_chi_chiet_khau", "sum"),
        grade_std=("diem_thang_4_dieu_chinh", lambda values: values.std(ddof=0)),
    ).reset_index()
    students["GPA_goc"] = students["raw_weighted_grade"] / students["total_credits"].replace(0, np.nan)
    students["Normalized_GPA"] = students["adjusted_weighted_grade"] / students["discounted_credits"].replace(0, np.nan)
    students["Consistency"] = (4 * (1 - students["grade_std"] / 2)).clip(0, 4)
    students = students.merge(slopes[["toc_do_tang_GPA_moi_ky"]], on="Mã SV", how="left", validate="one_to_one")
    students["Progress"] = (students["Normalized_GPA"] + students["toc_do_tang_GPA_moi_ky"].fillna(0)).clip(0, 4)
    enough_history = students["so_mon"].ge(5) & students["so_hoc_ky"].ge(3)
    students["TCI"] = (
        0.6 * students["Normalized_GPA"]
        + 0.2 * students["Consistency"]
        + 0.2 * students["Progress"]
    ).where(enough_history)
    students["Phan_cap"] = np.select(
        [
            ~enough_history,
            students["TCI"].ge(3.6),
            students["TCI"].ge(3.2),
            students["TCI"].ge(2.5),
        ],
        ["INSUFFICIENT_HISTORY", "Advanced", "Proficient", "Intermediate"],
        default="At-Risk",
    )

    def unique_courses(values):
        return ";".join(pd.unique(values.astype(str)))

    discounted = data.loc[data["alpha_chiet_khau"].lt(1)].groupby("Mã SV")["Mã môn"].agg(unique_courses)
    reviews = data.loc[data["REVIEW_REQUIRED"]].groupby("Mã SV")["Mã môn"].agg(unique_courses)
    students["mon_bi_chiet_khau"] = students["Mã SV"].map(discounted).astype("string").fillna("")
    students["mon_REVIEW_REQUIRED"] = students["Mã SV"].map(reviews).astype("string").fillna("")
    students["so_mon_bi_chiet_khau"] = students["mon_bi_chiet_khau"].map(lambda value: len(value.split(";")) if value else 0)
    students["so_mon_REVIEW_REQUIRED"] = students["mon_REVIEW_REQUIRED"].map(lambda value: len(value.split(";")) if value else 0)
    students = students.rename(columns={"khoa_sv": "Khóa SV", "khoa_faculty": "Khoa của SV"})
    student_columns = [
        "Mã SV", "Khóa SV", "Khoa của SV", "so_mon", "so_hoc_ky", "GPA_goc",
        "Normalized_GPA", "Consistency", "Progress", "toc_do_tang_GPA_moi_ky",
        "TCI", "Phan_cap", "so_mon_bi_chiet_khau", "mon_bi_chiet_khau",
        "so_mon_REVIEW_REQUIRED", "mon_REVIEW_REQUIRED",
    ]
    return students[student_columns], term_features[["Mã SV", "term_order", "term_index", "GPA_ky_chuan_hoa"]]