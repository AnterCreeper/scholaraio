"""Backup CLI command handler."""

from __future__ import annotations

import argparse
import logging
import shlex
import sys


def _ui(msg: str = "") -> None:
    try:
        from scholaraio.interfaces.cli import compat as cli_mod
    except ImportError:
        from scholaraio.core.log import ui as log_ui

        log_ui(msg)
        return
    cli_mod.ui(msg)


def _log_error(msg: str, *args) -> None:
    try:
        from scholaraio.interfaces.cli import compat as cli_mod
    except ImportError:
        logging.getLogger(__name__).error(msg, *args)
        return
    cli_mod._log.error(msg, *args)


def cmd_backup(args: argparse.Namespace, cfg) -> None:
    from scholaraio.services.backup import BackupConfigError, build_rsync_command, run_backup

    ui = _ui
    action = getattr(args, "backup_action", None)
    if action == "list":
        ui(f"备份源目录: {cfg.backup_source_dir}")
        if not cfg.backup.targets:
            ui("未配置任何备份目标。")
            return
        ui()
        for name, target in sorted(cfg.backup.targets.items()):
            status = "启用" if target.enabled else "禁用"
            remote = f"{target.user}@{target.host}" if target.user else target.host
            ui(f"[{name}] {status}")
            ui(f"  远端: {remote}:{target.path}")
            ui(f"  模式: {target.mode}  |  压缩: {'on' if target.compress else 'off'}")
            if target.exclude:
                ui(f"  排除: {', '.join(target.exclude)}")
        return

    if action == "run":
        try:
            cmd = build_rsync_command(cfg, args.target, dry_run=args.dry_run)
            ui("即将执行备份命令：")
            ui("  " + shlex.join(cmd))
            result = run_backup(cfg, args.target, dry_run=args.dry_run)
        except BackupConfigError as exc:
            _log_error("%s", exc)
            sys.exit(1)

        if result.stdout.strip():
            ui()
            ui(result.stdout.rstrip())
        if result.stderr.strip():
            ui()
            ui(result.stderr.rstrip())
        if result.returncode != 0:
            _print_backup_failure_guidance(cfg, args.target, result.stderr)
            _log_error("备份失败，退出码: %s", result.returncode)
            sys.exit(result.returncode)
        if args.dry_run:
            ui()
            ui("预演完成：未实际传输文件。")
        else:
            ui()
            ui("备份完成。")
        return

    _log_error("未知 backup 子命令: %s", action)
    sys.exit(1)


def _print_backup_failure_guidance(cfg, target_name: str, stderr: str) -> None:
    ui = _ui
    stderr = (stderr or "").strip()
    if not stderr:
        return

    target = cfg.backup.targets.get(target_name)
    host = target.host if target and target.host else "<host>"
    user = target.user if target and target.user else "<user>"
    port = target.port if target and target.port else 22
    identity_file = target.identity_file if target and target.identity_file else "~/.ssh/id_ed25519"
    remote = f"{user}@{host}" if user != "<user>" else host
    lower = stderr.lower()

    auth_error = "permission denied" in lower or "publickey" in lower
    host_key_error = "host key verification failed" in lower or "host key is unknown" in lower
    if not auth_error and not host_key_error:
        return

    ui()
    ui("提示：`scholaraio backup run` 会强制使用非交互 SSH（`BatchMode=yes`），不会在 CLI 里等待密码或 host key 确认。")
    ui("建议按下面步骤完成一次性配置：")
    ui("  1. 在 `config.local.yaml` 中为该目标补齐 SSH 配置：")
    ui("     backup:")
    ui("       targets:")
    ui(f"         {target_name}:")
    ui(f"           host: {host}")
    ui(f"           user: {user}")
    ui(f"           port: {port}")
    ui(f"           identity_file: {identity_file}  # 推荐：密钥登录")
    ui("           password: <ssh-password>  # 备选：仅放在 config.local.yaml")
    if host_key_error:
        ui(f"  2. 先写入 `known_hosts`：`ssh-keyscan -p {port} {host} >> ~/.ssh/known_hosts`")
    else:
        ui("  2. `backup run` 不支持在 CLI 里临时输入 SSH 密码；请提前准备密钥或把密码写进 `config.local.yaml`。")
        ui(f"     首次连接若还没信任主机，请先执行：`ssh-keyscan -p {port} {host} >> ~/.ssh/known_hosts`")
    ui(f"  3. 若走密钥方案，先验证：`ssh -i {identity_file} -p {port} {remote} true`")
    ui("     若走密码方案，保存 `config.local.yaml` 后直接重试 backup dry-run 即可。")
    ui(f"  4. 验证通过后重试：`scholaraio backup run {target_name} --dry-run`")
