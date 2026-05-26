from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.profile_graph import ProfileGraphNode
from app.models.document import Document

router = APIRouter(prefix="/api/profile-graph", tags=["profile-graph"])


class ExtractTextBody(BaseModel):
    text: str
    title: str = "Pasted content"
    node_type: str = "essay themes"


@router.get("")
def list_nodes(db: Session = Depends(get_db)):
    nodes = db.query(ProfileGraphNode).order_by(ProfileGraphNode.updated_at.desc()).all()
    clusters: dict[str, list] = {}
    for n in nodes:
        clusters.setdefault(n.node_type, []).append({
            "id": n.id,
            "title": n.title,
            "summary": n.summary,
            "confidence": n.confidence,
            "approved_by_user": n.approved_by_user,
            "conflict_flag": n.conflict_flag,
            "source_excerpt": (n.source_excerpt or "")[:200],
        })
    return {"clusters": clusters, "total": len(nodes)}


@router.post("/extract-from-text")
def extract_from_text(body: ExtractTextBody, db: Session = Depends(get_db)):
    """MVP: store pasted text as graph node chunks (no OCR)."""
    chunks = [c.strip() for c in body.text.split("\n\n") if len(c.strip()) > 40][:10]
    created = []
    for i, chunk in enumerate(chunks):
        node = ProfileGraphNode(
            node_type=body.node_type,
            title=f"{body.title} — section {i+1}",
            summary=chunk[:500],
            source_excerpt=chunk[:2000],
            confidence=0.5,
        )
        db.add(node)
        created.append(node)
    db.commit()
    return {"message": f"Created {len(created)} graph nodes from text", "count": len(created)}


@router.post("/nodes/{node_id}/approve")
def approve_node(node_id: int, db: Session = Depends(get_db)):
    node = db.query(ProfileGraphNode).filter(ProfileGraphNode.id == node_id).first()
    if not node:
        return {"message": "Not found"}
    node.approved_by_user = True
    db.commit()
    return {"message": "Approved"}


@router.get("/conflicts")
def list_conflicts(db: Session = Depends(get_db)):
    return [
        {"id": n.id, "title": n.title, "conflict_flag": n.conflict_flag}
        for n in db.query(ProfileGraphNode).filter(ProfileGraphNode.conflict_flag.isnot(None)).all()
    ]
