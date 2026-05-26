from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.trusted_platform_cleanup import apply_trusted_platform_cleanup
from app.services.trusted_platforms import (
    list_ignored_sources,
    list_trusted_platforms,
    trusted_mode_status,
)

router = APIRouter(prefix="/api/trusted-platforms", tags=["trusted-platforms"])


@router.get("/status")
def get_status(db: Session = Depends(get_db)):
    return trusted_mode_status(db)


@router.get("")
def list_platforms(db: Session = Depends(get_db)):
    return list_trusted_platforms(db)


@router.get("/ignored-sources")
def ignored_sources(db: Session = Depends(get_db)):
    return list_ignored_sources(db)


@router.post("/apply-cleanup")
def apply_cleanup(db: Session = Depends(get_db)):
    return apply_trusted_platform_cleanup(db)
