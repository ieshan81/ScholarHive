"""Memory Vault — ingest, dedupe, auto-approve, conflicts."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.profile_graph import ProfileGraphNode, SENSITIVE_NODE_TYPES
from app.models.story import Story
from app.services.memory_extraction import cluster_for_type, extract_memories_from_text


def decide_status(confidence: float, sensitive: bool, needs_review: bool, has_conflict: bool) -> str:
    if has_conflict:
        return "conflict"
    if sensitive or needs_review or confidence < 0.72:
        return "needs_review"
    if confidence >= 0.85:
        return "auto_approved"
    return "needs_review"


def ingest_memory_items(
    db: Session,
    items: list[dict],
    source_document_id: int | None = None,
) -> dict:
    created = merged = conflicts = auto_approved = 0
    by_key: dict[str, ProfileGraphNode] = {
        n.canonical_key: n
        for n in db.query(ProfileGraphNode).filter(ProfileGraphNode.canonical_key.isnot(None)).all()
        if n.canonical_key
    }

    for item in items:
        key = item.get("canonical_key")
        if not key:
            continue
        sensitive = bool(item.get("sensitive")) or item.get("node_type") in SENSITIVE_NODE_TYPES
        conf = float(item.get("confidence") or 0.5)
        existing = by_key.get(key)
        if existing:
            existing.summary = existing.summary or item.get("summary")
            if item.get("source_excerpt"):
                prev = existing.source_excerpt or ""
                if item["source_excerpt"][:200] not in prev:
                    existing.source_excerpt = (prev + "\n---\n" + item["source_excerpt"])[:4000]
            existing.confidence = max(existing.confidence or 0, conf)
            existing.updated_at = datetime.utcnow()
            merged += 1
            continue

        conflict = _detect_value_conflict(db, item)
        status = decide_status(conf, sensitive, bool(item.get("needs_review")), bool(conflict))
        if status == "auto_approved":
            auto_approved += 1
        if conflict:
            conflicts += 1

        node = ProfileGraphNode(
            node_type=item.get("node_type", "essay_theme"),
            title=(item.get("title") or "Memory")[:500],
            summary=item.get("summary"),
            details=item.get("details"),
            source_document_id=source_document_id,
            source_excerpt=item.get("source_excerpt"),
            confidence=conf,
            status=status,
            approved_by_user=status in ("auto_approved", "user_confirmed"),
            canonical_key=key,
            conflict_flag=conflict,
            importance_score=min(1.0, conf + (0.1 if sensitive else 0)),
        )
        db.add(node)
        by_key[key] = node
        created += 1

    db.commit()
    return {
        "created": created,
        "merged": merged,
        "conflicts": conflicts,
        "auto_approved": auto_approved,
    }


def _detect_value_conflict(db: Session, item: dict) -> str | None:
    ntype = item.get("node_type")
    title = (item.get("title") or "").lower()
    if ntype not in ("GPA", "university", "major", "international_status", "visa_status"):
        return None
    peers = db.query(ProfileGraphNode).filter(
        ProfileGraphNode.node_type == ntype,
        ProfileGraphNode.status.in_(("auto_approved", "user_confirmed", "needs_review")),
    ).all()
    new_val = (item.get("summary") or item.get("title") or "").strip().lower()
    for p in peers:
        old_val = (p.summary or p.title or "").strip().lower()
        if old_val and new_val and old_val != new_val and len(old_val) > 2 and len(new_val) > 2:
            return f"Possible conflict for {ntype}: '{p.summary or p.title}' vs '{item.get('summary') or item.get('title')}'"
    return None


async def process_document(db: Session, doc_id: int) -> dict:
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        return {"success": False, "message": "Document not found"}
    if not doc.extracted_text:
        return {"success": False, "message": "No extracted text — upload/extract first"}

    doc.processing_status = "processing"
    db.commit()

    items = await extract_memories_from_text(doc.extracted_text, doc.file_name or "document")
    stats = ingest_memory_items(db, items, doc.id)
    doc.processing_status = "processed"
    doc.extraction_status = "completed"
    db.commit()
    return {"success": True, "message": "Memory extraction complete", **stats}


def memory_overview(db: Session) -> dict:
    nodes = db.query(ProfileGraphNode).order_by(ProfileGraphNode.updated_at.desc()).all()
    clusters: dict[str, dict] = {}
    for n in nodes:
        cluster = cluster_for_type(n.node_type)
        c = clusters.setdefault(cluster, {"count": 0, "auto_approved": 0, "needs_review": 0, "conflicts": 0, "nodes": []})
        c["count"] += 1
        if n.status == "auto_approved" or n.approved_by_user:
            c["auto_approved"] += 1
        if n.status == "needs_review":
            c["needs_review"] += 1
        if n.status == "conflict" or n.conflict_flag:
            c["conflicts"] += 1
        c["nodes"].append(_node_dict(n))

    docs = db.query(Document).filter(Document.is_demo.is_(False)).order_by(Document.updated_at.desc()).all()
    stories = db.query(Story).filter(Story.is_demo.is_(False)).all()

    return {
        "total_nodes": len(nodes),
        "clusters": clusters,
        "documents_count": len(docs),
        "legacy_stories_count": len(stories),
        "documents": [_doc_dict(d) for d in docs],
    }


def _node_dict(n: ProfileGraphNode) -> dict:
    return {
        "id": n.id,
        "node_type": n.node_type,
        "cluster": cluster_for_type(n.node_type),
        "title": n.title,
        "summary": n.summary,
        "details": n.details,
        "source_excerpt": (n.source_excerpt or "")[:400],
        "confidence": n.confidence,
        "status": n.status,
        "approved_by_user": n.approved_by_user,
        "conflict_flag": n.conflict_flag,
        "source_document_id": n.source_document_id,
        "used_in_essays_count": n.used_in_essays_count,
    }


def _doc_dict(d: Document) -> dict:
    return {
        "id": d.id,
        "file_name": d.file_name,
        "original_filename": d.original_filename,
        "file_type": d.file_type,
        "source_type": d.source_type,
        "processing_status": d.processing_status,
        "extraction_status": d.extraction_status,
        "extraction_error": d.extraction_error,
        "created_at": d.created_at.isoformat() if d.created_at else None,
    }


def approved_memories_text(db: Session, limit: int = 40) -> str:
    nodes = (
        db.query(ProfileGraphNode)
        .filter(
            ProfileGraphNode.status.in_(("auto_approved", "user_confirmed")),
        )
        .order_by(ProfileGraphNode.importance_score.desc())
        .limit(limit)
        .all()
    )
    lines = []
    for n in nodes:
        lines.append(f"[{n.node_type}] {n.title}: {n.summary or ''}\nSource: {(n.source_excerpt or '')[:300]}")
    return "\n\n".join(lines)


def writing_style_samples(db: Session) -> str:
    nodes = (
        db.query(ProfileGraphNode)
        .filter(ProfileGraphNode.node_type == "writing_style_sample")
        .filter(ProfileGraphNode.status.in_(("auto_approved", "user_confirmed", "needs_review")))
        .limit(5)
        .all()
    )
    return "\n\n".join((n.details or n.summary or "")[:1500] for n in nodes)


def bulk_approve_high_confidence(db: Session, min_confidence: float = 0.85) -> dict:
    q = db.query(ProfileGraphNode).filter(
        ProfileGraphNode.status == "needs_review",
        ProfileGraphNode.confidence >= min_confidence,
        ProfileGraphNode.conflict_flag.is_(None),
        ~ProfileGraphNode.node_type.in_(list(SENSITIVE_NODE_TYPES)),
    )
    count = 0
    for n in q.all():
        n.status = "auto_approved"
        n.approved_by_user = True
        count += 1
    db.commit()
    return {"approved": count}
