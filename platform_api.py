"""Local API and dashboard for the academic analytics prototype."""

from __future__ import annotations

import json
import io
import os
import shutil
import subprocess
import sys
import tempfile
import threading
from pathlib import Path
from typing import Optional

import pandas as pd
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

ROOT = Path(__file__).resolve().parent
DEFAULT_DATA_DIR = ROOT / "data" / "processed"
RAW_DIR = ROOT / "data" / "raw"
STATIC_DIR = ROOT / "static"
PIPELINE = ROOT / "process_lop_analysis.py"
MAX_UPLOAD_BYTES = 50 * 1024 * 1024
EXPECTED_COLUMNS = {
    "Năm học", "Học kỳ", "Mã môn", "Mã lớp học phần", "Mã SV",
    "Điểm HP (thang 10)",
}
EXPORTS = {
    "du_lieu_clean.csv",
    "course_features.csv",
    "student_features.csv",
    "adjusted_scores.csv",
    "bao_cao_clean_data.csv",
}
CLASS_FILE = "course_features.csv"
STUDENT_FILE = "student_features.csv"
ADJUSTED_FILE = "adjusted_scores.csv"

app = FastAPI(
    title="NEU Academic Integrity & True Competency Analytics",
    version="1.0.0",
    description="Local prototype API for class anomaly screening, score review, and student TCI.",
)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
_state_lock = threading.Lock()
_active_dir = DEFAULT_DATA_DIR
_active_upload_dir: Optional[Path] = None


def _read_csv(name: str) -> pd.DataFrame:
    path = _active_dir / name
    if not path.exists():
        raise HTTPException(status_code=503, detail=f"Kết quả {name} chưa có. Hãy chạy pipeline trước.")
    try:
        return pd.read_csv(path)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Không đọc được {name}: {exc}") from exc


def _records(frame: pd.DataFrame) -> list[dict]:
    return json.loads(frame.to_json(orient="records", force_ascii=False))


def _as_int(value, default=0) -> int:
    return int(value) if pd.notna(value) else default


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def dashboard():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
def health():
    return {"status": "ok", "active_data": "uploaded" if _active_dir != DEFAULT_DATA_DIR else "bundled"}


@app.get("/api/summary")
def summary():
    classes = _read_csv(CLASS_FILE)
    students = _read_csv(STUDENT_FILE)
    adjusted = _read_csv(ADJUSTED_FILE)
    quality = _read_csv("bao_cao_clean_data.csv")
    flagged = classes[classes.get("nghi_van", False).fillna(False)] if "nghi_van" in classes else classes.iloc[0:0]
    levels = students.get("Phan_cap", pd.Series(dtype=str)).value_counts(dropna=False).to_dict()
    model_metrics = quality[quality["nhom_bao_cao"].eq("kiem_dinh_model")] if "nhom_bao_cao" in quality else quality.iloc[0:0]
    rmse_rows = model_metrics[model_metrics["chi_tieu"].str.startswith("RMSE_", na=False)] if len(model_metrics) else model_metrics
    model = next((str(row["chi_tieu"]).replace("RMSE_", "", 1) for _, row in rmse_rows.iterrows() if "duoc_chon=True" in str(row["ghi_chu"])), "Chưa có")
    distribution = {
        "gpa_before": students["GPA_goc"].dropna().round(3).tolist() if "GPA_goc" in students else [],
        "gpa_after": students["Normalized_GPA"].dropna().round(3).tolist() if "Normalized_GPA" in students else [],
        "tci": students["TCI"].dropna().round(3).tolist() if "TCI" in students else [],
        "levels": {str(key): _as_int(value) for key, value in levels.items()},
    }
    label_counts = classes.get("Nhan_bat_thuong", pd.Series(dtype=str)).value_counts().to_dict()
    return {
        "students": len(students),
        "classes": len(classes),
        "flagged_classes": len(flagged),
        "adjusted_rows": len(adjusted),
        "review_required": _as_int(adjusted.get("REVIEW_REQUIRED", pd.Series(dtype=bool)).fillna(False).sum()),
        "tci_available": _as_int(students.get("TCI", pd.Series(dtype=float)).notna().sum()),
        "model": model,
        "labels": {str(key): _as_int(value) for key, value in label_counts.items()},
        "levels": {str(key): _as_int(value) for key, value in levels.items()},
        "distribution": distribution,
        "data_source": "uploaded CSV" if _active_dir != DEFAULT_DATA_DIR else "project data",
    }


@app.get("/api/classes")
def classes(
    flagged_only: bool = False,
    query: str = "",
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
):
    frame = _read_csv(CLASS_FILE)
    if flagged_only and "nghi_van" in frame:
        frame = frame[frame["nghi_van"].fillna(False)]
    if query:
        mask = frame.astype(str).apply(lambda col: col.str.contains(query, case=False, na=False)).any(axis=1)
        frame = frame[mask]
    sort_columns = [column for column in ("nghi_van", "Anomaly_Rank", "Anomaly_Score") if column in frame]
    if sort_columns:
        frame = frame.sort_values(sort_columns, ascending=[False, True, False][:len(sort_columns)], na_position="last")
    total = len(frame)
    start = (page - 1) * page_size
    return {"total": total, "page": page, "page_size": page_size, "items": _records(frame.iloc[start:start + page_size])}


