.PHONY: install test test-unit test-integration test-zk verify-demo lint fmt typecheck circuits clean

PYTHON ?= python3

install:
	$(PYTHON) -m venv .venv && source .venv/bin/activate && pip install -e '.[dev]'
	npm install

circuits:
	@echo "→ Compiling ZK circuits (first run ~2 min)..."
	mkdir -p zk
	circom ironwall/zk_anticheat/circuits/human_constraints.circom --r1cs --wasm --sym -o zk/
	snarkjs plonk setup zk/human_constraints.r1cs $(ZK_TRUSTED_SETUP) zk/human_constraints.zkey
	snarkjs zkey export verificationkey zk/human_constraints.zkey zk/verification_key.json
	@echo "✓ Circuits compiled"

test: test-unit test-integration

test-unit:
	pytest tests/unit/ -v

test-integration:
	docker-compose up -d
	pytest tests/integration/ -v
	docker-compose down

test-zk:
	pytest tests/unit/test_zk_prover.py -v --timeout=300

verify-demo:
	$(PYTHON) -m ironwall.cli.verify examples/match-record-valid.json
	! $(PYTHON) -m ironwall.cli.verify examples/match-record-tampered.json

lint:
	ruff check ironwall/ tests/

fmt:
	black ironwall/ tests/
	isort ironwall/ tests/

typecheck:
	mypy ironwall/

cov:
	pytest tests/ --cov=ironwall --cov-report=html
	@echo "→ Coverage report: htmlcov/index.html"

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	rm -rf .coverage htmlcov/ dist/ build/ *.egg-info
