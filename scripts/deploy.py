#!/usr/bin/env python3
"""
Deploy Databricks Asset Bundle and run dbt transformations
Includes enterprise monitoring, governance, and compliance tracking
"""

import os
import sys
import subprocess
import shlex
import argparse
import time
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import enterprise modules
from monitoring.telemetry import (
    initialize_telemetry, 
    get_telemetry_client, 
    PerformanceMonitor,
    get_health_check
)
from compliance.audit_logging import (
    initialize_audit_logger,
    get_audit_logger,
    ComplianceFramework
)
from governance.data_governance import (
    get_governance_registry,
    DataClassification
)


def run_command(cmd, env=None, cwd=None) -> Tuple[bool, float]:
    """Execute shell command and return status with execution time"""
    print(f"\n{'='*60}")
    print(f"Running: {' '.join(cmd)}")
    print(f"{'='*60}\n")
    
    start_time = time.time()
    result = subprocess.run(cmd, env=env or os.environ, cwd=cwd)
    duration = time.time() - start_time
    
    return result.returncode == 0, duration


def deploy_bundle(target: str, bundle_path: str = None) -> Tuple[bool, float]:
    """Deploy Databricks Asset Bundle and record metrics"""
    start_time = time.time()
    cmd = ["databricks", "bundle", "deploy", "--target", target]
    if bundle_path:
        cmd.extend(["-C", bundle_path])
    
    success, cmd_duration = run_command(cmd)
    total_duration = time.time() - start_time
    
    # Record telemetry
    telemetry = get_telemetry_client()
    if success:
        telemetry.record_event(
            name="bundle_deploy_success",
            properties={
                "target": target,
                "bundle_path": bundle_path or "default",
                "duration_seconds": total_duration
            }
        )
        telemetry.record_metric(
            name="deployment.bundle.duration_seconds",
            value=total_duration,
            properties={"target": target, "status": "success"}
        )
    else:
        telemetry.record_event(
            name="bundle_deploy_failure",
            properties={
                "target": target,
                "bundle_path": bundle_path or "default",
                "duration_seconds": total_duration
            }
        )
        telemetry.record_metric(
            name="deployment.bundle.duration_seconds",
            value=total_duration,
            properties={"target": target, "status": "failure"}
        )
    
    # Record audit log
    audit = get_audit_logger()
    audit.log_pipeline_execution(
        pipeline_name="databricks_bundle_deploy",
        environment=target,
        status="success" if success else "failure",
        details={
            "bundle_path": bundle_path or "default",
            "duration_seconds": total_duration
        }
    )
    
    return success, total_duration


def run_dbt(command: str, target: str = "dev", profile_dir: str = None, **kwargs) -> Tuple[bool, float]:
    """Execute dbt command and record telemetry metrics"""
    start_time = time.time()
    cmd = ["dbt", command, "--target", target]
    
    if profile_dir:
        cmd.extend(["--profiles-dir", profile_dir])
    
    for key, value in kwargs.items():
        if value:
            cmd.extend([f"--{key}", str(value)])
    
    env = os.environ.copy()
    env["DBT_ENV"] = target
    
    success, cmd_duration = run_command(cmd, env=env, cwd="dbt")
    total_duration = time.time() - start_time
    
    # Record telemetry
    telemetry = get_telemetry_client()
    cmd_name = f"dbt_{command}"
    
    if success:
        telemetry.record_event(
            name=f"{cmd_name}_success",
            properties={
                "target": target,
                "duration_seconds": total_duration,
                "selection": kwargs.get("select", "all")
            }
        )
    else:
        telemetry.record_event(
            name=f"{cmd_name}_failure",
            properties={
                "target": target,
                "duration_seconds": total_duration,
                "selection": kwargs.get("select", "all")
            }
        )
    
    # Record performance metric
    telemetry.record_metric(
        name=f"dbt.{command}.duration_seconds",
        value=total_duration,
        properties={
            "target": target,
            "status": "success" if success else "failure"
        }
    )
    
    # Record audit log for dbt operations
    audit = get_audit_logger()
    audit.log_pipeline_execution(
        pipeline_name=f"dbt_{command}",
        environment=target,
        status="success" if success else "failure",
        details={
            "command": command,
            "selection": kwargs.get("select", "all"),
            "duration_seconds": total_duration
        }
    )
    
    return success, total_duration


def should_run_dbt_deps() -> bool:
    """Run dbt deps only when packages are not installed or packages.yml changed."""
    packages_lock = Path("dbt") / "dbt_packages"
    packages_yml = Path("dbt") / "packages.yml"
    if not packages_yml.exists():
        return False
    if not packages_lock.exists():
        return True
    return packages_yml.stat().st_mtime > packages_lock.stat().st_mtime


