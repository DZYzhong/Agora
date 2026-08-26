import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
import sys
from urllib.error import URLError
from urllib.request import urlopen

from sqlalchemy import select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from apps.api.dependencies import create_app_engine
from packages.core.models import (
    ApprovalDecisionModel,
    AssetModel,
    ContextProposalModel,
    ContextRevisionModel,
    ContextStreamModel,
    HumanConfirmationModel,
    ProjectModel,
    PullRequestSignalModel,
    QualityEvidenceModel,
    RepositoryRevisionSignalModel,
    SecurityAuditEventModel,
    SkillModel,
    SkillRunModel,
    SkillVersionModel,
    WorkArtifactModel,
    WorkItemLinkModel,
    WorkItemModel,
    WorkSessionModel,
    WritebackModel,
)
from packages.core.schema_manager import MigrationRequiredError, ensure_schema
from packages.knowledge.index_rebuilder import rebuild_indexes_from_assets
from packages.storage.opensearch.fake import FakeKeywordIndex
from packages.storage.qdrant.fake import FakeVectorIndex


def _sqlite_file_from_url(database_url: str) -> Path | None:
    url = make_url(database_url)
    if url.get_backend_name() != "sqlite":
        return None
    if not url.database or url.database == ":memory:":
        return None
    return Path(url.database).expanduser().resolve()


def rebuild_indexes(database_url: str) -> int:
    ensure_schema(database_url)
    engine = create_app_engine(database_url)
    session = sessionmaker(bind=engine)()
    try:
        return rebuild_indexes_from_assets(session, FakeKeywordIndex(), FakeVectorIndex())
    finally:
        session.close()


def reset_local(database_url: str, *, yes: bool) -> None:
    database_path = _sqlite_file_from_url(database_url)
    if database_path is None:
        raise SystemExit("reset-local only supports file-backed SQLite URLs")
    if not yes:
        raise SystemExit("Refusing to reset local database without --yes")

    for path in (database_path, Path(f"{database_path}-wal"), Path(f"{database_path}-shm")):
        path.unlink(missing_ok=True)
    ensure_schema(database_url)


def migrate(database_url: str, *, dry_run: bool, postgres_backup_confirmed: bool):
    return ensure_schema(
        database_url,
        dry_run=dry_run,
        postgres_backup_confirmed=postgres_backup_confirmed,
    )


def backup_sqlite(database_url: str, *, output: Path) -> Path:
    database_path = _sqlite_file_from_url(database_url)
    if database_path is None:
        raise SystemExit("backup-sqlite only supports file-backed SQLite URLs")
    output = output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    source_uri = f"file:{database_path}?mode=ro"
    with sqlite3.connect(source_uri, uri=True) as source, sqlite3.connect(output) as destination:
        source.backup(destination)
    return output


def restore_sqlite(*, backup: Path, database_url: str, yes: bool) -> Path:
    if not yes:
        raise SystemExit("Refusing to restore SQLite database without --yes")
    database_path = _sqlite_file_from_url(database_url)
    if database_path is None:
        raise SystemExit("restore-sqlite only supports file-backed SQLite URLs")
    backup = backup.expanduser().resolve()
    if not backup.exists():
        raise SystemExit(f"Backup not found: {backup}")
    database_path.parent.mkdir(parents=True, exist_ok=True)
    for path in (database_path, Path(f"{database_path}-wal"), Path(f"{database_path}-shm")):
        path.unlink(missing_ok=True)
    with sqlite3.connect(backup) as source, sqlite3.connect(database_path) as destination:
        source.backup(destination)
    ensure_schema(database_url)
    return database_path


