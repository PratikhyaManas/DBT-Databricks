#!/usr/bin/env python3
"""
Metadata-driven pipeline runner for dbt + Databricks workflows.
"""

import argparse
import os
import shlex
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

import yaml

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from compliance.audit_logging import get_audit_logger, initialize_audit_logger
from monitoring.telemetry import get_health_check, get_telemetry_client, initialize_telemetry


def run_command(
    cmd: List[str] | str,
    env: Dict[str, str] | None = None,
    cwd: str | None = None,
    shell: bool = False,
) -> Tuple[bool, float]:
    """Execute command and return status with execution time."""
    print(f"\n{'=' * 70}")
    if isinstance(cmd, list):
        print(f"Running: {' '.join(cmd)}")
    else:
        print(f"Running: {cmd}")
    print(f"{'=' * 70}\n")

    start_time = time.time()
    result = subprocess.run(cmd, env=env or os.environ, cwd=cwd, shell=shell)
    duration = time.time() - start_time

    return result.returncode == 0, duration


def should_run_dbt_deps(dbt_project_dir: str) -> bool:
    """Run dbt deps only when packages are not installed or packages.yml changed."""
    dbt_path = Path(dbt_project_dir)
    packages_lock = dbt_path / "dbt_packages"
    packages_yml = dbt_path / "packages.yml"

    if not packages_yml.exists():
        return False
    if not packages_lock.exists():
        return True

    return packages_yml.stat().st_mtime > packages_lock.stat().st_mtime


def load_metadata(path: str) -> Dict[str, Any]:
    """Load metadata YAML file."""
    metadata_path = Path(path)
    if not metadata_path.exists():
        raise FileNotFoundError(f"Metadata file not found: {path}")

    with metadata_path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)

    if not isinstance(data, dict):
        raise ValueError("Metadata file must contain a top-level object")

    if "pipelines" not in data or not isinstance(data["pipelines"], dict):
        raise ValueError("Metadata file must define 'pipelines'")

    return data


def format_target(value: Any, target: str) -> Any:
    """Replace {target} placeholders in string values."""
    if isinstance(value, str):
        return value.replace("{target}", target)
    return value


def is_step_enabled(step: Dict[str, Any], target: str) -> bool:
    """Check whether a step should run."""
    enabled = step.get("enabled", True)
    if not enabled:
        return False

    targets = step.get("targets")
    if targets and target not in targets:
        return False

    return True


def run_health_check_step(target: str) -> Tuple[bool, float, str]:
    """Run Databricks connection and schema checks."""
    start_time = time.time()
    health_check = get_health_check()

    databricks_ok = health_check.check_databricks_connection()
    schema_ok = health_check.validate_schema(target)

    duration = time.time() - start_time
    if databricks_ok and schema_ok:
        return True, duration, "completed"

    return False, duration, "failed"


def run_dbt_step(
    step: Dict[str, Any],
    target: str,
    defaults: Dict[str, Any],
    env: Dict[str, str],
) -> Tuple[bool, float, str]:
    """Run a dbt step."""
    command = step.get("command")
    if not command:
        raise ValueError("dbt step requires 'command'")

    dbt_project_dir = defaults.get("dbt_project_dir", "dbt")
    profile_dir = defaults.get("profile_dir", "profiles.yml")

    if command == "deps" and step.get("if_changed_packages", False):
        if not should_run_dbt_deps(dbt_project_dir):
            print("Skipping dbt deps (no package changes detected)")
            return True, 0.0, "skipped"

    cmd: List[str] = ["dbt", command, "--target", target, "--profiles-dir", profile_dir]

    args = step.get("args", [])
    if isinstance(args, list):
        cmd.extend(str(arg) for arg in args)
    elif isinstance(args, str):
        cmd.extend(shlex.split(args))

    select = step.get("select")
    if select:
        cmd.extend(["--select", str(select)])

    return (*run_command(cmd, env=env, cwd=dbt_project_dir), "completed")


def run_bundle_step(
    step: Dict[str, Any],
    target: str,
    defaults: Dict[str, Any],
    env: Dict[str, str],
) -> Tuple[bool, float, str]:
    """Run Databricks bundle action."""
    action = str(step.get("action", "deploy"))
    cmd = ["databricks", "bundle", action, "--target", target]

    bundle_path = step.get("bundle_path")
    if not bundle_path:
        base_path = defaults.get("bundle_base_path", "databricks_bundles")
        bundle_path = f"{base_path}/{target}"

    bundle_path = str(format_target(bundle_path, target))
    if bundle_path:
        cmd.extend(["-C", bundle_path])

    return (*run_command(cmd, env=env), "completed")


def run_shell_step(
    step: Dict[str, Any],
    target: str,
    env: Dict[str, str],
) -> Tuple[bool, float, str]:
    """Run arbitrary shell command."""
    command = step.get("command")
    if not command:
        raise ValueError("shell step requires 'command'")

    command = format_target(command, target)
    cwd = format_target(step.get("cwd"), target)

    if isinstance(command, list):
        return (*run_command([str(c) for c in command], env=env, cwd=cwd), "completed")

    return (*run_command(str(command), env=env, cwd=cwd, shell=True), "completed")


def run_step(
    step: Dict[str, Any],
    target: str,
    defaults: Dict[str, Any],
    env: Dict[str, str],
) -> Tuple[bool, float, str]:
    """Run one pipeline step based on type."""
    step_type = step.get("type")

    if step_type == "health_check":
        return run_health_check_step(target)
    if step_type == "dbt":
        return run_dbt_step(step, target, defaults, env)
    if step_type == "bundle":
        return run_bundle_step(step, target, defaults, env)
    if step_type == "shell":
        return run_shell_step(step, target, env)

    raise ValueError(f"Unsupported step type: {step_type}")


