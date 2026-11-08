# Contributing to GridPulse

Thank you for your interest in contributing to **GridPulse**! This repository serves as a research-grade data engineering pipeline and reliability evaluation suite.

## Code of Conduct & Research Integrity

1. **Empirical Grounding:** Never invent findings, mock metrics, or hallucinate schemas. All reported metrics must be deterministically reproducible from pipeline execution logs.
2. **Data Leakage Prohibition:** Any predictive model contributions must adhere strictly to chronological validation splits (Train <= 2020, Validation = 2021, Test = 2022) and must not include post-onset episode summary variables (`Max_outage`, `evDur_Hr`, etc.).
3. **Data Protection:** Original raw datasets (`*.csv`, `*.parquet`) must **never** be committed to Git.

## Development Workflow

1. Fork the repository and create your feature branch:
   ```bash
   git checkout -b feature/your-feature-name
   ```
2. Set up a virtual environment and install dependencies:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. Run existing tests before making changes:
   ```bash
   pytest tests/ -v
   ```
4. Commit your changes following conventional commit syntax (`feat:`, `fix:`, `docs:`, `test:`, `refactor:`):
   ```bash
   git commit -m "feat: add new weather warning aggregation metric"
   ```
5. Ensure all tests pass before opening a Pull Request:
   ```bash
   pytest tests/ -v
   ```
