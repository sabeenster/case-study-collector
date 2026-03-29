"""FastAPI web server for Case Study Collector."""

from __future__ import annotations

import logging
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, Form, Request, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import AppConfig
from app import db
from app.generator import generate_case_study
from app.notify import send_case_study_email

logger = logging.getLogger("casestudy")

# Resolve all paths relative to project root (parent of app/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent

config = AppConfig.load(PROJECT_ROOT / "config.yaml")


@asynccontextmanager
async def lifespan(app: FastAPI):
    config.ensure_dirs(PROJECT_ROOT)
    db.init_db(config.db_path_resolved(PROJECT_ROOT))
    logger.info("Case Study Collector started")
    yield


app = FastAPI(title="Case Study Collector", lifespan=lifespan)

templates = Jinja2Templates(directory=str(PROJECT_ROOT / "templates"))

# Resolve storage paths relative to project root
db_path = config.db_path_resolved(PROJECT_ROOT)
uploads_path = PROJECT_ROOT / config.storage.uploads_dir
uploads_path.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(uploads_path)), name="uploads")


@app.get("/health")
async def health():
    return {"status": "ok"}


# --- Brand List ---

@app.get("/", response_class=HTMLResponse)
async def brand_list(request: Request):
    brands = db.get_brands(db_path)
    return templates.TemplateResponse("index.html", {
        "request": request,
        "page": "brands",
        "brands": brands,
    })


@app.post("/brand/add")
async def add_brand(
    name: str = Form(...),
    industry: str = Form(""),
    onboarded_at: str = Form(""),
    notes: str = Form(""),
):
    db.create_brand(db_path, name, industry, onboarded_at, notes)
    return RedirectResponse("/", status_code=303)


@app.post("/brand/{brand_id}/delete")
async def delete_brand(brand_id: int):
    db.delete_brand(db_path, brand_id)
    return RedirectResponse("/", status_code=303)


# --- Brand Detail ---

@app.get("/brand/{brand_id}", response_class=HTMLResponse)
async def brand_detail(request: Request, brand_id: int):
    brand = db.get_brand(db_path, brand_id)
    if not brand:
        return RedirectResponse("/", status_code=303)

    snapshots = db.get_snapshots(db_path, brand_id)
    for snap in snapshots:
        snap["metrics"] = db.get_metrics(db_path, snap["id"])
        snap["screenshots"] = db.get_screenshots(db_path, snap["id"])

    entries = db.get_entries(db_path, brand_id)

    return templates.TemplateResponse("index.html", {
        "request": request,
        "page": "brand_detail",
        "brand": brand,
        "snapshots": snapshots,
        "entries": entries,
    })


# --- Snapshots ---

@app.post("/brand/{brand_id}/snapshot/add")
async def add_snapshot(
    brand_id: int,
    label: str = Form(...),
    snapshot_date: str = Form(...),
    notes: str = Form(""),
    # Metrics come as parallel arrays
    metric_category: list[str] = Form(default=[]),
    metric_name: list[str] = Form(default=[]),
    metric_value: list[str] = Form(default=[]),
    metric_unit: list[str] = Form(default=[]),
    metric_change_pct: list[str] = Form(default=[]),
    metric_change_vs: list[str] = Form(default=[]),
    # Screenshots
    screenshots: list[UploadFile] = File(default=[]),
):
    snapshot_id = db.create_snapshot(db_path, brand_id, label, snapshot_date, notes)

    # Add metrics
    for i in range(len(metric_name)):
        if not metric_name[i].strip():
            continue
        db.add_metric(
            db_path, snapshot_id,
            category=metric_category[i] if i < len(metric_category) else "",
            name=metric_name[i],
            value=metric_value[i] if i < len(metric_value) else "",
            unit=metric_unit[i] if i < len(metric_unit) else "",
            change_pct=metric_change_pct[i] if i < len(metric_change_pct) else "",
            change_vs=metric_change_vs[i] if i < len(metric_change_vs) else "",
        )

    # Save screenshots
    for file in screenshots:
        if not file.filename:
            continue
        ext = Path(file.filename).suffix
        stored_name = f"{uuid.uuid4().hex}{ext}"
        dest = uploads_path / stored_name
        content = await file.read()
        dest.write_bytes(content)
        db.add_screenshot(db_path, snapshot_id, stored_name, file.filename)

    return RedirectResponse(f"/brand/{brand_id}", status_code=303)


@app.post("/snapshot/{snapshot_id}/delete")
async def delete_snapshot(snapshot_id: int):
    snap = db.get_snapshot(db_path, snapshot_id)
    if snap:
        # Clean up screenshot files
        screenshots = db.get_screenshots(db_path, snapshot_id)
        for ss in screenshots:
            fpath = uploads_path / ss["filename"]
            if fpath.exists():
                fpath.unlink()
        db.delete_snapshot(db_path, snapshot_id)
        return RedirectResponse(f"/brand/{snap['brand_id']}", status_code=303)
    return RedirectResponse("/", status_code=303)


# --- Text Entries ---

@app.post("/brand/{brand_id}/entry/add")
async def add_entry(
    brand_id: int,
    category: str = Form(""),
    content: str = Form(...),
    source: str = Form(""),
    entry_date: str = Form(""),
):
    if not entry_date:
        entry_date = datetime.now().strftime("%Y-%m-%d")
    db.create_entry(db_path, brand_id, category, content, source, entry_date)
    return RedirectResponse(f"/brand/{brand_id}", status_code=303)


@app.post("/entry/{entry_id}/delete")
async def delete_entry(entry_id: int, brand_id: int = Form(...)):
    db.delete_entry(db_path, entry_id)
    return RedirectResponse(f"/brand/{brand_id}", status_code=303)


# --- Case Study Generation ---

@app.post("/brand/{brand_id}/case-study")
async def gen_case_study(request: Request, brand_id: int):
    brand_data = db.get_brand_full(db_path, brand_id)
    if not brand_data:
        return RedirectResponse("/", status_code=303)

    case_study = await generate_case_study(brand_data, config)

    snapshots = brand_data.get("snapshots", [])
    entries = brand_data.get("entries", [])

    return templates.TemplateResponse("index.html", {
        "request": request,
        "page": "case_study",
        "brand": brand_data,
        "snapshots": snapshots,
        "entries": entries,
        "case_study": case_study,
    })


@app.post("/brand/{brand_id}/case-study/email")
async def email_case_study(brand_id: int, case_study: str = Form(...)):
    brand = db.get_brand(db_path, brand_id)
    if brand:
        send_case_study_email(brand["name"], case_study, config)
    return RedirectResponse(f"/brand/{brand_id}", status_code=303)