def main() -> int:
    """Entry point for metadata-driven pipeline."""
    parser = argparse.ArgumentParser(description="Metadata-driven dbt + Databricks pipeline runner")
    parser.add_argument(
        "--metadata-file",
        default="pipelines/pipeline_metadata.yaml",
        help="Path to metadata YAML",
    )
    parser.add_argument(
        "--pipeline",
        default="full_deploy",
        help="Pipeline key in metadata file",
    )
    parser.add_argument(
        "--target",
        choices=["dev", "staging", "prod"],
        default="dev",
        help="Target environment",
    )
    parser.add_argument(
        "--list-pipelines",
        action="store_true",
        help="List available pipelines",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print steps without executing",
    )
    args = parser.parse_args()

    initialize_telemetry("metadata-driven-pipeline")
    initialize_audit_logger()

    telemetry = get_telemetry_client()
    audit = get_audit_logger()

    metadata = load_metadata(args.metadata_file)
    pipelines = metadata["pipelines"]

    if args.list_pipelines:
        print("Available pipelines:")
        for key, pipeline in pipelines.items():
            description = pipeline.get("description", "")
            print(f"- {key}: {description}")
        return 0

    if args.pipeline not in pipelines:
        print(f"Pipeline '{args.pipeline}' not found in {args.metadata_file}")
        return 1

    defaults = metadata.get("defaults", {})
    environment_config = metadata.get("environments", {}).get(args.target, {})

    env = os.environ.copy()
    env.update({k: str(v) for k, v in environment_config.get("env", {}).items()})

    selected_pipeline = pipelines[args.pipeline]
    steps = selected_pipeline.get("steps", [])

    if args.dry_run:
        print(f"Dry run for pipeline '{args.pipeline}' on target '{args.target}'")
        for step in steps:
            if is_step_enabled(step, args.target):
                print(f"- {step.get('id', 'unnamed')}: {step.get('type')}")
        return 0

    pipeline_start = datetime.utcnow()
    telemetry.record_event(
        name="metadata_pipeline_start",
        properties={"pipeline": args.pipeline, "target": args.target, "timestamp": pipeline_start.isoformat()},
    )

    audit.log_pipeline_execution(
        pipeline_name=args.pipeline,
        environment=args.target,
        status="started",
        details={"metadata_file": args.metadata_file},
    )

    continue_on_error = bool(selected_pipeline.get("continue_on_error", defaults.get("continue_on_error", False)))
    successful_steps = 0
    failed_steps = 0
    skipped_steps = 0

    for step in steps:
        step_id = step.get("id", "unnamed")

        if not is_step_enabled(step, args.target):
            print(f"Skipping step '{step_id}' (disabled or target mismatch)")
            skipped_steps += 1
            continue

        print(f"\nExecuting step '{step_id}' ({step.get('type')})")

        try:
            success, duration, status = run_step(step, args.target, defaults, env)
        except Exception as exc:
            success, duration, status = False, 0.0, "failed"
            print(f"Step '{step_id}' raised an error: {exc}")

        telemetry.record_metric(
            name="metadata_pipeline.step.duration_seconds",
            value=duration,
            properties={
                "pipeline": args.pipeline,
                "step": step_id,
                "target": args.target,
                "status": "success" if success else "failure",
            },
        )

        audit.log_pipeline_execution(
            pipeline_name=f"{args.pipeline}:{step_id}",
            environment=args.target,
            status=status if success else "failure",
            details={"duration_seconds": duration, "type": step.get("type")},
        )

        if success:
            if status == "skipped":
                skipped_steps += 1
            else:
                successful_steps += 1
            continue

        failed_steps += 1
        if not continue_on_error:
            print(f"Stopping pipeline due to failure in step '{step_id}'")
            break

    total_duration = (datetime.utcnow() - pipeline_start).total_seconds()

    pipeline_success = failed_steps == 0
    final_status = "success" if pipeline_success else "failure"

    telemetry.record_event(
        name=f"metadata_pipeline_{final_status}",
        properties={
            "pipeline": args.pipeline,
            "target": args.target,
            "duration_seconds": total_duration,
            "successful_steps": successful_steps,
            "failed_steps": failed_steps,
            "skipped_steps": skipped_steps,
        },
    )

    telemetry.record_metric(
        name="metadata_pipeline.total.duration_seconds",
        value=total_duration,
        properties={"pipeline": args.pipeline, "target": args.target, "status": final_status},
    )

    audit.log_pipeline_execution(
        pipeline_name=args.pipeline,
        environment=args.target,
        status=final_status,
        details={
            "duration_seconds": total_duration,
            "successful_steps": successful_steps,
            "failed_steps": failed_steps,
            "skipped_steps": skipped_steps,
        },
    )

    print("\n" + "-" * 70)
    print(f"Pipeline: {args.pipeline}")
    print(f"Target: {args.target}")
    print(f"Status: {final_status}")
    print(f"Duration: {total_duration:.2f}s")
    print(f"Successful steps: {successful_steps}")
    print(f"Failed steps: {failed_steps}")
    print(f"Skipped steps: {skipped_steps}")
    print("-" * 70)

    return 0 if pipeline_success else 1


if __name__ == "__main__":
    sys.exit(main())
