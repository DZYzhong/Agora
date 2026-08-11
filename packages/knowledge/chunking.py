from dataclasses import dataclass

from packages.domain.schemas import AssetCreate


@dataclass(frozen=True)
class AssetChunk:
    org_id: str
    project_id: str
    source_uri: str
    title: str
    content: str
    metadata: dict


def chunk_asset(asset: AssetCreate, *, max_chars: int = 1200) -> list[AssetChunk]:
    paragraphs = [part.strip() for part in asset.content.split("\n\n") if part.strip()]
    if not paragraphs:
        paragraphs = [asset.content[:max_chars]]

    chunks: list[AssetChunk] = []
    buffer = ""
    for paragraph in paragraphs:
        candidate = f"{buffer}\n\n{paragraph}".strip() if buffer else paragraph
        if len(candidate) <= max_chars:
            buffer = candidate
            continue
        if buffer:
            chunks.append(_make_chunk(asset, buffer))
        buffer = paragraph[:max_chars]

    if buffer:
        chunks.append(_make_chunk(asset, buffer))

    return chunks


def _make_chunk(asset: AssetCreate, content: str) -> AssetChunk:
    return AssetChunk(
        org_id=asset.org_id,
        project_id=asset.project_id,
        source_uri=asset.source_uri,
        title=asset.title,
        content=content,
        metadata=asset.metadata,
    )