@app.get("/api/students")
def students(
    level: str = "",
    query: str = "",
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
):
    frame = _read_csv(STUDENT_FILE)
    if level and "Phan_cap" in frame:
        frame = frame[frame["Phan_cap"].eq(level)]
    if query:
        mask = frame.astype(str).apply(lambda col: col.str.contains(query, case=False, na=False)).any(axis=1)
        frame = frame[mask]
    if "TCI" in frame:
        frame = frame.sort_values("TCI", ascending=False, na_position="last")
    total = len(frame)
    start = (page - 1) * page_size
    return {"total": total, "page": page, "page_size": page_size, "items": _records(frame.iloc[start:start + page_size])}


@app.get("/api/timetable/summary")
def timetable_summary():
    path = RAW_DIR / "Thoi_khoa_bieu.csv"
    if not path.exists():
        return {"available": False, "note": "Không có dữ liệu thời khóa biểu trong workspace."}
    frame = pd.read_csv(path)
    semester_counts = frame.get("Học kỳ", pd.Series(dtype=str)).value_counts().to_dict()
    schedule_type = frame.get("Dạng lịch", pd.Series(dtype=str)).value_counts().to_dict()
    return {
        "available": True,
        "rows": len(frame),
        "course_codes": int(frame.get("Mã HP", pd.Series(dtype=str)).nunique()),
        "section_codes": int(frame.get("Mã LHP", pd.Series(dtype=str)).nunique()),
        "registrations": int(pd.to_numeric(frame.get("Sĩ số ĐK", pd.Series(dtype=float)), errors="coerce").fillna(0).sum()),
        "semesters": {str(key): _as_int(value) for key, value in semester_counts.items()},
        "schedule_types": {str(key): _as_int(value) for key, value in schedule_type.items()},
        "joined_to_grades": False,
        "note": "Hiển thị thống kê TKB độc lập. Mã HP/Mã LHP không có khóa đối chiếu đáng tin cậy với Mã môn/Mã lớp học phần trong dữ liệu điểm.",
    }


@app.post("/api/analyze")
def analyze(file: UploadFile = File(...)):
    global _active_dir, _active_upload_dir
    if not file.filename or Path(file.filename).suffix.lower() not in {".csv", ".txt"}:
        raise HTTPException(status_code=400, detail="Tải lên file CSV dữ liệu điểm.")
    payload = file.file.read(MAX_UPLOAD_BYTES + 1)
    if len(payload) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File vượt giới hạn 50 MB.")
    try:
        header = pd.read_csv(io.BytesIO(payload), nrows=0)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"CSV không đọc được: {exc}") from exc
    missing = sorted(EXPECTED_COLUMNS - set(header.columns))
    if missing:
        raise HTTPException(status_code=422, detail={"missing_columns": missing})

    work_dir = Path(tempfile.mkdtemp(prefix="neu-analytics-"))
    input_path = work_dir / "upload.csv"
    output_path = work_dir / "processed"
    input_path.write_bytes(payload)
    environment = os.environ.copy()
    environment["FIT_INPUT_FILE"] = str(input_path)
    environment["FIT_OUTPUT_DIR"] = str(output_path)
    try:
        completed = subprocess.run(
            [sys.executable, str(PIPELINE)],
            cwd=ROOT,
            env=environment,
            capture_output=True,
            text=True,
            timeout=900,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        shutil.rmtree(work_dir, ignore_errors=True)
        raise HTTPException(status_code=504, detail="Pipeline vượt thời gian cho phép 15 phút.") from exc
    if completed.returncode != 0:
        shutil.rmtree(work_dir, ignore_errors=True)
        detail = (completed.stderr or completed.stdout)[-5000:]
        raise HTTPException(status_code=422, detail=f"Không xử lý được dữ liệu: {detail}")

    with _state_lock:
        old_upload_dir = _active_upload_dir
        _active_dir = output_path
        _active_upload_dir = work_dir
    if old_upload_dir:
        shutil.rmtree(old_upload_dir, ignore_errors=True)
    return {
        "status": "analyzed",
        "input_rows": int(pd.read_csv(input_path, usecols=["Mã SV"]).shape[0]),
        "results": {
            "summary": "/api/summary",
            "classes": "/api/classes",
            "students": "/api/students",
        },
        "logs": completed.stdout[-3000:],
    }


@app.get("/api/exports/{filename}")
def export_file(filename: str):
    if filename not in EXPORTS:
        raise HTTPException(status_code=404, detail="Không có file export này.")
    path = _active_dir / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="File export chưa được tạo.")
    return FileResponse(path, filename=filename, media_type="text/csv; charset=utf-8")
