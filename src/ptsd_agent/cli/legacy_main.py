import sys
import time
import argparse
import threading
import signal
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from ptsd_agent.ui.legacy_display import ProgressiveDisplay
from ptsd_agent.metrics.legacy_collector import MetricsCollector
from ptsd_agent.metrics.legacy_logger import MetricsLogger
from ptsd_agent.execution.legacy_executor import TestExecutor
from ptsd_agent.core.config import load_config
# from ptsd_agent.report_logging import get_log_manager  # TODO: Fix module path

def _signal_handler(signum, frame):
    """Handle Ctrl+C - exit immediately."""
    print("\n\033[0m\033[?25h", end="")  # Reset colors, show cursor
    sys.exit(130)  # Standard exit code for SIGINT

def main():
    # Register signal handler for clean Ctrl+C exit
    signal.signal(signal.SIGINT, _signal_handler)
    parser = argparse.ArgumentParser(description="PTSD Agent - Universal Test Runner")
    parser.add_argument("--phase", "--phases", nargs='*', dest="phase", help="Run specific phases (space separated, e.g. 1 3 4)")
    parser.add_argument("--component", type=str,
                       help="Filter by component name(s). Use comma-separated for multiple (e.g., 'acl,contracts')")
    parser.add_argument("--simulate", action="store_true", help="Skip test execution, show results from last run")
    parser.add_argument("--history", action="store_true", help="Show recent run history")
    parser.add_argument("--detailed-history", action="store_true", help="Show detailed history with phase/component breakdown")
    parser.add_argument("--history-run", type=str, help="Show details for a specific run ID")
    parser.add_argument("--history-limit", type=int, default=10, metavar="N",
                       help="Number of runs to show in history (default: 10)")
    parser.add_argument("--history-since", type=str, metavar="DATE",
                       help="Show runs since DATE (e.g. '2025-12-25', 'today', 'yesterday')")
    parser.add_argument("--parallel", type=int, nargs='?', const=0, default=0, metavar="N",
                       help="Run components in parallel with N workers (default: CPU count, use --sequential to disable)")
    parser.add_argument("--sequential", action="store_const", const=-1, dest="parallel", help="Run components sequentially instead of in parallel")
    parser.add_argument("--collapsed", "--collapse", nargs='*', default=None, dest="collapsed",
                       help="Collapse sections. Use alone or with: 'all', 'discover', 'overview', 'project', 'phases'")
    parser.add_argument("--discover", "--discovery", action="store_true", dest="discover", help="Auto-discover and categorize test files")
    parser.add_argument("--run-tests", action="store_true", help="Run tests (can be combined with --discover)")
    parser.add_argument("--show-logs", action="store_true", help="Show log summary with paths to log files after execution")
    parser.add_argument("--show-files", action="store_true", help="Show detailed test file list by component")
    parser.add_argument("--show-all-phases", action="store_true", default=True, 
                       help="Show all phases from config including those without tests (default: enabled)")
    parser.add_argument("--hide-empty-phases", action="store_true", default=False,
                       help="Hide phases without test units (overrides --show-all-phases)")
    parser.add_argument("--include-dev", action="store_true", default=True, help="Include development tests (default: True, use --no-include-dev to disable)")
    parser.add_argument("--no-include-dev", action="store_false", dest="include_dev", help="Disable development test inclusion")
    parser.add_argument("--coverage-temp-dir", type=str, default=None, 
                       help="Directory for coverage temp files (default: system temp dir)")
    parser.add_argument("--aggregate-coverage", action="store_true", default=None,
                       help="Enable coverage aggregation (overrides config, default: enabled)")
    parser.add_argument("--no-aggregate-coverage", action="store_false", dest="aggregate_coverage",
                       help="Disable coverage aggregation (overrides config)")
    parser.add_argument("--coverage-retention", type=int, default=None,
                       help="Number of coverage runs to retain (-1 = infinite, overrides config)")
    parser.add_argument("--overview", action="store_true",
                       help="Show enriched Phase Overview with project stats and progress indicators")
    parser.add_argument("--from-run",
                       help="Show Phase Overview from a specific historical run (use with --overview)")
    
    # Diagnostics display
    parser.add_argument("--diagnostics", "-d", action="store_true",
                       help="Show detailed diagnostics section with failures, errors, warnings, and skip reasons")
    
    # Test collection accuracy
    parser.add_argument("--accurate", action="store_true", default=True,
                       help="Use pytest collection for accurate test counts (default: enabled)")
    parser.add_argument("--no-accurate", action="store_false", dest="accurate",
                       help="Disable accurate test counting (faster but less precise)")
    args = parser.parse_args()
    
    # Parse phases argument (handle list and commas)
    target_phases = []
    if args.phase:
        for p_arg in args.phase:
            parts = str(p_arg).split(',')
            for part in parts:
                if part.strip():
                    try:
                        target_phases.append(int(part.strip()))
                    except ValueError:
                        parser.error(f"Invalid phase ID: {part}")
    
    # Parse component argument (handle comma-separated values)
    target_components = []
    if args.component:
        parts = str(args.component).split(',')
        for part in parts:
            if part.strip():
                target_components.append(part.strip())
    
    # Interpret parallel argument:
    # -1 = sequential (from --sequential)
    # 0 = parallel with auto worker count (CPU count)
    # >0 = parallel with specific worker count
    import os
    if args.parallel == -1:
        max_workers = 1  # Sequential
        parallel_mode = False
    elif args.parallel == 0:
        max_workers = os.cpu_count() or 4  # Auto
        parallel_mode = True
    else:
        max_workers = args.parallel  # User-specified
        parallel_mode = True
    
    # Initialize logging
    # log_mgr = get_log_manager()  # TODO: Fix module path
    # log_mgr.info("PTSD Agent started", data={"args": vars(args)})
    
    
    # Handle --history / --detailed-history / --history-run
    if args.history or args.detailed_history or args.history_run:
        from ptsd_agent.storage.legacy_history import get_history_store
        history = get_history_store()
        
        CYAN = "\033[96m"
        GREEN = "\033[92m"
        YELLOW = "\033[93m"
        ORANGE = "\033[38;5;208m"
        RED = "\033[91m"
        GRAY = "\033[90m"
        DIM = "\033[2m"
        RESET = "\033[0m"
        
        # Show specific run
        if args.history_run:
            run = history.get_run(args.history_run)
            if not run:
                print(f"\n  {RED}Run '{args.history_run}' not found.{RESET}\n")
                return
            
            print(f"\n{CYAN}Run Details: {run['run_id']}{RESET}\n")
            ts = run['timestamp'][:19].replace('T', ' ')
            git = run.get('git', {})
            overall = run.get('overall', {})
            
            print(f"  {GRAY}Timestamp:{RESET}  {ts}")
            print(f"  {GRAY}Branch:{RESET}     {git.get('branch', 'unknown')} ({git.get('commit', '?')[:8]})")
            print(f"  {GRAY}Duration:{RESET}   {run.get('duration_seconds', 0):.1f}s")
            print()
            
            # Overall metrics
            pass_rate = overall.get('pass_rate', 0)
            status_color = GREEN if pass_rate >= 95 else (YELLOW if pass_rate >= 80 else RED)
            print(f"  {GRAY}Overall:{RESET}")
            print(f"    {status_color}{pass_rate:.1f}%{RESET} pass | {overall.get('coverage', 0):.0f}% cov | {overall.get('total_tests', 0)} tests")
            print(f"    {ORANGE}{overall.get('failures', 0)}{RESET} fail | {RED}{overall.get('errors', 0)}{RESET} err | {GRAY}{overall.get('skipped', 0)} skip | {YELLOW}{overall.get('warnings', 0)} warn{RESET}")
            print()
            
            # Per-phase breakdown
            print(f"  {GRAY}By Phase:{RESET}")
            for phase_id, phase_data in sorted(run.get('phases', {}).items()):
                metrics = phase_data.get('metrics', {})
                p_pass = metrics.get('pass_rate', 0)
                p_color = GREEN if p_pass >= 95 else (YELLOW if p_pass >= 80 else RED)
                print(f"    {CYAN}Phase {phase_id}:{RESET} {phase_data.get('name', '')[:40]}")
                print(f"      {p_color}{p_pass:.1f}%{RESET} | {metrics.get('coverage', 0):.0f}% cov | {metrics.get('total_tests', 0)} tests | {metrics.get('failures', 0)} fail")
                
                # Component details
                for comp_name, comp_data in phase_data.get('components', {}).items():
                    c_pass = comp_data.get('pass_rate', 0)
                    c_color = GREEN if c_pass >= 95 else (YELLOW if c_pass >= 80 else RED)
                    print(f"        {DIM}├─{RESET} {comp_name}: {c_color}{c_pass:.0f}%{RESET} | {comp_data.get('coverage', 0):.0f}% | {comp_data.get('total_tests', 0)} tests")
                print()
            return
        
        # List runs (simple or detailed)
        from datetime import datetime, timedelta
        
        # Parse --history-since if provided
        since_date = None
        if args.history_since:
            since_str = args.history_since.lower()
            if since_str == 'today':
                since_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            elif since_str == 'yesterday':
                since_date = (datetime.now() - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            else:
                try:
                    since_date = datetime.strptime(args.history_since, '%Y-%m-%d')
                except ValueError:
                    print(f"  {RED}Invalid date format: {args.history_since}{RESET}")
                    print(f"  {DIM}Use YYYY-MM-DD, 'today', or 'yesterday'{RESET}")
                    return
        
        # Get runs with limit
        limit = args.history_limit if args.history_limit else 10
        all_runs = history.list_runs(limit=1000)  # Get total count
        total_runs = len(all_runs)
        
        # Filter by date if specified
        if since_date:
            runs = []
            for r in all_runs:
                run_time = datetime.fromisoformat(r['timestamp'][:19])
                if run_time >= since_date:
                    runs.append(r)
            runs = runs[:limit]  # Apply limit after filtering
            filter_str = f"since {args.history_since}"
        else:
            runs = history.list_runs(limit=limit)
            filter_str = f"showing {len(runs)} of {total_runs}"
        
        print(f"\n{CYAN}Recent Test Runs{RESET} {DIM}({filter_str}){RESET}\n")
        if not runs:
            print(f"  {GRAY}No runs found.{RESET}")
        else:
            for run in runs:
                ts = run['timestamp'][:19].replace('T', ' ')
                branch = run.get('git_branch') or 'unknown'
                tests = run.get('total_tests', 0)
                pass_rate = run.get('overall_pass_rate', 0)
                coverage = run.get('overall_coverage', 0)
                failures = run.get('overall_failures', 0)
                errors = run.get('overall_errors', 0)
                
                # Color coding consistent with discovery/test running
                pass_color = GREEN if pass_rate >= 95 else (YELLOW if pass_rate >= 80 else RED)
                cov_color = GREEN if coverage >= 80 else (YELLOW if coverage >= 50 else GRAY)
                fail_color = GREEN if failures == 0 else (YELLOW if failures < 10 else ORANGE)
                err_color = GREEN if errors == 0 else RED
                
                print(f"  {GRAY}{ts}{RESET}  {DIM}[{run['run_id']}]{RESET}  {CYAN}{branch}{RESET}")
                print(f"    {pass_color}{pass_rate:.1f}%{RESET} pass  {DIM}|{RESET}  {cov_color}{coverage:.0f}%{RESET} cov  {DIM}|{RESET}  {CYAN}{tests}{RESET} tests  {DIM}|{RESET}  {fail_color}{failures}{RESET} fail  {DIM}|{RESET}  {err_color}{errors}{RESET} err")
                
                # Show per-phase in detailed mode
                if args.detailed_history:
                    full_run = history.get_run(run['run_id'])
                    if full_run:
                        for phase_id, phase_data in sorted(full_run.get('phases', {}).items()):
                            metrics = phase_data.get('metrics', {})
                            p_pass = metrics.get('pass_rate', 0)
                            p_tests = metrics.get('total_tests', 0)
                            p_fail = metrics.get('failures', 0)
                            p_pass_color = GREEN if p_pass >= 95 else (YELLOW if p_pass >= 80 else RED)
                            p_fail_color = GREEN if p_fail == 0 else (YELLOW if p_fail < 10 else ORANGE)
                            print(f"      {DIM}Phase {phase_id}:{RESET} {p_pass_color}{p_pass:.0f}%{RESET} | {CYAN}{p_tests}{RESET} tests | {p_fail_color}{p_fail}{RESET} fail")
                print()
        
        if not args.detailed_history:
            print(f"  {DIM}Use --detailed-history for per-phase breakdown{RESET}")
            print(f"  {DIM}Use --history-run <id> for full run details{RESET}\n")
        return
    
    # Handle standalone --overview (show last results without running tests)
    if (args.overview or args.from_run) and not args.run_tests and not args.discover:
        from ptsd_agent.storage.legacy_history import get_history_store
        # from ptsd_agent.integrations.legacy_taskmaster import TaskMasterLoader  # TODO: Module doesn't exist
        import shutil
        
        history = get_history_store()
        # Suppress config output during test UI
        os.environ['PTSD_SILENT_CONFIG'] = '1'
        project_config = load_config()
        
        CYAN = "\033[96m"
        GREEN = "\033[92m"
        YELLOW = "\033[93m"
        GRAY = "\033[90m"
        DIM = "\033[2m"
        RED = "\033[91m"
        RESET = "\033[0m"
        term_width = shutil.get_terminal_size().columns
        
        print()
        print(f"  {GRAY}PTSD Agent - Phase Overview{RESET}")
        
        # Determine which run to show
        target_run = None
        if args.from_run:
            # Load specific run by ID
            target_run = history.get_run(args.from_run)
            if not target_run:
                print(f"  {RED}Run '{args.from_run}' not found.{RESET}")
                print(f"  {DIM}Use --history to see available runs.{RESET}")
                print()
                return
            print(f"  {DIM}Showing run: {args.from_run}{RESET}")
        else:
            # Find the most recent run with the most phase data (prefer full runs)
            runs = history.list_runs(limit=10)
            best_run = None
            best_phase_count = 0
            for r in runs:
                run_data = history.get_run(r['run_id'])
                if run_data:
                    phases_count = len(run_data.get('phases', {}))
                    if phases_count > best_phase_count:
                        best_phase_count = phases_count
                        best_run = run_data
                    # If we find a run with all phases, use it
                    if phases_count >= 3:  # At least phases 1-3 with tests
                        break
            
            if best_run:
                target_run = best_run
                run_id = target_run.get('run_id', 'unknown')[:8]
                print(f"  {DIM}Showing best run: {run_id}... ({best_phase_count} phases){RESET}")
            else:
                # Fallback to last run
                if runs:
                    target_run = history.get_run(runs[0]['run_id'])
                print(f"  {DIM}Showing last scan results{RESET}")
        print()
        
        # Display run stats if available
        if target_run:
            overall = target_run.get('overall', {})
            ts = target_run['timestamp'][:19].replace('T', ' ')
            run_id = target_run.get('run_id', 'unknown')
            
            print(f"  {GRAY}Run:{RESET} {run_id[:16]}...  {GRAY}Date:{RESET} {ts}")
            
            total_tests = overall.get('total_tests', 0)
            pass_rate = overall.get('pass_rate', 0)
            coverage = overall.get('coverage', 0)
            failures = overall.get('failures', 0)
            errors = overall.get('errors', 0)
            
            pass_color = GREEN if pass_rate >= 95 else (YELLOW if pass_rate >= 80 else RED)
            cov_color = GREEN if coverage >= 80 else (YELLOW if coverage >= 50 else GRAY)
            
            print(f"  {GRAY}Tests:{RESET} {total_tests} | {GRAY}Pass:{RESET} {pass_color}{pass_rate:.1f}%{RESET} | {GRAY}Coverage:{RESET} {cov_color}{coverage:.0f}%{RESET}", end="")
            if failures > 0 or errors > 0:
                print(f" | {YELLOW}{failures} fail{RESET} | {RED}{errors} err{RESET}")
            else:
                print()
            
            # Show collection info if accurate mode was used
            collection_info = target_run.get('collection_info')
            if collection_info and collection_info.get('errors', 0) > 0:
                ORANGE = "\033[38;5;208m"
                collected = collection_info.get('collected', total_tests)
                import_errors = collection_info.get('errors', 0)
                uncollectable = total_tests - collected if total_tests > collected else 0
                print(f"  {GRAY}Import Errors:{RESET} {ORANGE}{import_errors}{RESET} {GRAY}({uncollectable} tests uncollectable){RESET}")
                
                # Show a few error files
                error_files = collection_info.get('error_files', [])
                if error_files:
                    print(f"  {DIM}Affected files: {', '.join(error_files[:3])}{RESET}", end="")
                    if len(error_files) > 3:
                        print(f"{DIM}, +{len(error_files) - 3} more{RESET}")
                    else:
                        print()
            
            print()
            
            # Per-phase metrics from historical run
            phases_data = target_run.get('phases', {})
        else:
            print(f"  {YELLOW}No test runs found. Run with --run-tests first.{RESET}")
            print()
            phases_data = {}
        
        # Load Task Master data for task-based phases
        # tm_loader = TaskMasterLoader()  # TODO: Disabled
        # tm_summary = tm_loader.load()
        tm_summary = None
        
        task_by_id = {}
        if tm_summary:
            for task in tm_summary.tasks:
                task_by_id[task.id] = task
        
        print(f"{GRAY}Phase Overview{RESET}")
        print()
        
        # Calculate and display phase stats with component breakdown
        all_phases = project_config.phases
        phase_completed = 0
        phase_in_progress = 0
        phase_planned = 0
        
        # Component totals
        total_comp_done = 0
        total_comp_wip = 0
        total_comp_pending = 0
        
        for phase in all_phases:
            p_id = phase['id']
            p_name = phase['name']
            p_status = phase.get('status', '')
            components = phase.get('components', [])
            
            has_test_paths = any(c.get('test_path') for c in components)
            has_taskmaster = any(c.get('taskmaster_id') for c in components)
            
            # Get phase-level metrics from historical run if available
            phase_metrics = phases_data.get(str(p_id), {}).get('metrics', {})
            phase_pass_rate = phase_metrics.get('pass_rate', 0)
            phase_coverage = phase_metrics.get('coverage', 0)
            phase_tests = phase_metrics.get('total_tests', 0)
            
            # Get per-component metrics from historical run
            component_metrics = phases_data.get(str(p_id), {}).get('components', {})
            
            # Component breakdown for this phase
            comp_done = 0
            comp_wip = 0
            comp_pending = 0
            
            if has_test_paths:
                # Phase with test paths - check per-component status from historical data
                for comp in components:
                    c_name = comp.get('name', '')
                    c_metrics = component_metrics.get(c_name, {})
                    c_tests = c_metrics.get('total_tests', 0)
                    c_pass_rate = c_metrics.get('pass_rate', 0)
                    c_status = comp.get('status', '').lower()
                    
                    # Determine component status
                    if 'complete' in c_status or 'done' in c_status:
                        comp_done += 1
                    elif c_tests > 0:
                        # Component has tests run
                        if c_pass_rate >= 100:
                            comp_done += 1  # 100% pass = done
                        else:
                            comp_wip += 1  # Has tests but not 100% = wip
                    elif 'progress' in c_status or 'active' in c_status:
                        comp_wip += 1
                    else:
                        comp_pending += 1
                
                if 'COMPLETE' in p_status.upper() or (comp_done == len(components) and len(components) > 0):
                    status_color = GREEN
                    status_text = "Complete"
                    phase_completed += 1
                elif 'PROGRESS' in p_status.upper() or comp_wip > 0 or comp_done > 0:
                    status_color = YELLOW
                    status_text = "In Progress"
                    phase_in_progress += 1
                else:
                    status_color = GRAY
                    status_text = "Planned"
                    phase_planned += 1
                
                # Show metrics if available
                if phase_tests > 0:
                    p_color = GREEN if phase_pass_rate >= 95 else (YELLOW if phase_pass_rate >= 80 else RED)
                    metrics_str = f" | {p_color}{round(phase_pass_rate)}%{RESET} pass | {round(phase_coverage)}% cov"
                else:
                    metrics_str = ""
                    
            elif has_taskmaster and task_by_id:
                # Phase with Task Master components
                for comp in components:
                    tm_id = comp.get('taskmaster_id')
                    if tm_id and tm_id in task_by_id:
                        task = task_by_id[tm_id]
                        if task.status == 'done':
                            comp_done += 1
                        elif task.status == 'in-progress':
                            comp_wip += 1
                        else:
                            comp_pending += 1
                    elif tm_id is None:
                        comp_pending += 1
                
                total_comps = comp_done + comp_wip + comp_pending
                if comp_done == total_comps and total_comps > 0:
                    status_color = GREEN
                    status_text = "Complete"
                    phase_completed += 1
                elif comp_done > 0 or comp_wip > 0:
                    status_color = YELLOW
                    status_text = "In Progress"
                    phase_in_progress += 1
                else:
                    status_color = GRAY
                    status_text = "Planned"
                    phase_planned += 1
                metrics_str = ""
            elif len(components) == 0:
                # No components defined
                status_color = GRAY
                status_text = "Not Planned"
                phase_planned += 1
                metrics_str = ""
            else:
                status_color = GRAY
                status_text = "Planned"
                phase_planned += 1
                comp_pending = len(components)
                metrics_str = ""
            
            # Accumulate component totals
            total_comp_done += comp_done
            total_comp_wip += comp_wip
            total_comp_pending += comp_pending
            
            # Build component breakdown string with new format [ ◐ 4 | ✓ 3 ]
            if comp_done + comp_wip + comp_pending > 0:
                comp_parts = []
                if comp_wip > 0:
                    comp_parts.append(f"{YELLOW}◐ {comp_wip}{RESET}")
                if comp_done > 0:
                    comp_parts.append(f"{GREEN}✓ {comp_done}{RESET}")
                if comp_pending > 0:
                    comp_parts.append(f"{GRAY}○ {comp_pending}{RESET}")
                comp_str = "|".join(comp_parts)
            else:
                comp_str = f"{GRAY}n/a{RESET}"
            
            print(f"  {DIM}├─{RESET} Phase {p_id}: {status_color}{status_text}{RESET} [{comp_str}]{metrics_str}")
        
        print()
        print(f"  {DIM}Phases:{RESET} {GREEN}{phase_completed}{RESET} complete | {YELLOW}{phase_in_progress}{RESET} active | {GRAY}{phase_planned} planned{RESET}")
        print(f"  {DIM}Components:{RESET} {GREEN}✓ {total_comp_done}{RESET} done | {YELLOW}◐ {total_comp_wip}{RESET} wip | {GRAY}○ {total_comp_pending}{RESET} pending")
        print()
        print(f"{DIM}{CYAN}{'▰' * term_width}{RESET}")
        return
    
    # Handle discovery mode
    if args.discover and not args.run_tests:
        # from ptsd_agent.ui.discovery import run_discovery  # TODO: Module doesn't exist
        print("Discovery mode temporarily disabled - module not found")
        return
    
    # Handle run-tests - always show discovery first (expanded by default)
    discovery_results = None
    if args.run_tests:
        # from ptsd_agent.ui.discovery import run_discovery_with_tests  # TODO: Module doesn't exist
        print("Run-tests mode temporarily disabled - module not found")
        print("Running tests directly without discovery...")
        # Continue to normal test execution
        discovery_results = None

    # Validate arguments
    if target_components and not target_phases:
        parser.error("--component requires --phase to be specified (component names can be identical across phases)")

    # Load project configuration from .ptsd.yaml
    project_config = load_config(".")
    
    # Build phase_configs from loaded config
    # Build phase_configs from loaded config will be done after args parsing
    pass

    # Parse collapse configuration
    collapse_config = {
        "project": False,
        "phases": set()
    }
    
    if args.collapsed is not None:
        # --collapsed with no args means collapse all
        if len(args.collapsed) == 0 or 'all' in args.collapsed:
            collapse_config["project"] = True
            collapse_config["phases"] = set([1, 2, 5, 7])  # All phases
        else:
            if 'project' in args.collapsed:
                collapse_config["project"] = True
            if 'phases' in args.collapsed:
                collapse_config["phases"] = set([1, 2, 5, 7])  # All phases
            else:
                # Parse specific phase IDs
                for arg in args.collapsed:
                    try:
                        phase_id = int(arg)
                        collapse_config["phases"].add(phase_id)
                    except ValueError:
                        pass  # Ignore non-numeric args

    # Load coverage configuration
    import yaml
    import uuid
    coverage_config = {}
    config_path = Path(".ptsd.yaml")
    if config_path.exists():
        with open(config_path) as f:
            full_config = yaml.safe_load(f)
            coverage_config = full_config.get('coverage', {})
    
    # Determine if coverage aggregation is enabled
    # Priority: CLI args > config file > default (True)
    if args.aggregate_coverage is not None:
        coverage_enabled = args.aggregate_coverage
    else:
        coverage_enabled = coverage_config.get('enabled', True)
    
    # Determine coverage retention
    if args.coverage_retention is not None:
        coverage_retention = args.coverage_retention
    else:
        coverage_retention = coverage_config.get('retention_runs', -1)
    
    # Generate run_id early for coverage tracking
    run_id = str(uuid.uuid4())[:8]
    
    # Initialization
    collector = MetricsCollector()
    display = ProgressiveDisplay("RAGE", collector=collector)
    logger = MetricsLogger()
    
    # Initialize executor with coverage storage if enabled
    if coverage_enabled:
        coverage_storage_dir = str(Path(".ptsd") / "coverage" / "raw")
        executor = TestExecutor(
            collector, 
            coverage_temp_dir=args.coverage_temp_dir,
            coverage_storage_dir=coverage_storage_dir,
            run_id=run_id
        )
    else:
        executor = TestExecutor(collector, coverage_temp_dir=args.coverage_temp_dir)
    
    render_lock = threading.Lock()
    
    # Check simulation mode (use historical data instead of running tests)
    simulation_mode = args.simulate

    # project_config was already loaded earlier (around line 74)
    
    # Build phase_configs from loaded config
    # Build phase_configs from loaded config - SINGLE SOURCE OF TRUTH
    phase_configs = {}
    # Experimental: Force include components with discovered tests
    forced_test_paths = {} # phase_id -> comp_name -> path
    
    # Check config or CLI override
    should_include_dev = getattr(project_config, 'include_dev_tests', False) or args.include_dev
    
    if should_include_dev and 'discovery_results' in locals() and discovery_results is not None and 'categorized' in discovery_results:
        categorized = discovery_results['categorized']
        for p_id_val, comps in categorized.items():
            for c_name_val, t_files in comps.items():
                if t_files:
                     path = t_files[0].path.parent
                     forced_test_paths.setdefault(p_id_val, {})[c_name_val] = str(path)

    for phase in project_config.phases:
        raw_comps = phase.get('components', [])
        
        # Inject forced paths into config in-memory
        if phase['id'] in forced_test_paths:
             for c_name_f, t_path_f in forced_test_paths[phase['id']].items():
                 for rc in raw_comps:
                     if rc.get('name') == c_name_f and 'test_path' not in rc:
                         rc['test_path'] = t_path_f

        # Strict filtering: testable ONLY if test_path explicitly exists
        testable = [c['name'] for c in raw_comps if 'test_path' in c]
        all_comps = [c['name'] for c in raw_comps]
        
        phase_configs[phase['id']] = {
            'name': phase['name'],
            'components': testable,  # Only components with tests
            'all_components': all_comps,
            'raw_components': raw_comps
        }

    # Only include phases that have components with test_path (actual tests)
    # Phases with only taskmaster_id components are excluded from test execution
    def has_testable_components(phase_config):
        return len(phase_config.get('components', [])) > 0
    
    # Determine which phases to show based on CLI flags
    if args.hide_empty_phases:
        # Old behavior: only show phases with testable components
        active_phases = [p_id for p_id in phase_configs.keys() if has_testable_components(phase_configs[p_id])]
    else:
        # New default: show all phases from config
        active_phases = sorted(phase_configs.keys())
    
    if target_phases:
        # Filter active phases to only those requested
        # Check if requested phases exist
        valid_requested = []
        for p_id in target_phases:
            if p_id in phase_configs:
                valid_requested.append(p_id)
            else:
                print(f"Warning: Phase {p_id} not found in configuration.")
        
        if valid_requested:
             active_phases = sorted(list(set(valid_requested)))
        else:
             print("No valid phases requested.")
             return

    # Initialize Global State
    state = {
        "overall_progress": 0,
        "mode": "running",
        "phases": {},
        "current_test": None
    }

    # Load Task Master data for non-testable components
    # from ptsd_agent.integrations.legacy_taskmaster import TaskMasterLoader  # TODO: Module doesn't exist
    # tm_loader = TaskMasterLoader(project_root=".")  # Use current directory
    # tm_summary = tm_loader.load() if tm_loader.exists() else None
    tm_summary = None  # Temporarily disabled
    
    # Build task ID to status mapping
    tm_task_map = {}
    if tm_summary:
        for task in tm_summary.tasks:
            tm_task_map[str(task.id)] = task.phase_status  # Returns: "planned", "ready", "in-progress", "completed"
            
    from ptsd_agent.core.status_logic import determine_component_status, determine_phase_status
    
    for p_id in active_phases:
        config = phase_configs[p_id]
        testable_comps = config.get("components", [])  # Only includes components with test_path
        all_comps = config.get("all_components", [])  # All components including Task Master ones
        raw_comps = config.get("raw_components", [])  # Raw component configs with taskmaster_id
        
        # Filter by component(s) if specified
        if target_components:
            # Filter to only include specified components
            testable_comps = [c for c in testable_comps if c in target_components]
            all_comps = [c for c in all_comps if c in target_components]
            raw_comps = [c for c in raw_comps if c.get('name') in target_components]
            
            # If no matching component found in this phase, skip it
            if not testable_comps and not all_comps:
                continue
        
        # Calculate status for all components first
        components_dict = {}
        comp_statuses = []
        
        # 1. Process Testable Components
        for c_name in testable_comps:
            # Initially no metrics -> determined as 'in progress' by logic if has_tests=True
            status = determine_component_status(has_tests=True, metrics=None, tm_status=None)
            components_dict[c_name] = {
                "progress": 0,
                "status": "pending", # Internal execution status
                "current_test": None,
                "display_status": status, # Logic-determined status
                "taskmaster_component": False
            }
            comp_statuses.append(status)

        # 2. Process Task Master Components (always add them alongside testable ones)
        # Get all component names that should be added as Task Master components
        tm_component_names = [c for c in all_comps if c not in testable_comps]
        
        for comp_name in tm_component_names:
            # Find taskmaster_id
            tm_id = None
            for rc in raw_comps:
                if rc.get("name") == comp_name and "taskmaster_id" in rc:
                    tm_id = rc["taskmaster_id"]
                    break
            
            tm_status = tm_task_map.get(str(tm_id), "not planned") if tm_id else "not planned"
            
            # Determine status using shared logic (has_tests=False)
            status = determine_component_status(has_tests=False, metrics=None, tm_status=tm_status)
            
            components_dict[comp_name] = {
                "progress": 0,
                "status": "taskmaster",
                "current_test": None,
                "taskmaster_component": True,
                "taskmaster_status": status, # Use the logic-determined status
                "display_status": status
            }
            comp_statuses.append(status)
                
        # 3. Determine Phase Mode/Status from components
        # If no components (Phases 4-7), status logic naturally handles empty lists if we pass defaults?
        # Actually logic expects statuses.
        if not all_comps:
             # Empty phase -> Check config override or default to planned
             phase_status_text = project_config.phases[p_id - 1].get("status", "") if p_id <= len(project_config.phases) else ""
             phase_mode = "not planned"
        else:
            phase_mode = determine_phase_status(comp_statuses)

        state["phases"][p_id] = {
            "name": config["name"],
            "progress": 0,
            "mode": phase_mode, # Now using standardized statuses like 'in progress', 'ready'
            "components": components_dict,
            "has_tests": len(testable_comps) > 0,  # Track if phase has testable components
            "has_taskmaster": not testable_comps and len(all_comps) > 0  # Track if phase has Task Master components
        }

    def render_all():
        with render_lock:
            display.next_frame()  # Advance animations
            display.clear_screen()
            
            # Build component list for aggregation (needed for header color inheritance)
            all_components = []
            for p_id in active_phases:
                if p_id in state["phases"]:
                    all_components.extend(list(state["phases"][p_id]["components"].keys()))
            
            # Header inherits color from all components
            display.build_header(len(active_phases), mode=state["mode"], all_components=all_components)
            
            # Determine project triangle state
            project_triangle = "collapsed" if collapse_config["project"] else "expanded"
            
            # Count total running components for project blinking
            total_running_count = sum(
                1 for p_id in active_phases
                for c_name, c_state in state["phases"][p_id]["components"].items()
                if c_state.get("status") == "running"
            )
            
            # Collect running test names for collapsed display (with phase/component context)
            running_tests = []
            if collapse_config["project"]:
                for p_id in active_phases:
                    for c_name, c_state in state["phases"][p_id]["components"].items():
                        current = c_state.get("current_test")
                        if current and c_state.get("status") == "running":
                            from ptsd_agent.ui.theme import GRAY, CYAN, DIM, RESET
                            # Show: Phase N/component: test_name (washed-out blue)
                            activity_text = f"{DIM}{CYAN}P{p_id}/{c_name}::{current}{RESET}"
                            running_tests.append(activity_text)
            
            display.build_project_line(
                active_phases=active_phases, 
                progress_pct=state["overall_progress"], 
                mode=state["mode"], 
                triangle=project_triangle,
                phase_names={p_id: list(state["phases"][p_id]["components"].keys()) for p_id in active_phases},
                running_count=total_running_count,
                current_test=running_tests if running_tests else None
            )
            
            # Only render phases if project is not collapsed
            if not collapse_config["project"]:
                for p_id in active_phases:
                    p_state = state["phases"][p_id]
                    is_last_phase = (p_id == active_phases[-1])
                    comp_list = list(p_state["components"].keys())
                    
                    # Determine phase triangle state
                    phase_triangle = "collapsed" if p_id in collapse_config["phases"] else "expanded"
            # If no components, use "none" for no triangle
                    if not comp_list:
                        phase_triangle = "none"
                    
                    # Count running components in this phase for blinking
                    phase_running_count = sum(
                        1 for c in comp_list 
                        if p_state["components"][c].get("status") == "running"
                    )
                    
                    display.build_phase_line(
                        p_id, p_state["name"], 
                        progress_pct=p_state["progress"], 
                        mode=p_state["mode"],
                        is_last=is_last_phase,
                        current_test=p_state.get("current_test"),
                        triangle=phase_triangle,
                        components=comp_list,
                        running_count=phase_running_count
                    )
                    
                    # Only render components if:
                    # 1. Phase has testable components (comp_list not empty)
                    # 2. Phase is not collapsed
                    if comp_list and p_id not in collapse_config["phases"]:
                        for c_idx, c_name in enumerate(comp_list):
                            c_state = p_state["components"][c_name]
                            is_last_comp = (c_idx == len(comp_list) - 1)
                            display.build_component_line(
                                c_name, is_last_comp, 
                                progress_pct=c_state["progress"],
                                status=c_state["status"],
                                mode="running" if c_state["status"] != "complete" else "completed",
                                is_last_phase=is_last_phase,
                                current_test=c_state.get("current_test"),
                                taskmaster_status=c_state.get("taskmaster_status")  # Pass Task Master status
                            )
            
            # Count currently running components for blinking blocks
            running_count = sum(
                1 for p_id in active_phases 
                for c_name, c_state in state["phases"][p_id]["components"].items()
                if c_state.get("status") == "running"
            )
            # Use at least 1 if any component is running, otherwise use the count
            active_count = max(1, running_count)
            
            if state["mode"] == "completed":
                display.build_bottom_bar(progress_pct=100, mode="completed", active_count=0)
            else:
                display.build_bottom_bar(state["overall_progress"], "running", active_count=active_count)
                
            display.render()

    def run_comp_task(p_id, c_name, comps_finished_ref):
        p_state = state["phases"][p_id]
        c_state = p_state["components"][c_name]
        
        # Skip Task Master components (they don't run tests)
        if c_state.get("taskmaster_component"):
            with render_lock:
                comps_finished_ref[0] += 1
            render_all()
            return

        c_state["status"] = "running"
        c_state["progress"] = 0
        c_state["current_test"] = f"Initializing..."
        render_all()

        # Simulation Mode: Load from history instead of running tests
        if simulation_mode:
            from ptsd_agent.storage.legacy_history import get_history_store
            history = get_history_store()
            historical = history.get_latest_run()
            
            if historical and str(p_id) in historical.get("phases", {}):
                phase_hist = historical["phases"][str(p_id)]
                comp_hist = phase_hist.get("components", {}).get(c_name, {})
                
                # Apply historical metrics
                c_state["coverage"] = comp_hist.get("coverage", 0)
                c_state["warnings"] = comp_hist.get("warnings", 0)
                c_state["failures"] = comp_hist.get("failures", 0)
                c_state["errors"] = comp_hist.get("errors", 0)
                c_state["skipped"] = comp_hist.get("skipped", 0)
                c_state["total"] = comp_hist.get("total_tests", 0)
                c_state["pass_rate"] = comp_hist.get("pass_rate", 0)
                c_state["progress"] = 100
                c_state["current_test"] = "[Historical]"
                c_state["mode"] = "completed"
                
                # Update collector with historical data
                comp_metrics = collector.get_component(c_name)
                comp_metrics.coverage = comp_hist.get("coverage", 0)
                comp_metrics.warnings = comp_hist.get("warnings", 0)
                comp_metrics.failed = comp_hist.get("failures", 0)
                comp_metrics.errors = comp_hist.get("errors", 0)
                comp_metrics.skipped = comp_hist.get("skipped", 0)
                comp_metrics.passed = comp_hist.get("total_tests", 0) - comp_hist.get("failures", 0) - comp_hist.get("errors", 0) - comp_hist.get("skipped", 0)
                comp_metrics.discovered_total = comp_hist.get("total_tests", 0)
                
                render_all()
                return  # Skip actual test execution
            else:
                c_state["current_test"] = "[No history]"
                c_state["progress"] = 100
                c_state["mode"] = "completed"
                render_all()
                return
        else:
            # Real mode: show initializing with component name
            c_state["current_test"] = f"Initializing {c_name}…"
            render_all()

        # Define callback to update current test in real-time
        def update_current_test(test_name):
            # Keep TestClass::test_name format for context
            if "::" in test_name:
                parts = test_name.split("::")
                # Keep last two parts (class and method) if available
                test_name = "::".join(parts[-2:]) if len(parts) >= 2 else parts[-1]
            c_state["current_test"] = test_name  # Just the test name, display.py adds formatting
            
            # Update component progress: executed / its own discovered total = its own 100%
            comp_data = collector.get_component(c_name)
            if comp_data and comp_data.discovered_total > 0:
                executed = comp_data.passed + comp_data.failed + comp_data.errors + comp_data.skipped
                c_state["progress"] = int((executed / comp_data.discovered_total) * 100)
            
            # Update phase progress: phase_executed / phase_total = phase's own 100%
            phase_executed = 0
            phase_total = 0
            for cn in p_state["components"].keys():
                cd = collector.get_component(cn)
                if cd:
                    phase_executed += cd.passed + cd.failed + cd.errors + cd.skipped
                    phase_total += cd.discovered_total
            p_state["progress"] = int((phase_executed / phase_total) * 100) if phase_total > 0 else 0
            
            # Update project progress: all_executed / all_total = project's own 100%
            total_executed = 0
            total_tests = 0
            for pid in active_phases:
                ps = state["phases"][pid]
                for cn in ps["components"].keys():
                    cd = collector.get_component(cn)
                    if cd:
                        total_executed += cd.passed + cd.failed + cd.errors + cd.skipped
                        total_tests += cd.discovered_total
            state["overall_progress"] = int((total_executed / total_tests) * 100) if total_tests > 0 else 0

        # Execute with component-specific test path from config
        test_path = project_config.get_component_test_path(p_id, c_name)
        executor.run_component(p_id, c_name, test_path=test_path, simulation=simulation_mode, callback=update_current_test)

        # Post-Execution Update
        c_state["status"] = "complete"
        # Component is 100% complete when done (all its own tests executed)
        c_state["progress"] = 100
        c_state["current_test"] = None
        
        with render_lock:
            comps_finished_ref[0] += 1
            
            # Update phase progress: phase_executed / phase_total = phase's own 100%
            phase_executed = 0
            phase_total = 0
            for comp_name in p_state["components"].keys():
                comp_data = collector.get_component(comp_name)
                if comp_data:
                    phase_executed += comp_data.passed + comp_data.failed + comp_data.errors + comp_data.skipped
                    phase_total += comp_data.discovered_total
            p_state["progress"] = int((phase_executed / phase_total) * 100) if phase_total > 0 else 0
            
            # Update project progress: all_executed / all_total = project's own 100%
            total_executed = 0
            total_tests = 0
            for pid in active_phases:
                ps = state["phases"][pid]
                for cn in ps["components"].keys():
                    cd = collector.get_component(cn)
                    if cd:
                        total_executed += cd.passed + cd.failed + cd.errors + cd.skipped
                        total_tests += cd.discovered_total
            state["overall_progress"] = int((total_executed / total_tests) * 100) if total_tests > 0 else 0
            
        render_all()

    # Animation thread flag
    animation_running = [True]
    
    def animation_loop():
        """Background thread for smooth animation refresh"""
        while animation_running[0]:
            if state["mode"] != "completed":
                render_all()
            time.sleep(0.1)  # 100ms refresh rate
    
    # Phase 2 optimization: Discovery handled by executor.discover_all_components()
    # Orphaned discovery UI code removed (ui.discovery module doesn't exist)
    # Test execution continues below with Phase 1+2 features displayed
    
    # Prepare for dynamic UI
    import shutil
    # Standardize width across all UI components
    width = max(40, shutil.get_terminal_size().columns - 1)
    
    print() # Space before animation
        
    # Initialize display for in-place rendering
    display.last_line_count = 0
    # Ensure it uses current width logic
    display.term_width = width
        
        
    # Start animation thread AFTER initial render is complete
    animation_thread = threading.Thread(target=animation_loop, daemon=True)
    animation_thread.start()
    
    try:
        # Execution loop
    total_comps = sum(len(phase_configs[p]["components"]) for p in active_phases) or 1
    comps_finished_ref = [0]

    def run_phase(p_id):
        """Run all components in a phase"""
        p_state = state["phases"][p_id]
        original_mode = p_state["mode"]
        p_state["mode"] = "running"
            
        components = list(p_state["components"].keys())
        if not components:
            p_state["progress"] = 100
            p_state["mode"] = original_mode
            return

        if parallel_mode:
            # Run components in parallel within phase
            comp_workers = min(len(components), max_workers)
            with ThreadPoolExecutor(max_workers=comp_workers) as pool:
                futures = [pool.submit(run_comp_task, p_id, c_name, comps_finished_ref) for c_name in components]
                for f in futures: f.result()
        else:
            for c_name in components:
                run_comp_task(p_id, c_name, comps_finished_ref)

        p_state["mode"] = "completed" if p_state.get("has_tests") else original_mode
        
    if parallel_mode:
        # Parallel mode: run ALL phases concurrently
        phase_workers = min(len(active_phases), max_workers)
        with ThreadPoolExecutor(max_workers=phase_workers) as phase_pool:
            phase_futures = [phase_pool.submit(run_phase, p_id) for p_id in active_phases]
            for f in phase_futures: f.result()
    else:
        # Sequential mode: run phases one by one
        for p_id in active_phases:
            run_phase(p_id)

    # Final Transition
    animation_running[0] = False  # Stop animation thread
    time.sleep(0.15)  # Wait for animation thread to exit
    state["mode"] = "completed"
    summary = collector.get_summary()
    state["overall_progress"] = 100  # 100% complete when all tests finish
    render_all()
        
    # Log results
    logger.log_snapshot(summary, collector.components)
        
    # Save run history (JSON + SQLite)
    from ptsd_agent.storage.legacy_history import get_history_store
    history = get_history_store()
        
    # Build comprehensive run state for history
    run_state = {
        "duration_seconds": summary.get("duration", 0),
        "phases_requested": active_phases,
        "parallel": parallel_mode,
        "max_workers": max_workers,
        "overall_coverage": sum(c.coverage for c in collector.components.values()) / max(len(collector.components), 1),
        "overall_warnings": summary.get("warnings", sum(c.warnings for c in collector.components.values())),
        "overall_failures": summary.get("failed", 0),
        "overall_errors": summary.get("errors", 0),
        "overall_skipped": summary.get("skipped", 0),
        "overall_tests": summary.get("total", 0),
        "overall_pass_rate": summary.get("pass_rate", 0),
        "overall_progress": 100,
        "phases": {}
    }
        
    # Add collection_info from discovery if accurate mode was used
    if discovery_results and 'collection_info' in discovery_results:
        run_state['collection_info'] = discovery_results['collection_info']
        
    # Build phase data
    for p_id in active_phases:
        p_state = state["phases"][p_id]
        phase_config = phase_configs.get(p_id, {})
        phase_metrics = {
            "name": phase_config.get("name", f"Phase {p_id}"),
            "status": p_state.get("mode", "completed"),
            "coverage": 0,
            "warnings": 0,
            "failures": 0,
            "errors": 0,
            "skipped": 0,
            "total_tests": 0,
            "pass_rate": 0,
            "components": {}
        }
            
        # Aggregate from components
        coverage_count = 0  # Track components with actual coverage data
        for c_name in p_state["components"]:
            metrics = collector.components.get(c_name)
            if metrics:
                # Get diagnostics limits from config
                diag_config = project_config.get_diagnostics_config()
                limits = diag_config["diagnostics_limits"]
                    
                comp_data = {
                    "coverage": metrics.coverage,
                    "warnings": metrics.warnings,
                    "failures": metrics.failed,
                    "errors": metrics.errors,
                    "skipped": metrics.skipped,
                    "total_tests": metrics.total,
                    "pass_rate": metrics.pass_rate,
                    "progress": 100,
                    "status": "completed",
                    "test_path": project_config.get_component_test_path(p_id, c_name),
                    # DIAGNOSTIC DETAILS: Store with configurable limits
                    "failure_details": [
                        {"test": f["test_name"], "reason": f["reason"], "location": f["location"]}
                        for f in metrics.failures[:limits["max_failures"]]
                    ],
                    "error_details": [
                        {"test": e["test_name"], "error_type": e["error_type"], "message": e["message"]}
                        for e in metrics.test_errors[:limits["max_errors"]]
                    ],
                    "warning_details": [
                        {"category": w["category"], "message": w["message"], "location": w["location"]}
                        for w in metrics.warning_details[:limits["max_warnings"]]
                    ],
                    "skipped_details": [
                        {"test": s["test_name"], "reason": s["reason"], "marker": s["marker"]}
                        for s in metrics.skipped_tests[:limits["max_skipped"]]
                    ],
                }
                phase_metrics["components"][c_name] = comp_data
                # Only include components with actual coverage data (excludes YAML-only like contracts)
                # This matches the display.py _get_aggregated_metrics logic (line 165-167)
                if metrics.coverage is not None and metrics.coverage >= 0:
                    phase_metrics["coverage"] += metrics.coverage
                    coverage_count += 1
                phase_metrics["warnings"] += metrics.warnings
                phase_metrics["failures"] += metrics.failed
                phase_metrics["errors"] += metrics.errors
                phase_metrics["skipped"] += metrics.skipped
                phase_metrics["total_tests"] += metrics.total
            
        if coverage_count > 0:
            phase_metrics["coverage"] /= coverage_count
        if phase_metrics["components"]:
            total_executed = phase_metrics["total_tests"] - phase_metrics["skipped"]
            passed = total_executed - phase_metrics["failures"] - phase_metrics["errors"]
            phase_metrics["pass_rate"] = (passed / total_executed * 100) if total_executed > 0 else 0
            
        run_state["phases"][p_id] = phase_metrics
        
    # Build file details
    file_details = {}
    for c_name, comp_metrics in collector.components.items():
        file_details[c_name] = {}
        # Group tests by file (simplified - just counts)
        for test in comp_metrics.tests:
            # Extract file from test name if possible
            file_key = test.name.split("::")[0] if "::" in test.name else "unknown"
            if file_key not in file_details[c_name]:
                file_details[c_name][file_key] = {
                    "test_count": 0, "passed": 0, "failed": 0, "errors": 0, "skipped": 0
                }
            file_details[c_name][file_key]["test_count"] += 1
            if test.status == "passed":
                file_details[c_name][file_key]["passed"] += 1
            elif test.status == "failed":
                file_details[c_name][file_key]["failed"] += 1
            elif test.status == "error":
                file_details[c_name][file_key]["errors"] += 1
            elif test.status == "skipped":
                file_details[c_name][file_key]["skipped"] += 1
        
    # Save to history (both JSON and SQLite)
    history_run_id = history.save_run(run_state, file_details=file_details)
    log_mgr.debug(f"Saved run history: {history_run_id}")
        
    # Aggregate coverage if enabled
    # TODO: Re-enable once coverage_aggregator.py is implemented
    # if coverage_enabled and not simulation_mode:
    #     from ptsd_agent.coverage_aggregator import get_coverage_aggregator
    #     
    #     aggregator = get_coverage_aggregator()
    #     
    #     # Get coverage files collected during test execution
    #     coverage_files = executor.get_coverage_files()
    #     
    #     if coverage_files:
    #         log_mgr.info(f"Aggregating coverage from {len(coverage_files)} component(s)")
    #         
    #         # Combine coverage files
    #         combined_file = aggregator.combine_coverage_files(run_id)
    #         
    #         if combined_file:
    #             # Generate reports
    #             formats = []
    #             if coverage_config.get('generate_html', True):
    #                 formats.append('html')
    #             if coverage_config.get('generate_xml', True):
    #                 formats.append('xml')
    #             if coverage_config.get('generate_json', True):
    #                 formats.append('json')
    #             
    #             reports = aggregator.generate_reports(run_id, formats=formats)
    #             
    #             # Display coverage report paths
    #             if reports.get('html'):
    #                 from ptsd_agent.ui.theme import CYAN, DIM, RESET
    #                 print(f"\n{CYAN}Coverage Reports:{RESET}")
    #                 print(f"  {DIM}HTML:{RESET} .ptsd/coverage/reports/{run_id}/htmlcov/index.html")
    #                 if reports.get('xml'):
    #                     print(f"  {DIM}XML: {RESET} .ptsd/coverage/reports/{run_id}/coverage.xml")
    #                 if reports.get('json'):
    #                     print(f"  {DIM}JSON:{RESET} .ptsd/coverage/reports/{run_id}/coverage.json")
    #                 print()
    #         
    #         # Cleanup old coverage if retention is set
    #         if coverage_retention > 0:
    #             deleted = aggregator.cleanup_old_coverage(keep_runs=coverage_retention)
    #             if deleted > 0:
    #                 log_mgr.info(f"Cleaned up {deleted} old coverage run(s)")
        
    # Display log summary if requested
    if args.show_logs:
        log_mgr.info("Execution completed", data={"summary": summary})
        # Build discovery stats from discovery_results if available
        discovery_stats = None
        collection_info = None
        if discovery_results:
            discovery_stats = {
                'total_files': len(discovery_results.get('test_files', [])),
                'total_tests': discovery_results.get('total_tests', 0)
            }
            # Get collection info for accurate counts when --accurate was used
            collection_info = discovery_results.get('collection_info')
            
        # Load baseline for delta comparison when targeting specific phases
        baseline_summary = None
        if target_phases:
            from ptsd_agent.storage.legacy_history import get_history_store
            history = get_history_store()
            # Find baseline run that wasn't targeting specific phases (full run)
            all_runs = history.get_all_runs(limit=20)
            for run in all_runs:
                if run.get('run_id') != history.get_latest_run().get('run_id'):
                    # Use first previous run as baseline
                    phases_data = run.get('phases', {})
                    if phases_data:
                        baseline_summary = {'passed': 0, 'failed': 0, 'errors': 0, 'skipped': 0}
                        for p_id in target_phases:
                            p_metrics = phases_data.get(str(p_id), {}).get('metrics', {})
                            baseline_summary['passed'] += p_metrics.get('passed', 0)
                            baseline_summary['failed'] += p_metrics.get('failures', 0)
                            baseline_summary['errors'] += p_metrics.get('errors', 0)
                            baseline_summary['skipped'] += p_metrics.get('skipped', 0)
            
        log_mgr.display_log_summary(
            show_paths=True, 
            test_summary=summary,
            discovery_stats=discovery_stats,
            baseline_summary=baseline_summary,
            targeted_phases=target_phases if target_phases else None,
            collection_info=collection_info
        )
        
    # Display test files by component if requested
    if args.show_files:
        GRAY = "\033[90m"
        CYAN = "\033[96m"
        RESET = "\033[0m"
        DIM = "\033[2m"
            
        # Section header (no top bar)
        print()
        print(f"{GRAY}Test Files by Component{RESET}")
        print()
            
        for p_id in active_phases:
            phase_name = phase_configs.get(p_id, {}).get('name', f'Phase {p_id}')
            print(f"  {CYAN}{phase_name}{RESET}")
                
            p_state = state["phases"][p_id]
            for c_name in p_state["components"].keys():
                test_path = project_config.get_component_test_path(p_id, c_name)
                # Skip components with no test path configured (Task Master components)
                if not test_path:
                    c_state = p_state["components"][c_name]
                    if c_state.get("taskmaster_component"):
                        print(f"    {GRAY}├─ {c_name}:{RESET} [Task Master - no tests]")
                    else:
                        print(f"    {GRAY}├─ {c_name}:{RESET} [no test path configured]")
                    continue
                path = Path(test_path)
                if path.exists():
                    test_files = list(path.rglob('test_*.py'))
                    print(f"    {GRAY}├─ {c_name}:{RESET} {len(test_files)} files")
                    print(f"    {DIM}│  Path: {path.absolute()}{RESET}")
                    # Show first 3 files as examples
                    for tf in test_files[:3]:
                        print(f"    {DIM}│    - {tf.name}{RESET}")
                    if len(test_files) > 3:
                        print(f"    {DIM}│    ... and {len(test_files) - 3} more{RESET}")
                else:
                    print(f"    {GRAY}├─ {c_name}:{RESET} (path not found: {test_path})")
            print()
        
    # Phase Overview - only show when --overview flag is passed
    import shutil
    term_width = shutil.get_terminal_size().columns
    DIM = "\033[2m"
    CYAN = "\033[96m"
    GRAY = "\033[90m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    RED = "\033[91m"
    RESET = "\033[0m"
        
    # Check if overview should be collapsed
    collapse_overview = False
    if args.collapsed is not None:
        # --collapse with no args means collapse all (empty list)
        if len(args.collapsed) == 0 or 'overview' in args.collapsed or 'all' in args.collapsed:
            collapse_overview = True
        
    if args.overview:
        # Header is printed inside expanded block, not here
            
        # Load history data for metrics (just saved in this run)
        from ptsd_agent.storage.legacy_history import get_history_store
        history = get_history_store()
        runs = history.list_runs(limit=1)
        phases_data = {}
        if runs:
            target_run = history.get_run(runs[0]['run_id'])
            if target_run:
                phases_data = target_run.get('phases', {})
        
        # Load Task Master data for accurate phase status
        from ptsd_agent.integrations.legacy_taskmaster import TaskMasterLoader
        tm_loader = TaskMasterLoader()
        tm_summary = tm_loader.load()
            
        task_by_id = {}
        if tm_summary:
            for task in tm_summary.tasks:
                task_by_id[task.id] = task
        
        # Get all phases from config
        all_phases = project_config.phases
        completed_count = 0
        in_progress_count = 0
        planned_count = 0
            
        # Component totals
        total_comp_done = 0
        total_comp_wip = 0
        total_comp_pending = 0
            
        if collapse_overview:
            # COLLAPSED: Count phases AND components, then show only summary lines
            for phase in all_phases:
                p_id = phase['id']
                p_status = phase.get('status', '')
                components = phase.get('components', [])
                    
                # Count phase status
                if 'COMPLETE' in p_status.upper():
                    completed_count += 1
                elif 'PROGRESS' in p_status.upper():
                    in_progress_count += 1
                else:
                    planned_count += 1
                    
                # Count component statuses using Task Master data
                for comp in components:
                    tm_id = comp.get('taskmaster_id')
                    if tm_id and tm_id in task_by_id:
                        task = task_by_id[tm_id]
                        if task.status == 'done':
                            total_comp_done += 1
                        elif task.status in ['in-progress', 'review']:
                            total_comp_wip += 1
                        else:
                            total_comp_pending += 1
                    else:
                        # Check test-based components from history
                        has_tests = bool(comp.get('test_path'))
                        if has_tests:
                            phase_metrics = phases_data.get(str(p_id), {}).get('metrics', {})
                            if phase_metrics.get('pass_rate', 0) >= 100:
                                total_comp_done += 1
                            elif phase_metrics.get('total_tests', 0) > 0:
                                total_comp_wip += 1
                            else:
                                total_comp_pending += 1
                        else:
                            total_comp_pending += 1
                
            # Show collapsed Phase Overview with header and triangle at end
            from ptsd_agent.ui.theme import TRIANGLE_COLLAPSED
            from ptsd_agent.ui.components import right_align_text
            print()  # Space after progress bar
            phase_header = right_align_text(f"  {GRAY}Phase Overview{RESET}", f"{DIM}{TRIANGLE_COLLAPSED}{RESET}", term_width, trailing_space=0)
            print(phase_header)
            print(f"  {DIM}Phases:{RESET} {GREEN}{completed_count}{RESET} complete | {YELLOW}{in_progress_count}{RESET} active | {GRAY}{planned_count} planned{RESET}")
            print(f"  {DIM}Components:{RESET} {GREEN}✓ {total_comp_done}{RESET} done | {YELLOW}◐ {total_comp_wip}{RESET} wip | {GRAY}○ {total_comp_pending}{RESET} pending")
        else:
            # EXPANDED: Show full phase details with component breakdown (like standalone --overview)
            from ptsd_agent.ui.theme import TRIANGLE_EXPANDED, GRAY, RESET, DIM, GREEN, YELLOW, RED
            from ptsd_agent.ui.theme import get_color_for_value
            from ptsd_agent.ui.components import right_align_text
            print()  # Space after progress bar
            phase_header = right_align_text(f"  {GRAY}Phase Overview{RESET}", f"{DIM}{TRIANGLE_EXPANDED}{RESET}", term_width, trailing_space=0)
            print(phase_header)
            print()
            for phase in all_phases:
                p_id = phase['id']
                p_name = phase['name']
                p_status = phase.get('status', '')
                components = phase.get('components', [])
                    
                has_test_paths = any(c.get('test_path') for c in components)
                has_taskmaster = any(c.get('taskmaster_id') for c in components)
                    
                # Get phase-level metrics from historical run
                phase_metrics = phases_data.get(str(p_id), {}).get('metrics', {})
                phase_pass_rate = phase_metrics.get('pass_rate', 0)
                phase_coverage = phase_metrics.get('coverage', 0)
                phase_tests = phase_metrics.get('total_tests', 0)
                    
                # Get per-component metrics
                component_metrics = phases_data.get(str(p_id), {}).get('components', {})
                    
                comp_done = 0
                comp_wip = 0
                comp_pending = 0
                    
                if has_test_paths:
                    for comp in components:
                        c_name = comp.get('name', '')
                        c_metrics = component_metrics.get(c_name, {})
                        c_tests = c_metrics.get('total_tests', 0)
                        c_pass_rate = c_metrics.get('pass_rate', 0)
                        c_status = comp.get('status', '').lower()
                            
                        if 'complete' in c_status or 'done' in c_status:
                            comp_done += 1
                        elif c_tests > 0:
                            if c_pass_rate >= 100:
                                comp_done += 1
                            else:
                                comp_wip += 1
                        elif 'progress' in c_status or 'active' in c_status:
                            comp_wip += 1
                        else:
                            comp_pending += 1
                        
                    if 'COMPLETE' in p_status.upper() or (comp_done == len(components) and len(components) > 0):
                        status_color = GREEN
                        status_text = "Complete"
                        completed_count += 1
                    elif 'PROGRESS' in p_status.upper() or comp_wip > 0 or comp_done > 0:
                        status_color = YELLOW
                        status_text = "In Progress"
                        in_progress_count += 1
                    else:
                        status_color = GRAY
                        status_text = "Planned"
                        planned_count += 1
                        
                    if phase_tests > 0:
                        p_color = GREEN if phase_pass_rate >= 95 else (YELLOW if phase_pass_rate >= 80 else RED)
                        cov_color = get_color_for_value("coverage", phase_coverage)
                        metrics_str = f" | {p_color}{round(phase_pass_rate)}%{RESET} pass | {cov_color}{round(phase_coverage)}%{RESET} cov"
                    else:
                        metrics_str = ""
                            
                elif has_taskmaster and task_by_id:
                    for comp in components:
                        tm_id = comp.get('taskmaster_id')
                        if tm_id and tm_id in task_by_id:
                            task = task_by_id[tm_id]
                            if task.status == 'done':
                                comp_done += 1
                            elif task.status == 'in-progress':
                                comp_wip += 1
                            else:
                                comp_pending += 1
                        elif tm_id is None:
                            comp_pending += 1
                        
                    total_comps = comp_done + comp_wip + comp_pending
                    if comp_done == total_comps and total_comps > 0:
                        status_color = GREEN
                        status_text = "Complete"
                        completed_count += 1
                    elif comp_done > 0 or comp_wip > 0:
                        status_color = YELLOW
                        status_text = "In Progress"
                        in_progress_count += 1
                    else:
                        status_color = GRAY
                        status_text = "Planned"
                        planned_count += 1
                    metrics_str = ""
                elif len(components) == 0:
                    status_color = GRAY
                    status_text = "Not Planned"
                    planned_count += 1
                    metrics_str = ""
                else:
                    status_color = GRAY
                    status_text = "Planned"
                    planned_count += 1
                    comp_pending = len(components)
                    metrics_str = ""
                    
                total_comp_done += comp_done
                total_comp_wip += comp_wip
                total_comp_pending += comp_pending
                    
                # Build component breakdown string
                if comp_done + comp_wip + comp_pending > 0:
                    comp_parts = []
                    if comp_wip > 0:
                        comp_parts.append(f"{YELLOW}◐ {comp_wip}{RESET}")
                    if comp_done > 0:
                        comp_parts.append(f"{GREEN}✓ {comp_done}{RESET}")
                    if comp_pending > 0:
                        comp_parts.append(f"{GRAY}○ {comp_pending}{RESET}")
                    comp_str = "|".join(comp_parts)
                else:
                    comp_str = f"{GRAY}n/a{RESET}"
                    
                print(f"  {DIM}├─{RESET} Phase {p_id}: {status_color}{status_text}{RESET} [{comp_str}]{metrics_str}")
                
            print()
            print(f"  {DIM}Phases:{RESET} {GREEN}{completed_count}{RESET} complete | {YELLOW}{in_progress_count}{RESET} active | {GRAY}{planned_count} planned{RESET}")
            print(f"  {DIM}Components:{RESET} {GREEN}✓ {total_comp_done}{RESET} done | {YELLOW}◐ {total_comp_wip}{RESET} wip | {GRAY}○ {total_comp_pending}{RESET} pending")
            
        print()
        # Final closing delimiter bar
        print(f"{DIM}{CYAN}{'▰' * term_width}{RESET}")
            
        # DIAGNOSTICS SECTION: Show when --diagnostics flag is set OR config enabled
        diag_config = project_config.get_diagnostics_config()
        show_diag = args.diagnostics or diag_config["show_diagnostics"]
            
        if show_diag:
            print()
            from ptsd_agent.ui.components import DiagnosticsSection
            diagnostics = DiagnosticsSection(
                collector=collector,
                term_width=term_width,
                show_diagnostics=True
            )
            diag_lines = diagnostics.build()
            if diag_lines:
                for line in diag_lines:
                    print(line)
                print()
                print(f"{DIM}{CYAN}{'▰' * term_width}{RESET}")
                print()
            
        print(f"running \"git fetch\"... ok!")
        
    except KeyboardInterrupt:
        sys.stdout.write("\033[?25h")
        print("\nInterrupted by user.")
        sys.exit(1)
    finally:
        sys.stdout.write("\033[?25h")

if __name__ == "__main__":
    main()
