#!/usr/bin/env python3
"""
Generate all configuration files from variables.yaml

This script reads config/variables.yaml and generates:
- GitHub Actions workflow environment blocks
- Terragrunt locals and tfvars
- Terraform variable declarations
- Agent service .env templates

Usage:
    python scripts/generate-configs.py [--validate] [--target github-actions|terragrunt|terraform|agent-env]
"""

import sys
import yaml
import json
from pathlib import Path
from typing import Dict, List, Any


class ConfigGenerator:
    def __init__(self, variables_file: Path):
        """Initialize generator with variables.yaml"""
        with open(variables_file, 'r') as f:
            self.config = yaml.safe_load(f)
        self.variables = {v['name']: v for v in self.config.get('variables', [])}

    def validate(self) -> List[str]:
        """Validate variables configuration"""
        errors = []
        required_keys = {'name', 'category', 'type', 'description', 'targets', 'terraform_type'}
        
        for i, var in enumerate(self.config.get('variables', [])):
            if not isinstance(var, dict):
                errors.append(f"Variable {i} is not a dict")
                continue
            
            missing = required_keys - set(var.keys())
            if missing:
                errors.append(f"Variable '{var.get('name', f'index-{i}')}' missing keys: {missing}")
            
            if 'github-actions' in var.get('targets', []) and var.get('type') == 'secret' and '{{ secrets.' not in str(var.get('github_template', '')):
                # This is fine, we'll auto-generate the template
                pass
        
        return errors

    def generate_github_actions_env_block(self) -> str:
        """Generate GitHub Actions env block with all variables"""
        lines = []
        current_category = None
        
        # Sort by category for readability
        sorted_vars = sorted(
            [v for v in self.config['variables'] if 'github-actions' in v.get('targets', [])],
            key=lambda x: x['category']
        )
        
        for var in sorted_vars:
            if var['category'] != current_category:
                current_category = var['category']
                lines.append(f"          # {current_category} Configuration")
            
            var_name = var['name']
            var_type = var.get('type', 'variable')
            
            if var_type == 'secret':
                template = f"${{{{ secrets.{var_name} }}}}"
            else:
                # Check if we should use || for defaults
                default = var.get('github_default', '')
                if default:
                    template = f"${{{{ vars.{var_name} || '{default}' }}}}"
                else:
                    template = f"${{{{ vars.{var_name} }}}}"
            
            lines.append(f"          {var_name}: {template}")
        
        return "\n".join(lines)

    def generate_terragrunt_locals(self) -> str:
        """Generate Terragrunt local variables"""
        lines = ['  # Environment variable locals']
        current_category = None
        
        sorted_vars = sorted(
            [v for v in self.config['variables'] if 'terragrunt' in v.get('targets', [])],
            key=lambda x: x['category']
        )
        
        for var in sorted_vars:
            if var['category'] != current_category:
                current_category = var['category']
                lines.append(f"\n  # {current_category}")
            
            var_name = var['name']
            snake_case_name = var['name'].lower()
            default = var.get('terraform_default', '""')
            
            lines.append(f"  {snake_case_name} = get_env(\"{var_name}\", {default})")
        
        return "\n".join(lines)

    def generate_terragrunt_tfvars(self) -> str:
        """Generate Terragrunt tfvars pass-through"""
        lines = ['# Pass environment variables to Terraform']
        current_category = None
        
        sorted_vars = sorted(
            [v for v in self.config['variables'] if 'terragrunt' in v.get('targets', [])],
            key=lambda x: x['category']
        )
        
        for var in sorted_vars:
            if var['category'] != current_category:
                current_category = var['category']
                lines.append(f"\n# {current_category}")
            
            var_name = var['name']
            snake_case_name = var['name'].lower()
            lines.append(f"{snake_case_name} = \"${{local.{snake_case_name}}}\"")
        
        return "\n".join(lines)

    def generate_terraform_variables(self) -> str:
        """Generate Terraform variable declarations"""
        lines = []
        current_category = None
        
        sorted_vars = sorted(
            [v for v in self.config['variables'] if 'terraform-root' in v.get('targets', [])],
            key=lambda x: x['category']
        )
        
        for var in sorted_vars:
            if var['category'] != current_category:
                current_category = var['category']
                lines.append(f"\n# {current_category}")
            
            var_name = var['name']
            snake_case_name = var['name'].lower()
            description = var.get('description', '')
            tf_type = var.get('terraform_type', 'string')
            tf_default = var.get('terraform_default', '""')
            is_sensitive = var.get('terraform_sensitive', False)
            
            lines.append(f"\nvariable \"{snake_case_name}\" {{")
            lines.append(f"  description = \"{description}\"")
            lines.append(f"  type        = {tf_type}")
            lines.append(f"  default     = {tf_default}")
            if is_sensitive:
                lines.append(f"  sensitive   = true")
            lines.append("}")
        
        return "\n".join(lines)

    def generate_terraform_module_variables(self) -> str:
        """Generate module-level Terraform variable declarations"""
        lines = []
        current_category = None
        
        sorted_vars = sorted(
            [v for v in self.config['variables'] if 'terraform-module' in v.get('targets', [])],
            key=lambda x: x['category']
        )
        
        for var in sorted_vars:
            if var['category'] != current_category:
                current_category = var['category']
                lines.append(f"\n# {current_category}")
            
            var_name = var['name']
            snake_case_name = var['name'].lower()
            description = var.get('description', '')
            tf_type = var.get('terraform_type', 'string')
            tf_default = var.get('terraform_default', '""')
            is_sensitive = var.get('terraform_sensitive', False)
            
            lines.append(f"\nvariable \"{snake_case_name}\" {{")
            lines.append(f"  description = \"{description}\"")
            lines.append(f"  type        = {tf_type}")
            lines.append(f"  default     = {tf_default}")
            lines.append(f"  nullable    = false")
            if is_sensitive:
                lines.append(f"  sensitive   = true")
            lines.append("}")
        
        return "\n".join(lines)

    def generate_agent_env_template(self, agent_name: str = None) -> str:
        """Generate .env template for agent services"""
        lines = ['# Agent service environment configuration', '# Copy this file to .env and populate with actual values']
        current_category = None
        
        # Filter by agent if specified
        if agent_name:
            agent_vars = [
                v for v in self.config['variables'] 
                if 'agent-env' in v.get('targets', []) 
                and (not v.get('agent_targets') or agent_name in v.get('agent_targets', []))
            ]
        else:
            agent_vars = [v for v in self.config['variables'] if 'agent-env' in v.get('targets', [])]
        
        sorted_vars = sorted(agent_vars, key=lambda x: x['category'])
        
        for var in sorted_vars:
            if var['category'] != current_category:
                current_category = var['category']
                lines.append(f"\n# {current_category}")
            
            var_name = var['name']
            agent_default = var.get('agent_default', '<placeholder>')
            description = var.get('description', '')
            
            lines.append(f"# {description}")
            lines.append(f"{var_name}={agent_default}")
        
        return "\n".join(lines)

    def generate_terraform_main_passthrough(self) -> str:
        """Generate variable passthrough in infra/main.tf"""
        lines = ['# Pass variables to container-apps module']
        current_category = None
        
        sorted_vars = sorted(
            [v for v in self.config['variables'] if 'terraform-root' in v.get('targets', [])],
            key=lambda x: x['category']
        )
        
        for var in sorted_vars:
            if var['category'] != current_category:
                current_category = var['category']
                lines.append(f"\n  # {current_category}")
            
            snake_case_name = var['name'].lower()
            lines.append(f"  {snake_case_name} = var.{snake_case_name}")
        
        return "\n".join(lines)


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Generate configuration files from variables.yaml'
    )
    parser.add_argument(
        '--validate',
        action='store_true',
        help='Validate variables.yaml and exit'
    )
    parser.add_argument(
        '--target',
        choices=['github-actions', 'terragrunt', 'terraform', 'agent-env', 'all'],
        default='all',
        help='Generate only specified target'
    )
    parser.add_argument(
        '--agent',
        help='Specific agent for --target=agent-env (e.g., orchestrator, conversation, formsupport)'
    )
    
    args = parser.parse_args()
    
    # Find config directory
    config_path = Path(__file__).parent.parent / 'config' / 'variables.yaml'
    if not config_path.exists():
        print(f"Error: {config_path} not found", file=sys.stderr)
        sys.exit(1)
    
    generator = ConfigGenerator(config_path)
    
    # Validate
    errors = generator.validate()
    if errors:
        print("Validation errors:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        sys.exit(1)
    
    if args.validate:
        print("✓ Configuration is valid")
        return
    
    # Generate targets
    targets = ['github-actions', 'terragrunt', 'terraform', 'agent-env'] if args.target == 'all' else [args.target]
    
    if 'github-actions' in targets:
        print("# GitHub Actions Environment Block")
        print("# Add this to .github/workflows/.deployer_aca.yml env: sections")
        print(generator.generate_github_actions_env_block())
        print()
    
    if 'terragrunt' in targets:
        print("# Terragrunt locals (add to terragrunt.hcl)")
        print(generator.generate_terragrunt_locals())
        print()
        print("# Terragrunt tfvars (add to generate block in terragrunt.hcl)")
        print(generator.generate_terragrunt_tfvars())
        print()
    
    if 'terraform' in targets:
        print("# Root Terraform variables (infra/variables.tf)")
        print(generator.generate_terraform_variables())
        print()
        print("# Module Terraform variables (infra/modules/container-apps/variables.tf)")
        print(generator.generate_terraform_module_variables())
        print()
        print("# Terraform main.tf passthrough")
        print(generator.generate_terraform_main_passthrough())
        print()
    
    if 'agent-env' in targets:
        agent_name = args.agent or ""
        print(f"# Agent .env template{f' for {args.agent}' if args.agent else ''}")
        print(generator.generate_agent_env_template(agent_name))


if __name__ == '__main__':
    main()
