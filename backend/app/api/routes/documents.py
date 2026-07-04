"""Document management routes (all require authentication)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from starlette.concurrency import run_in_threadpool

from app.api.deps import get_current_user
from app.core.ratelimit import rate_limit
from app.db.base import DocumentRecord, User
from app.schemas.documents import DocumentCreate, DocumentOut

router = APIRouter(prefix="/documents", tags=["documents"])


def _to_out(doc: DocumentRecord) -> DocumentOut:
    return DocumentOut(
        id=doc.id,
        title=doc.title,
        char_count=doc.char_count,
        chunk_count=doc.chunk_count,
        created_at=doc.created_at,
    )


@router.post(
    "",
    response_model=DocumentOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit("ingest", limit=20, window_seconds=60))],
)
async def create_document(
    payload: DocumentCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
) -> DocumentOut:
    settings = request.app.state.settings
    text = payload.text.strip()
    if not text:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Document text is empty.",
        )
    if len(text) > settings.max_document_chars:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Document exceeds {settings.max_document_chars} characters.",
        )

    pipeline = request.app.state.pipeline
    # Embedding can involve blocking network/CPU work; keep the event loop free.
    document_id, chunk_count = await run_in_threadpool(
        pipeline.ingest, current_user.id, payload.title.strip(), text
    )
    if chunk_count == 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="No indexable content found in the document.",
        )

    record = DocumentRecord(
        id=document_id,
        user_id=current_user.id,
        title=payload.title.strip(),
        char_count=len(text),
        chunk_count=chunk_count,
    )
    await request.app.state.repos.documents.create(record)
    return _to_out(record)


@router.get("", response_model=list[DocumentOut])
async def list_documents(
    request: Request, current_user: User = Depends(get_current_user)
) -> list[DocumentOut]:
    docs = await request.app.state.repos.documents.list_for_user(current_user.id)
    return [_to_out(d) for d in docs]


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
) -> None:
    deleted = await request.app.state.repos.documents.delete(
        current_user.id, document_id
    )
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found."
        )
    pipeline = request.app.state.pipeline
    await run_in_threadpool(pipeline.delete_document, current_user.id, document_id)
