"""CLI runtime entrypoint."""

from __future__ import annotations

from scholaraio.core.log import ui as _default_ui


def _ui(message: str = "") -> None:
    try:
        from scholaraio.interfaces.cli import compat as cli_mod
    except ImportError:
        _default_ui(message)
        return
    cli_mod.ui(message)


def main() -> None:
    from scholaraio.interfaces.cli import compat as cli_mod

    parser = cli_mod._build_parser()
    args = parser.parse_args()
    cfg = cli_mod.load_config()
    cfg.ensure_dirs()

    from scholaraio.core import log as _log
    from scholaraio.services import metrics as _metrics
    from scholaraio.services.ingest_metadata._models import configure_s2_session, configure_session
    from scholaraio.services.migration_control import (
        SUPPORTED_LAYOUT_VERSION,
        describe_migration_lock,
        ensure_instance_metadata,
        layout_version_is_supported,
    )

    meta = ensure_instance_metadata(cfg)
    session_id = _log.setup(cfg)
    if args.command == "migrate":
        args.func(args, cfg)
        return

    layout_version = meta.get("layout_version")
    if not layout_version_is_supported(layout_version):
        _ui(f"检测到更高版本的运行时布局：layout_version={layout_version}。")
        _ui(f"当前程序最高支持 {SUPPORTED_LAYOUT_VERSION}；请先升级 ScholarAIO。")
        _ui("当前仍可运行 `scholaraio migrate status` 查看控制面状态。")
        raise SystemExit(2)

    lock_status = describe_migration_lock(cfg)
    if lock_status["status"] != "absent":
        _ui(f"检测到活动的 migration.lock：{cfg.migration_lock_path}")
        _ui("当前仅允许运行 `scholaraio migrate status` 或 `scholaraio migrate recover --clear-lock`。")
        raise SystemExit(2)

    is_setup_cmd = args.command == "setup"
    try:
        _metrics.init(cfg.metrics_db_path, session_id)
    except Exception as exc:
        if not is_setup_cmd:
            raise
        _ui(f"警告：metrics 初始化失败，已跳过，不影响 setup: {exc}")
    configure_session(cfg.ingest.contact_email)
    configure_s2_session(cfg.resolved_s2_api_key())

    args.func(args, cfg)
