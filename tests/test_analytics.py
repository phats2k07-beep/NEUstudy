import unittest
from pathlib import Path
import shutil
import subprocess
from unittest.mock import patch

import numpy as np
import pandas as pd
from fastapi.testclient import TestClient

from advanced_analysis import (
    CLASS_KEYS,
    make_class_anomaly_features,
    make_student_features,
    score_to_grade_point,
    score_to_letter,
)


class AnalyticsTests(unittest.TestCase):
    def test_requested_gpa_bands_and_boundary_convention(self):
        scores = pd.Series([4.49, 4.5, 5.49, 5.5, 5.99, 6.0, 6.49, 6.5, 6.99, 7.0, 7.99, 8.0, 8.49, 8.5, 8.99, 9.0, 10.0])
        self.assertEqual(
            score_to_grade_point(scores).tolist(),
            [0, 1, 1, 1.5, 1.5, 2, 2, 2.5, 2.5, 3, 3, 3.5, 3.5, 4, 4, 4, 4],
        )
        self.assertEqual(
            score_to_letter(scores).tolist(),
            ["F", "D", "D", "D+", "D+", "C", "C", "C+", "C+", "B", "B", "B+", "B+", "A", "A", "A+", "A+"],
        )

    def make_class_inputs(self):
        classes = []
        predictions = []
        quality = []
        profiles = [("L001", 5.0, 1.0, 0.10, 15), ("L002", 5.2, 1.1, 0.15, 15), ("L003", 9.0, 0.2, 0.80, 15), ("L004", 4.8, 1.0, 0.10, 14)]
        for section, mean, std, a_rate, size in profiles:
            keys = {"Năm học": "2024-2025", "Học kỳ": 1, "loai_lop": "He_thuong", "Mã môn": "M001", "Mã lớp học phần": section}
            classes.append({**keys, "so_sinh_vien": size, "diem_hp_tb": mean, "diem_hp_std": std, "ty_le_diem_A": a_rate * 100})
            quality.append({**keys, "ty_le_thieu_diem_lop_pct": 5.0})
            for student in range(size):
                prior = 3.0 + student / 10
                predictions.append({**keys, "Mã SV": f"{section}_{student}", "target_diem_hp": mean + (student - size / 2) / 10, "prior_gpa_credit_weighted": prior})
        return pd.DataFrame(classes), pd.DataFrame(predictions), pd.DataFrame(quality)

    def test_anomaly_score_is_bounded_and_small_class_is_not_scored(self):
        course, prediction, quality = self.make_class_inputs()
        scored = make_class_anomaly_features(course, prediction, quality)
        finite = scored["Anomaly_Score"].dropna()
        self.assertTrue(finite.between(0, 1).all())
        small = scored.loc[scored["Mã lớp học phần"].eq("L004")].iloc[0]
        self.assertTrue(bool(small["co_mau_nho"]))
        self.assertTrue(pd.isna(small["Anomaly_Score"]))
        self.assertFalse(bool(small["nghi_van"]))
        self.assertTrue(scored.loc[scored["Mã lớp học phần"].eq("L003"), "Anomaly_Score"].iloc[0] > 0.3)

    def test_tci_requires_course_and_term_history(self):
        rows = []
        for course in range(6):
            for term_index, term in enumerate((20231, 20232, 20241)):
                rows.append({
                    "Mã SV": "S001", "Khóa SV": "K60", "Khoa của SV": "KH01",
                    "Mã môn": f"M{course:03}", "term_order": term, "Số TC": 3,
                    "diem_hp_goc": 7.0 + course / 10 + term_index / 10,
                    "Adjusted_Score": 7.0 + course / 10 + term_index / 10,
                    "alpha_chiet_khau": 1.0, "Anomaly_Score": 0.0,
                    "REVIEW_REQUIRED": False,
                })
        students, term_features = make_student_features(pd.DataFrame(rows))
        student = students.iloc[0]
        self.assertEqual(len(term_features), 3)
        self.assertAlmostEqual(student["GPA_goc"], 3.0)
        self.assertAlmostEqual(student["Normalized_GPA"], 3.0)
        self.assertTrue(pd.notna(student["TCI"]))
        self.assertGreaterEqual(student["TCI"], 0)
        self.assertLessEqual(student["TCI"], 4)
        self.assertIn(student["Phan_cap"], {"Advanced", "Proficient", "Intermediate", "At-Risk"})

    def test_current_api_reads_project_summary(self):
        import platform_api
        with TestClient(platform_api.app) as client:
            self.assertEqual(client.get("/api/health").status_code, 200)
            summary = client.get("/api/summary").json()
            self.assertGreater(summary["classes"], 0)
            self.assertGreater(summary["students"], 0)
            self.assertIn("distribution", summary)
            self.assertEqual(client.get("/api/classes?page_size=5").status_code, 200)
            self.assertEqual(client.get("/api/students?page_size=5").status_code, 200)
            self.assertTrue(client.get("/api/timetable/summary").json()["available"])

    def test_analyze_returns_classification_endpoints(self):
        import platform_api

        original_active_dir = platform_api._active_dir
        original_upload_dir = platform_api._active_upload_dir
        csv_content = (
            "Năm học,Học kỳ,Mã môn,Mã lớp học phần,Mã SV,Điểm HP (thang 10)\n"
            "2024-2025,1,M001,L001,S001,8.0\n"
        )
        upload_dir = None
        try:
            with TestClient(platform_api.app) as client:
                with patch(
                    "platform_api.subprocess.run",
                    return_value=subprocess.CompletedProcess([], 0, "pipeline ok", ""),
                ):
                    response = client.post(
                        "/api/analyze",
                        files={"file": ("scores.csv", csv_content, "text/csv")},
                    )
            upload_dir = platform_api._active_upload_dir
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["results"], {
                "summary": "/api/summary",
                "classes": "/api/classes",
                "students": "/api/students",
            })
        finally:
            platform_api._active_dir = original_active_dir
            platform_api._active_upload_dir = original_upload_dir
            if upload_dir and upload_dir != original_upload_dir:
                shutil.rmtree(upload_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
