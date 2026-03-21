#!/usr/bin/env python3
"""VideoPilot Command Line Interface."""

import argparse
import sys
from pathlib import Path
from core.orchestrator import Orchestrator
from core.input_handler import analyze_inputs
from core.pipeline import Pipeline
from core.task_router import TaskRouter


def list_modules():
    """List all available modules."""
    orch = Orchestrator()
    orch.load_modules()
    print("Available VideoPilot Modules:")
    print("-" * 50)
    for module_info in orch.list_tasks():
        print(f"{module_info['name']:<30} {module_info['description']}")


def run_module(module_name: str, input_path: str, output_path: str):
    """Run a single module on a video file."""
    input_path = Path(input_path)
    output_path = Path(output_path)
    
    if not input_path.exists():
        print(f"Error: Input file '{input_path}' does not exist.")
        sys.exit(1)
    
    # Initialize orchestrator
    orch = Orchestrator()
    orch.load_modules()
    
    # Check if module exists
    module_names = [mod['name'] for mod in orch.list_tasks()]
    if module_name not in module_names:
        print(f"Error: Module '{module_name}' not found.")
        print("Available modules:")
        for mod in module_names:
            print(f"  - {mod}")
        sys.exit(1)
    
    # Run module
    try:
        result = orch.run_task(
            task=module_name,
            files=[input_path],
            output_path=output_path
        )
        
        if result.success:
            print(f"Success! Output saved to: {output_path}")
        else:
            print(f"Error: {result.error}")
            sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


def run_pipeline(input_path: str, output_path: str, modules: list):
    """Run a pipeline of multiple modules on a video file."""
    input_path = Path(input_path)
    output_path = Path(output_path)
    
    if not input_path.exists():
        print(f"Error: Input file '{input_path}' does not exist.")
        sys.exit(1)
    
    # Initialize orchestrator
    orch = Orchestrator()
    orch.load_modules()
    
    # Check all modules exist
    module_names = [mod['name'] for mod in orch.list_tasks()]
    invalid_modules = [mod for mod in modules if mod not in module_names]
    if invalid_modules:
        print("Error: Invalid modules:")
        for mod in invalid_modules:
            print(f"  - {mod}")
        print("Available modules:")
        for mod in module_names:
            print(f"  - {mod}")
        sys.exit(1)
    
    # Run pipeline
    try:
        result = orch.run_pipeline(
            tasks=modules,
            files=[input_path],
            output_path=output_path
        )
        
        if result.success:
            print(f"Success! Output saved to: {output_path}")
        else:
            print(f"Error: Pipeline failed: {result.error}")
            sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="VideoPilot - AI-Powered Video Editing Platform",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  List all available modules:
    videopilot --list-modules
    
  Run a single module:
    videopilot --run color_grading --input input.mp4 --output output.mp4
    
  Run a pipeline of multiple modules:
    videopilot --pipeline "color_grading,stabilization,auto_subtitles" --input input.mp4 --output output.mp4
    
  Run pipeline with custom options:
    videopilot --run color_grading --input input.mp4 --output output.mp4 --options '{"intensity": 0.8}'
        """
    )
    
    # List modules
    parser.add_argument(
        "--list-modules",
        "-l",
        action="store_true",
        help="List all available VideoPilot modules"
    )
    
    # Run single module
    parser.add_argument(
        "--run",
        "-r",
        metavar="MODULE",
        help="Run a specific module on a video file"
    )
    
    # Run pipeline
    parser.add_argument(
        "--pipeline",
        "-p",
        metavar="MODULES",
        help="Run a pipeline of modules (comma-separated list)"
    )
    
    # Input file
    parser.add_argument(
        "--input",
        "-i",
        metavar="FILE",
        help="Path to input video file"
    )
    
    # Output file
    parser.add_argument(
        "--output",
        "-o",
        metavar="FILE",
        help="Path to output video file"
    )
    
    # Module options
    parser.add_argument(
        "--options",
        "-O",
        metavar="JSON",
        help="Options for module(s) in JSON format"
    )
    
    # Verbose mode
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output"
    )
    
    # Version
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 0.1.0"
    )
    
    args = parser.parse_args()
    
    # Check for valid command combinations
    if args.list_modules:
        list_modules()
        return
    
    if args.run or args.pipeline:
        if not args.input:
            print("Error: --input is required when running modules or pipelines")
            parser.print_help()
            sys.exit(1)
        
        if not args.output:
            print("Error: --output is required when running modules or pipelines")
            parser.print_help()
            sys.exit(1)
    
    if args.run:
        run_module(args.run, args.input, args.output)
    elif args.pipeline:
        modules = [m.strip() for m in args.pipeline.split(",") if m.strip()]
        run_pipeline(args.input, args.output, modules)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
