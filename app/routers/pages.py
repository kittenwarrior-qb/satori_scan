"""Phục vụ các trang HTML."""
from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

from app.paths import TEMPLATES_DIR

router = APIRouter()
templates = Jinja2Templates(directory=TEMPLATES_DIR)


@router.get("/")
def index(request: Request):
    return templates.TemplateResponse(request, "index.html")


@router.get("/identify")
def identify_page(request: Request):
    return templates.TemplateResponse(request, "identify.html")


@router.get("/classify")
def classify_page(request: Request):
    return templates.TemplateResponse(request, "classify.html")


@router.get("/reject")
def reject_page(request: Request):
    return templates.TemplateResponse(request, "reject.html")


@router.get("/reports")
def reports_page(request: Request):
    return templates.TemplateResponse(request, "reports.html")
