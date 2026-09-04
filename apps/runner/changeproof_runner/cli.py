import argparse
import asyncio
import json
import sys
from dataclasses import asdict
from pathlib import Path

from changeproof_runner.git_inspector import get_git_changed_files, inspect_python_file
from changeproof_runner.load_generator import run_local_load
from changeproof_runner.validator import TargetSecurityError, validate_target_url


def run_inspect(args: argparse.Namespace) -> int:
    repo_path = Path(args.repo).resolve()
    changed = get_git_changed_files(repo_path, args.base)
    all_findings = []

    # If git diff found files, inspect them; otherwise inspect all python files in repo
    files_to_check = [repo_path / f for f in changed if f.endswith(".py")]
    if not files_to_check:
        files_to_check = list(repo_path.glob("**/*.py"))

    for py_file in files_to_check:
        findings = inspect_python_file(py_file, repo_path=repo_path, base_ref=args.base)
        all_findings.extend(findings)

    if args.json:
        print(json.dumps({"findings": all_findings, "count": len(all_findings)}, indent=2))
        return 0

    print("ChangeProof Code Change Inspection")
    print(f"Repository: {repo_path}")
    print(f"Base Ref:   {args.base}\n")

    if not all_findings:
        print("No external dependencies detected on request paths.")
        return 0

    print(f"Found {len(all_findings)} performance risk candidate(s):")
    for f in all_findings:
        print(f"  - [{f['method']} {f['path']}] at {f['file']}:{f['line']} -> {f['symbol']}")
    return 0


def run_verify(args: argparse.Namespace) -> int:
    repo_path = Path(args.repo).resolve()
    try:
        validated_target = validate_target_url(args.target)
    except TargetSecurityError as exc:
        print(f"SECURITY ERROR: {exc}", file=sys.stderr)
        return 2

    # Step 1: Inspect local changes
    changed = get_git_changed_files(repo_path, args.base)
    files_to_check = [repo_path / f for f in changed if f.endswith(".py")]
    if not files_to_check:
        files_to_check = list(repo_path.glob("**/*.py"))

    findings = []
    for py_file in files_to_check:
        findings.extend(inspect_python_file(py_file, repo_path=repo_path, base_ref=args.base))

    endpoint = args.endpoint or (findings[0]["path"] if findings else "/dashboard")
    method = findings[0]["method"] if findings else "GET"
    symbol = findings[0]["symbol"] if findings else "external_client"

    if not args.json:
        print("==================================================")
        print("       ChangeProof Performance Verification       ")
        print("==================================================")
        print("TARGET ENVIRONMENT: DEVELOPMENT / LOCAL")
        print(f"Target URL:         {validated_target}")
        print(f"Endpoint:           {method} {endpoint}")
        if findings:
            print(f"Detected Change:    {symbol} at {findings[0]['file']}:{findings[0]['line']}")
        print("\nHypothesis:")
        print("  Peak traffic may saturate downstream capacity and amplify latency")
        print("  Status: UNVERIFIED (Awaiting local load proof)\n")
        print(f"Executing Load:     {args.concurrency} concurrent users, {args.requests} requests...")

    metrics = asyncio.run(
        run_local_load(
            target_url=validated_target,
            method=method,
            endpoint=endpoint,
            concurrency=args.concurrency,
            request_count=args.requests,
        )
    )

    if args.json:
        payload = {
            "target": validated_target,
            "endpoint": f"{method} {endpoint}",
            "findings": findings,
            "metrics": asdict(metrics),
            "verdict": metrics.verdict,
        }
        print(json.dumps(payload, indent=2))
        return 0 if metrics.verdict in ("PROVEN_PASS", "PROVEN_BOTTLENECK") else 1

    print("\nResults:")
    print(f"  Functional Check: {'PASS' if metrics.functional_pass else 'FAIL'} ({metrics.functional_latency_ms} ms)")
    print(f"  p50 Latency:      {metrics.p50_ms} ms")
    print(f"  p95 Latency:      {metrics.p95_ms} ms")
    print(f"  p99 Latency:      {metrics.p99_ms} ms")
    print(f"  Throughput:       {metrics.throughput_rps} rps")
    print(f"  Timeout Rate:     {metrics.timeout_rate * 100:.1f}%")
    print(f"\nObservation:        {metrics.observation}")
    print(f"Verdict:            {metrics.verdict}")
    print("==================================================")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="changeproof",
        description="ChangeProof Local / Enterprise Performance Verification Agent",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # inspect
    inspect_parser = subparsers.add_parser("inspect", help="Inspect local git diff for performance risk facts")
    inspect_parser.add_argument("--repo", default=".", help="Path to local repository (default: .)")
    inspect_parser.add_argument("--base", default="HEAD~1", help="Base git reference (default: HEAD~1)")
    inspect_parser.add_argument("--json", action="store_true", help="Output machine-readable JSON")

    # verify
    verify_parser = subparsers.add_parser("verify", help="Inspect code changes and execute local peak load")
    verify_parser.add_argument("--repo", default=".", help="Path to local repository (default: .)")
    verify_parser.add_argument("--base", default="HEAD~1", help="Base git reference (default: HEAD~1)")
    verify_parser.add_argument("--target", required=True, help="Local/private HTTP target URL (e.g. http://localhost:8001)")
    verify_parser.add_argument("--endpoint", default=None, help="Endpoint path override (e.g. /dashboard)")
    verify_parser.add_argument("--concurrency", type=int, default=50, help="Concurrent workers (default: 50)")
    verify_parser.add_argument("--requests", type=int, default=100, help="Total requests (default: 100)")
    verify_parser.add_argument("--json", action="store_true", help="Output machine-readable JSON")

    args = parser.parse_args()
    if args.command == "inspect":
        sys.exit(run_inspect(args))
    elif args.command == "verify":
        sys.exit(run_verify(args))


if __name__ == "__main__":
    main()