def export_project(*, database_url: str, project_slug: str, output_dir: Path) -> Path:
    ensure_schema(database_url)
    engine = create_app_engine(database_url)
    output_dir = output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    with sessionmaker(bind=engine)() as session:
        project = session.scalar(select(ProjectModel).where(ProjectModel.slug == project_slug))
        if project is None:
            raise SystemExit(f"Project not found: {project_slug}")
        revision = session.scalar(text("SELECT version_num FROM alembic_version"))
        work_item_ids = [
            item.id
            for item in session.scalars(select(WorkItemModel).where(WorkItemModel.project_id == project.id)).all()
        ]
        session_ids = [
            item.id
            for item in session.scalars(select(WorkSessionModel).where(WorkSessionModel.work_item_id.in_(work_item_ids))).all()
        ] if work_item_ids else []
        stream_ids = [
            item.id
            for item in session.scalars(select(ContextStreamModel).where(ContextStreamModel.project_id == project.id)).all()
        ]
        export_specs = {
            "projects.jsonl": [project],
            "assets.jsonl": session.scalars(select(AssetModel).where(AssetModel.project_id == project.id)).all(),
            "work_items.jsonl": session.scalars(select(WorkItemModel).where(WorkItemModel.project_id == project.id)).all(),
            "work_item_links.jsonl": session.scalars(select(WorkItemLinkModel).where(WorkItemLinkModel.project_id == project.id)).all(),
            "work_sessions.jsonl": session.scalars(select(WorkSessionModel).where(WorkSessionModel.work_item_id.in_(work_item_ids))).all()
            if work_item_ids
            else [],
            "work_artifacts.jsonl": session.scalars(select(WorkArtifactModel).where(WorkArtifactModel.project_id == project.id)).all(),
            "human_confirmations.jsonl": session.scalars(select(HumanConfirmationModel).where(HumanConfirmationModel.project_id == project.id)).all(),
            "writebacks.jsonl": session.scalars(select(WritebackModel).where(WritebackModel.project_id == project.id)).all(),
            "context_streams.jsonl": session.scalars(select(ContextStreamModel).where(ContextStreamModel.project_id == project.id)).all(),
            "context_revisions.jsonl": session.scalars(select(ContextRevisionModel).where(ContextRevisionModel.project_id == project.id)).all(),
            "context_proposals.jsonl": session.scalars(select(ContextProposalModel).where(ContextProposalModel.project_id == project.id)).all(),
            "approval_decisions.jsonl": session.scalars(select(ApprovalDecisionModel).where(ApprovalDecisionModel.project_id == project.id)).all(),
            "skills.jsonl": session.scalars(select(SkillModel).where(SkillModel.project_id == project.id)).all(),
            "skill_versions.jsonl": session.scalars(select(SkillVersionModel).where(SkillVersionModel.project_id == project.id)).all(),
            "skill_runs.jsonl": session.scalars(select(SkillRunModel).where(SkillRunModel.project_id == project.id)).all(),
            "quality_evidence.jsonl": session.scalars(select(QualityEvidenceModel).where(QualityEvidenceModel.project_id == project.id)).all(),
            "security_audit_events.jsonl": session.scalars(select(SecurityAuditEventModel).where(SecurityAuditEventModel.project_id == project.id)).all(),
            "repository_revision_signals.jsonl": session.scalars(select(RepositoryRevisionSignalModel).where(RepositoryRevisionSignalModel.project_id == project.id)).all(),
            "pull_request_signals.jsonl": session.scalars(select(PullRequestSignalModel).where(PullRequestSignalModel.project_id == project.id)).all(),
        }
        counts = {}
        for filename, records in export_specs.items():
            counts[filename] = _write_jsonl(output_dir / filename, records)
        manifest = {
            "format": "agora-project-export/v1",
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "schema_revision": revision,
            "project": {
                "id": project.id,
                "org_id": project.org_id,
                "slug": project.slug,
                "name": project.name,
            },
            "files": counts,
            "relationships": {
                "work_item_ids": work_item_ids,
                "work_session_ids": session_ids,
                "context_stream_ids": stream_ids,
            },
        }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    return output_dir


def _write_jsonl(path: Path, records) -> int:
    count = 0
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(_model_to_dict(record), ensure_ascii=False, sort_keys=True, default=str) + "\n")
            count += 1
    return count


def _model_to_dict(record) -> dict:
    data = {}
    for column in record.__table__.columns:
        data[column.name] = getattr(record, column.key)
    return data


def smoke(*, api_base_url: str, web_base_url: str | None = None, timeout: float = 5.0) -> list[str]:
    api_base_url = api_base_url.rstrip("/")
    ready = _fetch_json(f"{api_base_url}/ready", timeout=timeout)
    if ready.get("status") != "ready":
        raise SystemExit(f"API readiness failed: {ready}")
    metrics = _fetch_text(f"{api_base_url}/metrics", timeout=timeout)
    if "agora_ready 1" not in metrics:
        raise SystemExit("Metrics check failed: agora_ready 1 not found")
    lines = [
        f"API readiness: {ready['status']}",
        "Metrics: ok",
    ]
    if web_base_url:
        _fetch_text(web_base_url.rstrip("/") + "/", timeout=timeout)
        lines.append("Web: ok")
    return lines


