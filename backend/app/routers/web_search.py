from pydantic import BaseModel
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.web_search import run_web_scholarship_search, web_search_status

router = APIRouter(prefix="/api/web-search", tags=["web-search"])


class WebSearchRunRequest(BaseModel):
    query: str | None = None


@router.get("/status")
def status(db: Session = Depends(get_db)):
    return web_search_status(db)


@router.post("/run")
async def run_search(body: WebSearchRunRequest | None = None, db: Session = Depends(get_db)):
    query = body.query if body else None
    return await run_web_scholarship_search(db, query)


@router.post("/discover-scholarships")
async def discover_scholarships(body: WebSearchRunRequest | None = None, db: Session = Depends(get_db)):
    query = body.query if body else None
    return await run_web_scholarship_search(db, query)
