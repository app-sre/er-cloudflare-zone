# AGENTS.md

This file provides guidance to AI coding agents when working with code in this repository.

## Overview

External Resources module for provisioning and managing Cloudflare zones. This is part of the ERv2 (External Resources v2) ecosystem, using `external-resources-io` for input parsing and Terraform configuration generation.

## Environment Setup

Create a `.env` file in the project root from `.env.example`.

Load environment variables before running Terraform or import commands:

```bash
source .env
# or
export $(cat .env | xargs)
```

## Commands

```bash
# Setup development environment
make dev-env
source .venv/bin/activate

# Run full test suite (lint + type check + tests)
make test

# Run a single test
uv run pytest tests/test_main.py::test_function_name -vv

# Format code
make format

# Type checking only
uv run mypy

# Generate variables.tf from Pydantic model
make generate-variables-tf

# Lock terraform providers for multiple platforms
make providers-lock

# Dry run import (log commands without executing)
DRY_RUN=True import-tfstate

# Import existing Cloudflare resources into Terraform state
DRY_RUN=False import-tfstate
```

## Architecture

The module follows the ERv2 pattern:
1. **Pydantic input models** (`er_cloudflare_zone/app_interface_input.py`) define the expected input schema from App Interface
2. **Entry point** (`er_cloudflare_zone/__main__.py`) parses input and generates Terraform backend config + tfvars
3. **State import** (`er_cloudflare_zone/import_tfstate.py`) imports existing Cloudflare resources into Terraform state
4. **Terraform module** (`module/`) provisions Cloudflare zone, DNS records, subscriptions, and rulesets

Input models in `app_interface_input.py` mirror the Terraform variables in `module/variables.tf`. When modifying input models, regenerate variables.tf with `make generate-variables-tf`.

## Key Dependencies

- `external-resources-io`: Provides input parsing, Terraform helpers, and CLI utilities
- `cloudflare`: Python SDK for Cloudflare API (used for state import)
- `pydantic`: Data validation and schema definition