def _fetch_json(url: str, *, timeout: float) -> dict:
    text_body = _fetch_text(url, timeout=timeout)
    try:
        return json.loads(text_body)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON from {url}: {exc}") from exc


def _fetch_text(url: str, *, timeout: float) -> str:
    try:
        with urlopen(url, timeout=timeout) as response:
            status = getattr(response, "status", 200)
            if status >= 400:
                raise SystemExit(f"HTTP {status} from {url}")
            return response.read().decode("utf-8")
    except URLError as exc:
        raise SystemExit(f"Unable to reach {url}: {exc}") from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Agora local administration commands")
    subparsers = parser.add_subparsers(dest="command", required=True)

    rebuild = subparsers.add_parser("rebuild-indexes", help="Rebuild local search indexes from persisted assets")
    rebuild.add_argument("--database-url", required=True)

    reset = subparsers.add_parser("reset-local", help="Reset a file-backed local SQLite database")
    reset.add_argument("--database-url", required=True)
    reset.add_argument("--yes", action="store_true", help="Confirm destructive local reset")

    migrate_parser = subparsers.add_parser("migrate", help="Inspect and migrate the product database")
    migrate_parser.add_argument("--database-url", required=True)
    migrate_parser.add_argument("--dry-run", action="store_true", help="Inspect without changing the database")
    migrate_parser.add_argument(
        "--postgres-backup-confirmed",
        action="store_true",
        help="Confirm an operator backup exists before stamping an unversioned PostgreSQL P1 schema",
    )

    backup = subparsers.add_parser("backup-sqlite", help="Write an online backup of a file-backed SQLite database")
    backup.add_argument("--database-url", required=True)
    backup.add_argument("--output", required=True, type=Path)

    restore = subparsers.add_parser("restore-sqlite", help="Restore a file-backed SQLite database from a backup file")
    restore.add_argument("--backup", required=True, type=Path)
    restore.add_argument("--database-url", required=True)
    restore.add_argument("--yes", action="store_true", help="Confirm replacing the target SQLite database")

    export = subparsers.add_parser("export-project", help="Export one project governance archive as JSONL files")
    export.add_argument("--database-url", required=True)
    export.add_argument("--project-slug", required=True)
    export.add_argument("--output-dir", required=True, type=Path)

    smoke_parser = subparsers.add_parser("smoke", help="Run deployment smoke checks against running Agora services")
    smoke_parser.add_argument("--api-base-url", required=True)
    smoke_parser.add_argument("--web-base-url")
    smoke_parser.add_argument("--timeout", type=float, default=5.0)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "rebuild-indexes":
        count = rebuild_indexes(args.database_url)
        print(f"Rebuilt indexes from {count} persisted assets")
        return 0
    if args.command == "reset-local":
        reset_local(args.database_url, yes=args.yes)
        print("Reset local SQLite database")
        return 0
    if args.command == "migrate":
        try:
            result = migrate(
                args.database_url,
                dry_run=args.dry_run,
                postgres_backup_confirmed=args.postgres_backup_confirmed,
            )
        except MigrationRequiredError as exc:
            print(str(exc), file=sys.stderr)
            return 2
        print(f"Action: {result.action}")
        print(f"Schema fingerprint: {result.fingerprint}")
        print(f"Revision: {result.revision_before or 'unversioned'} -> {result.revision_after}")
        print(f"Backup: {result.backup_path or 'not-created'}")
        return 0
    if args.command == "backup-sqlite":
        path = backup_sqlite(args.database_url, output=args.output)
        print(f"SQLite backup written: {path}")
        return 0
    if args.command == "restore-sqlite":
        path = restore_sqlite(backup=args.backup, database_url=args.database_url, yes=args.yes)
        print(f"SQLite backup restored: {path}")
        return 0
    if args.command == "export-project":
        path = export_project(
            database_url=args.database_url,
            project_slug=args.project_slug,
            output_dir=args.output_dir,
        )
        print(f"Project export written: {path}")
        return 0
    if args.command == "smoke":
        for line in smoke(api_base_url=args.api_base_url, web_base_url=args.web_base_url, timeout=args.timeout):
            print(line)
        return 0
    raise SystemExit(f"Unknown command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