def main():
    """Main deployment orchestration with enterprise telemetry"""
    # Initialize telemetry and audit logging
    try:
        initialize_telemetry("dbt-databricks-deploy")
        initialize_audit_logger()
    except Exception as e:
        print(f"⚠️  Warning: Failed to initialize telemetry: {e}")
        print("Continuing deployment without full telemetry support\n")
    
    telemetry = get_telemetry_client()
    audit = get_audit_logger()
    
    # Parse arguments
    parser = argparse.ArgumentParser(
        description="Deploy dbt project with Databricks Asset Bundle"
    )
    parser.add_argument(
        "--target",
        choices=["dev", "staging", "prod"],
        default="dev",
        help="Target environment"
    )
    parser.add_argument(
        "--skip-dbt",
        action="store_true",
        help="Skip dbt run/test"
    )
    parser.add_argument(
        "--skip-bundle",
        action="store_true",
        help="Skip Databricks bundle deployment"
    )
    parser.add_argument(
        "--skip-health-check",
        action="store_true",
        help="Skip health checks before deployment"
    )
    parser.add_argument(
        "--bundle-path",
        default=None,
        help="Path to bundle configuration"
    )
    parser.add_argument(
        "--dbt-select",
        default=None,
        help="dbt selection criteria (e.g., 'tag:marts')"
    )
    
    args = parser.parse_args()
    
    # Record deployment start
    deployment_start = datetime.now()
    telemetry.record_event(
        name="deployment_start",
        properties={
            "target": args.target,
            "timestamp": deployment_start.isoformat()
        }
    )
    
    # Perform health checks
    if not args.skip_health_check:
        print(f"\n{'#'*60}")
        print(f"# Performing health checks...")
        print(f"{'#'*60}")
        
        health_check = get_health_check()
        try:
            databricks_ok = health_check.check_databricks_connection()
            schema_ok = health_check.validate_schema(args.target)
            
            if not databricks_ok or not schema_ok:
                print("\n⚠️  Health check failed")
                telemetry.record_event(
                    name="health_check_failure",
                    properties={"target": args.target}
                )
                audit.log_security_event(
                    event_type="deployment_blocked",
                    details={"reason": "health_check_failed"}
                )
                return 1
            else:
                print("\n✅ Health checks passed")
                telemetry.record_event(
                    name="health_check_success",
                    properties={"target": args.target}
                )
        except Exception as e:
            print(f"\n⚠️  Health check error (continuing): {e}")
    
    success = True
    deployment_duration = 0
    
    if not args.skip_dbt:
        print(f"\n{'#'*60}")
        print(f"# Running dbt against {args.target}")
        print(f"{'#'*60}")
        
        # Install dependencies only when needed.
        if should_run_dbt_deps():
            deps_success, deps_duration = run_dbt("deps", args.target, "profiles.yml")
            if not deps_success:
                print("\n❌ dbt deps failed")
                success = False
        else:
            print("\nℹ️  Skipping dbt deps (no package changes detected)")
        
        # Run models
        if success:
            dbt_kwargs = {}
            if args.dbt_select:
                dbt_kwargs["select"] = args.dbt_select
            
            run_success, run_duration = run_dbt("run", args.target, "profiles.yml", **dbt_kwargs)
            if not run_success:
                print("\n❌ dbt run failed")
                success = False
        
        # Run tests
        if success:
            test_success, test_duration = run_dbt("test", args.target, "profiles.yml")
            if not test_success:
                print("\n❌ dbt test failed")
                success = False
    
    if not args.skip_bundle and success:
        print(f"\n{'#'*60}")
        print(f"# Deploying Databricks Bundle to {args.target}")
        print(f"{'#'*60}")
        
        bundle_path = args.bundle_path or f"databricks_bundles/{args.target}"
        
        bundle_success, bundle_duration = deploy_bundle(args.target, bundle_path)
        if not bundle_success:
            print(f"\n❌ Bundle deployment to {args.target} failed")
            success = False
    
    # Record deployment completion
    deployment_end = datetime.now()
    deployment_duration = (deployment_end - deployment_start).total_seconds()
    
    if success:
        print(f"\n{'+'*60}")
        print(f"✅ Deployment to {args.target} completed successfully!")
        print(f"{'+'*60}\n")
        
        telemetry.record_event(
            name="deployment_success",
            properties={
                "target": args.target,
                "duration_seconds": deployment_duration,
                "timestamp": deployment_end.isoformat()
            }
        )
        
        telemetry.record_metric(
            name="deployment.total.duration_seconds",
            value=deployment_duration,
            properties={
                "target": args.target,
                "status": "success"
            }
        )
        
        # Log successful deployment
        audit.log_pipeline_execution(
            pipeline_name="full_deployment",
            environment=args.target,
            status="success",
            details={
                "duration_seconds": deployment_duration,
                "skip_dbt": args.skip_dbt,
                "skip_bundle": args.skip_bundle
            }
        )
        
        return 0
    else:
        print(f"\n{'!'*60}")
        print(f"❌ Deployment to {args.target} failed!")
        print(f"{'!'*60}\n")
        
        telemetry.record_event(
            name="deployment_failure",
            properties={
                "target": args.target,
                "duration_seconds": deployment_duration,
                "timestamp": deployment_end.isoformat()
            }
        )
        
        telemetry.record_metric(
            name="deployment.total.duration_seconds",
            value=deployment_duration,
            properties={
                "target": args.target,
                "status": "failure"
            }
        )
        
        # Log failed deployment
        audit.log_pipeline_execution(
            pipeline_name="full_deployment",
            environment=args.target,
            status="failure",
            details={
                "duration_seconds": deployment_duration,
                "skip_dbt": args.skip_dbt,
                "skip_bundle": args.skip_bundle
            }
        )
        
        return 1


if __name__ == "__main__":
    sys.exit(main())
