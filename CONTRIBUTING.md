# Contributing to Project Ironwall

## PR Checklist

- [ ] All new functions have type annotations
- [ ] Unit tests added / updated — coverage must not decrease
- [ ] Security-sensitive changes (`extract_pov`, `TEEVerifier`, attestation) require **two** maintainer reviews
- [ ] No SHA-256 in crypto paths — SHA3-256 only
- [ ] No game state variables outside `layer1_thinclient/server.py`
- [ ] Hedera operations tested against testnet before mainnet PR
- [ ] ZK circuit changes include empirical data citation in PR description
- [ ] `CHANGELOG.md` updated

## Code Style

| Tool | Config |
|------|--------|
| Formatter | `black` (line length 100) |
| Linter | `ruff` — config in `pyproject.toml` |
| Type checks | `mypy --strict` on all `core/` and `layer*/` modules |
| Imports | `isort` — stdlib, third-party, local; no star imports |
| Naming | `snake_case` functions/vars, `PascalCase` classes, `UPPER_SNAKE` constants |
| Docstrings | Google style — required on all public functions |

## Adding Attestation Providers

Implement the `_verify_tee()` interface in `layer3_attest/broker.py`, add the
provider to `SUPPORTED_ATTESTATION_PROVIDERS` in `core/config.py`, and include
integration tests against the provider's test endpoint.

## Adding ZK Constraints

New constraints require peer review by at least one biomechanics or human-factors
researcher. Open an issue with empirical data citations before submitting a circuit PR.

## Security Disclosure

**Do not open a public GitHub issue for security vulnerabilities.**  
Email security@ironwall.gg — 24h acknowledgement, 14-day patch target.
