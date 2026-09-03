"""CLI for security red-teaming using PyRIT framework."""

import asyncio
import sys
import json
from pathlib import Path
from typing import Optional
from datetime import datetime, timezone

import click
import structlog

from redteam.config import settings
from redteam.pyrit_runner import PyRITRunner
from redteam.orchestrator import RedTeamOrchestrator

logger = structlog.get_logger(__name__)

# Windows consoles default to cp1252, which cannot encode the emoji used in
# status output; force UTF-8 so the CLI runs cross-platform.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass


@click.group()
def main():
    """Security Red-Team Testing CLI."""
    pass


@main.command()
@click.option(
    "--threat-models",
    "-t",
    default=None,
    help="Comma-separated list of threat models (jailbreak,prompt_injection,data_exfiltration)",
)
@click.option(
    "--max-iterations",
    "-i",
    type=int,
    default=None,
    help="Max attack iterations per threat model",
)
@click.option(
    "--attack-type",
    "-a",
    type=click.Choice(["PromptSending", "Crescendo", "MultiTurn", "RedTeaming", "PromptSeed"]),
    default="PromptSending",
    help="Type of PyRIT attack to execute",
)
@click.option(
    "--output",
    "-o",
    type=Path,
    default=None,
    help="Output file for report (auto-generated if not provided)",
)
@click.option(
    "--use-file/--no-file",
    default=False,
    help="Load test cases from data/red_team_test_cases.json instead of backend",
)
@click.option(
    "--cases",
    "-c",
    default=None,
    help="Comma-separated test case names to run (use --list-cases to see available)",
)
def scan(
    threat_models: Optional[str],
    max_iterations: Optional[int],
    attack_type: str,
    output: Optional[Path],
    use_file: bool,
    cases: Optional[str],
):
    """
    Run security scan using PyRIT framework.
    
    PyRIT (Python Red Teaming) provides sophisticated attack capabilities:
    - PromptSending: Basic prompt transformations with converters
    - Crescendo: Escalating multi-turn jailbreak attacks
    - MultiTurn: Adaptive multi-turn conversations
    - RedTeaming: Intelligent red-teaming attacks
    
    Examples:
        # Run PromptSending attack with test cases
        red-team scan --use-file -a PromptSending
        
        # Run Crescendo jailbreak attack
        red-team scan --use-file -a Crescendo
        
        # Run multi-turn attack
        red-team scan --use-file -a MultiTurn -i 10
        
        # Run specific test cases
        red-team scan --use-file --cases jailbreak_role_playing -a Crescendo
    """
    try:
        # Parse threat models
        if threat_models:
            models = [m.strip() for m in threat_models.split(",") if m.strip()]
        else:
            models = None
        
        # Create PyRIT runner
        max_iter = max_iterations or settings.red_team_max_iterations
        runner = PyRITRunner(
            threat_models=models,
            max_iterations=max_iter,
            verbose=True
        )
        
        click.echo("Starting PyRIT security red-team scan...")
        click.echo(f"Attack Type: {attack_type}")
        click.echo(f"Max Iterations: {max_iter}")
        if models:
            click.echo(f"Threat Models: {', '.join(models)}")
        
        # Load test cases
        if use_file:
            all_test_cases = RedTeamOrchestrator.load_test_cases()
            
            # Filter by case names if specified
            if cases:
                case_names = {c.strip() for c in cases.split(",") if c.strip()}
                test_cases = [tc for tc in all_test_cases if tc.get("name") in case_names]
                click.echo(f"Running {len(test_cases)} selected test cases")
            else:
                test_cases = all_test_cases
                click.echo(f"Running {len(test_cases)} test cases from file")
        else:
            click.echo("Running attack against backend (set --use-file to use test cases)")
            test_cases = [{"query": "What is the application fee for a water licence?"}]
        
        if not test_cases:
            click.echo("❌ No test cases found", err=True)
            sys.exit(1)
        
        # Run attacks
        results = asyncio.run(
            runner.scan_test_cases(test_cases, attack_type=attack_type)
        )
        
        # Print summary
        successful = sum(1 for r in results if "error" not in r)
        click.echo(f"\n✅ Completed {successful}/{len(results)} attacks successfully")
        
        # Save report
        report_path = _save_pyrit_report(runner, output)
        click.echo(f"Report saved: {report_path}")
        
        # Save detailed results with escalation steps
        if results:
            stem = Path(report_path).stem.replace("pyrit_report", "crescendo_details")
            detailed_filename = stem + ".json"
            detailed_path = Path(report_path).parent / detailed_filename
            try:
                runner.save_detailed_results(results, str(detailed_path))
                click.echo(f"Detailed results saved: {detailed_path}")
            except Exception as e:
                click.echo(f"Warning: Could not save detailed results: {e}")
        
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@main.command()
@click.option(
    "--query",
    "-q",
    required=True,
    help="Query to test",
)
@click.option(
    "--attack-type",
    "-a",
    type=click.Choice(["PromptSending", "Crescendo", "MultiTurn", "RedTeaming", "PromptSeed"]),
    default="PromptSending",
    help="Type of PyRIT attack",
)
def test_query(query: str, attack_type: str):
    """
    Test a single query with PyRIT attack.
    
    Example:
        red-team test-query -q "What is water application fee?" -a Crescendo
    """
    try:
        runner = PyRITRunner(verbose=True)
        
        click.echo(f"Testing query: {query}")
        click.echo(f"Attack type: {attack_type}\n")
        
        # Run attack
        if attack_type == "Crescendo":
            result = asyncio.run(runner.run_jailbreak_attack(query))
        elif attack_type == "MultiTurn":
            result = asyncio.run(runner.run_multi_turn_attack(query))
        elif attack_type == "RedTeaming":
            result = asyncio.run(runner.run_red_team_attack(query))
        elif attack_type == "PromptSeed":
            # For PromptSeed, use seed datasets instead of query
            result = asyncio.run(runner.run_attack_seed())
        else:
            result = asyncio.run(runner.run_attack(query))
        
        if "error" in result:
            click.echo(f"❌ Error: {result['error']}", err=True)
            sys.exit(1)
        
        # Display results
        click.echo(f"✅ Attack completed")
        click.echo(f"Attack type: {result.get('attack_type')}")
        click.echo(f"Turns executed: {len(result.get('results', {}).get('turns', []))}")
        
        if result.get("results", {}).get("turns"):
            click.echo("\nAttack turns:")
            for turn in result["results"]["turns"][:3]:  # Show first 3 turns
                click.echo(f"\n  Turn {turn['turn']}:")
                click.echo(f"    Prompt: {turn['prompt'][:100]}...")
                click.echo(f"    Response: {turn['response'][:100]}...")
        
        return 0
        
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@main.command()
@click.option(
    "--filter",
    "-f",
    default=None,
    help="Filter by threat model (jailbreak, prompt_injection, data_exfiltration)",
)
def list_cases(filter: Optional[str]):
    """
    List available test cases from data/red_team_test_cases.json.
    
    Examples:
        # List all test cases
        red-team list-cases
        
        # List only jailbreak test cases
        red-team list-cases -f jailbreak
    """
    try:
        test_cases = RedTeamOrchestrator.load_test_cases()
        
        if not test_cases:
            click.echo("❌ No test cases found")
            sys.exit(1)
        
        # Filter if specified
        if filter:
            test_cases = [
                tc for tc in test_cases 
                if filter in tc.get("threat_models", [])
            ]
        
        click.echo("\n" + "="*80)
        click.echo(f"AVAILABLE TEST CASES ({len(test_cases)})")
        click.echo("="*80)
        
        for i, case in enumerate(test_cases, 1):
            name = case.get("name", "unnamed")
            description = case.get("description", "")
            threat_models = case.get("threat_models", [])
            query = case.get("query", "")
            
            click.echo(f"\n{i}. [{name}]")
            click.echo(f"   Description: {description}")
            click.echo(f"   Threat Models: {', '.join(threat_models)}")
            click.echo(f"   Query: {query[:100]}{'...' if len(query) > 100 else ''}")
        
        click.echo("\n" + "="*80)
        click.echo(f"\nTo run with PyRIT (recommended):")
        click.echo(f"  red-team scan --use-file -a PromptSending")
        click.echo(f"  red-team scan --use-file --cases case_name1 -a Crescendo")
        click.echo("="*80)
        
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@main.command(name="seed-attack")
@click.option(
    "--datasets",
    "-d",
    default=None,
    help="Comma-separated list of seed datasets (illegal,violence,hate,sexual,harassment,scams,malware,fairness,leakage,misinformation,harms,psychosocial)",
)
@click.option(
    "--limit-seeds",
    "-l",
    type=int,
    default=None,
    help="Maximum number of seeds to use (None = all available)",
)
@click.option(
    "--output",
    "-o",
    type=Path,
    default=None,
    help="Output file for report (auto-generated if not provided)",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Enable verbose output",
)
def seed_attack(
    datasets: Optional[str],
    limit_seeds: Optional[int],
    output: Optional[Path],
    verbose: bool,
):
    """
    Run security attack using AIRT seed datasets.
    
    Attacks using pre-curated seed prompts from 12 threat categories:
    - illegal: Illegal activities (theft, explosives, etc.)
    - violence: Physical violence scenarios
    - hate: Hate speech and discrimination
    - sexual: Sexual content and exploitation
    - harassment: Bullying and harassment
    - scams: Fraud and deception
    - malware: Software exploitation
    - fairness: Bias and discrimination
    - leakage: Data disclosure
    - misinformation: False information
    - harms: General harmful content
    - psychosocial: Psychological harm
    
    Examples:
        # Default attack (4 core datasets, 20 seeds)
        red-team seed-attack
        
        # Custom datasets
        red-team seed-attack -d "violence,harassment,scams"
        
        # Quick test with limited seeds
        red-team seed-attack -l 3
        
        # Full coverage with all datasets
        red-team seed-attack -d "illegal,violence,hate,sexual,harassment,scams,malware,fairness,leakage,misinformation,harms,psychosocial"
        
        # All datasets (55 total seeds)
        red-team seed-attack -d "all"
    """
    try:
        runner = PyRITRunner(verbose=verbose)
        
        # Parse datasets
        seed_datasets = None
        if datasets:
            if datasets.lower() == "all":
                seed_datasets = list(runner.available_seed_datasets.keys())
            else:
                seed_datasets = [d.strip() for d in datasets.split(",") if d.strip()]
        
        # Display configuration
        if verbose:
            click.echo("🚀 Starting seed dataset attack...")
            if seed_datasets:
                click.echo(f"📊 Datasets: {', '.join(seed_datasets)}")
            else:
                click.echo(f"📊 Datasets: Default (illegal, violence, hate, sexual)")
            if limit_seeds:
                click.echo(f"📉 Seed limit: {limit_seeds}")
            click.echo()
        
        # Run attack
        if verbose:
            click.echo("⏳ Loading seed datasets...")
        
        result = asyncio.run(runner.run_attack_seed(
            seed_datasets=seed_datasets,
            limit_seeds=limit_seeds
        ))
        
        # Check for errors
        if "error" in result:
            click.echo(f"❌ Attack failed: {result['error']}", err=True)
            sys.exit(1)
        
        # Display results
        click.echo(f"✅ Attack completed successfully!")
        click.echo(f"\n📋 Attack Summary:")
        click.echo(f"  Attack Type: {result.get('attack_type')}")
        click.echo(f"  Seed Source: {result.get('seed_source')}")
        click.echo(f"  Datasets Used: {', '.join(result.get('seed_datasets', []))}")
        click.echo(f"  Total Seeds: {result.get('total_seeds_used')}")
        click.echo(f"  Converters: {', '.join(result.get('converters', []))}")
        
        results = result.get("results", {})
        total_turns = results.get("total_turns", 0)
        turns = results.get("turns", [])
        
        click.echo(f"  Total Turns: {total_turns}")
        click.echo(f"  Timestamp: {result.get('timestamp')}")
        
        # Show sample results
        if turns:
            click.echo(f"\n📝 Sample Results (first 3 turns):")
            for i, turn in enumerate(turns[:3], 1):
                prompt = turn.get("prompt", "N/A")
                response = turn.get("response", "N/A")
                prompt_preview = prompt[:70] + "..." if len(prompt) > 70 else prompt
                response_preview = response[:70] + "..." if len(response) > 70 else response
                
                click.echo(f"\n  Turn {i}:")
                click.echo(f"    Prompt: {prompt_preview}")
                click.echo(f"    Response: {response_preview}")
        
        # Save report if requested
        if output:
            with open(output, "w") as f:
                json.dump(result, f, indent=2, default=str)
            click.echo(f"\n💾 Report saved: {output}")
        else:
            # Auto-generate report path
            results_dir = Path("results")
            results_dir.mkdir(exist_ok=True)
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            report_path = results_dir / f"seed_attack_{timestamp}.json"
            with open(report_path, "w") as f:
                json.dump(result, f, indent=2, default=str)
            click.echo(f"\n💾 Report saved: {report_path}")
        
        return 0
        
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


def _save_pyrit_report(runner: PyRITRunner, output_path: Optional[Path] = None) -> Path:
    """Save PyRIT attack results to JSON report."""
    if output_path is None:
        results_dir = Path("results")
        results_dir.mkdir(exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        output_path = results_dir / f"pyrit_report_{timestamp}.json"
    
    # Create report
    report = {
        "report_type": "PyRIT",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **runner.results,
    }
    
    with open(output_path, "w") as f:
        json.dump(report, f, indent=2, default=str)
    
    return output_path


if __name__ == "__main__":
    main()
