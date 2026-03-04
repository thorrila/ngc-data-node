<div align="center">

# NGC Data Node

[![Rust](https://img.shields.io/badge/rust-stable-%23E34F26.svg?style=flat-square&logo=rust)](https://www.rust-lang.org/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg?style=flat-square&logo=python)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com)
[![DuckDB](https://img.shields.io/badge/DuckDB-FFF000?style=flat-square&logo=duckdb)](https://duckdb.org/)
[![Apache Parquet](https://img.shields.io/badge/Apache%20Parquet-50ABF1?style=flat-square&logo=apacheparquet&logoColor=white)](https://parquet.apache.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=flat-square&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-2496ED?style=flat-square&logo=docker&logoColor=white)](https://www.docker.com/)
[![Ansible](https://img.shields.io/badge/Ansible-EE0000?style=flat-square&logo=ansible&logoColor=white)](https://www.ansible.com/)
[![Nix](https://img.shields.io/badge/Nix-Reproducible-5277C3.svg?style=flat-square&logo=Nixos)](https://nixos.org/)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?style=flat-square&logo=pre-commit)](https://pre-commit.com/)
[![GitHub Actions](https://img.shields.io/badge/GitHub%20Actions-CI-2088FF?style=flat-square&logo=githubactions&logoColor=white)](https://github.com/features/actions)

<img src="assets/screenshot4.jpg" alt="DNA double helix" width="300"/>

High-throughput genomic data infrastructure. Rust → Parquet ingestion, DuckDB analytics, FastAPI secure enclave. Built to handle real-world genomics scale with sub-5ms queries and 28× network compression.

</div>

---

## Features

- **Zero-Copy Ingestion:** Rust streams `.VCF` files in 10k-row batches directly to Apache Parquet — 100,000 variants processed in **~20ms**, with peak RAM bounded to a single batch regardless of file size.
- **Sub-5ms Queries:** DuckDB scans Parquet with a thread-safe, TTL-cached async API. **~2ms p50**, **0% failure rate** under 300 RPS with 100 concurrent users.
- **28× Network Compression:** GZip middleware compresses every response automatically — `/variants` drops from 95KB → 3.3KB on the wire. Zero changes needed to any endpoint.
- **Secure Enclave:** API access gatekept with rotating API keys and an immutable PostgreSQL audit log. Every query is recorded.
- **Safe by Design:** Sample IDs anonymised with BLAKE3 cryptographic hashing. All query parameters passed through DuckDB's parameterised query interface — SQL injection is structurally impossible.
- **Reproducible Builds:** Fully hermetic Nix Flake environment. One command (`nix develop`) gives every developer the exact same Python, Rust, and toolchain versions.
- **Developer CLI:** The `ngc` utility wraps the entire lifecycle — `ngc demo` spins up the database, generates synthetic VCF data, processes it, and starts the API in one shot.

---

## Developer Environment - Nix

The easiest and most reliable way to work on this project is by using the provided **Nix**, which sets up a fully reproducible development environment and a custom helper CLI.

### 1. Enter the Environment
```bash
nix develop
```

### 2. The `ngc` Developer CLI
Inside the Nix shell, the `ngc` command provides the following hooks:

| Command | Description |
| :--- | :--- |
| `ngc demo` | Runs setup, starts DB, generates data, processes VCF to Parquet, and starts the API. |
| `ngc setup` | Syncs Python dependencies via `uv`. |
| `ngc db-up` / `db-down` | Lifecycle management for the PostgreSQL Docker container. |
| `ngc generate` | Creates a synthetic 100k variant VCF testing file. |
| `ngc run` | Compiles and runs the Rust Processor against the VCF data. |
| `ngc serve` | Starts the FastAPI server and opens the SWAGGER documentation. |
| `ngc deploy` | Deploys the application |
| `ngc bench` | Runs Rust benchmarks to measure performance. |
| `ngc profile` | Generates a CPU flamegraph to identify performance bottlenecks. |
| `ngc test` | Runs the full test suite (Rust unit tests + Python PyTest). |
| `ngc locust` | Triggers the Locust Load Testing tool for performance analysis. |
| `ngc polish` | Formats, lints and tests in one go |
| `ngc query <sql>` | Runs a SQL query against the Parquet data. |
| `ngc logs` | Shows the audit logs of the application. |
| `ngc clean` | Removes all artifacts and resets the database. |
| `ngc help` | Shows all available developer commands. |

---

## Native Workflows

If you are not using Nix, ensure you have the `cargo` toolchain, `uv` for Python 3.11+, and `docker-compose` installed.

### 1. Setup & Ingest Data
```bash
# Start Metadatabase
docker-compose up -d

# Set your API key (or use the default 'ngc' for local development only)
export NGC_API_KEY=your-secret-key

# Generate Synthetic Data
python scripts/generate_vcf.py

# Parse and Optimize to Parquet (streaming — constant memory usage)
cd processor && cargo run --release -- --input ../data/synthetic_100k.vcf --output ../data/output.parquet
```

### 2. Run the Secure API
```bash
cd enclave
uv sync
uv run uvicorn ngc_enclave.main:app --reload
```

---

## Architecture

The system is split into two independent engines connected by Apache Parquet:

```
 Raw VCF File
      │
      ▼
┌─────────────────────────────────┐
│   Rust Processor                │  Zero-copy streaming ingestion
│   noodles-vcf → ArrowWriter     │  BLAKE3 anonymisation per sample
│   Batched Parquet output        │  100k variants in ~20ms
└────────────────┬────────────────┘
                 │  data/output.parquet
                 ▼
┌─────────────────────────────────┐
│   FastAPI Secure Enclave        │  API key auth + audit log
│   DuckDB (thread-safe pool)     │  TTL cache — ~2ms p50
│   PostgreSQL audit log          │  GZip — 28× payload reduction
└─────────────────────────────────┘
```

The Rust processor and Python API share no runtime state — they communicate only through Parquet on disk. This means the ingest pipeline can run as a batch job (or Kubernetes Job) completely independently of the live query API.

---

## Project Structure

```
ngc-data-node/
│
├── processor/                  # Rust — VCF ingestion engine
│   ├── src/
│   │   ├── main.rs             # CLI entry point (--input / --output)
│   │   ├── lib.rs              # Core streaming pipeline + Parquet writer
│   │   └── anonymize.rs        # BLAKE3 sample ID hashing
│   └── benches/
│       └── benchmark.rs        # Criterion micro + macro benchmarks
│
├── enclave/                    # Python — secure query API
│   └── src/ngc_enclave/
│       ├── main.py             # FastAPI app, auth, GZip middleware
│       ├── query.py            # DuckDB queries with TTL cache
│       ├── db.py               # SQLAlchemy + PostgreSQL session
│       └── audit.py            # Immutable audit log writer
│   └── tests/
│       ├── test_api.py         # API endpoint integration tests
│       └── test_query.py       # Query layer unit tests (16 tests)
│
├── infra/
│   ├── ansible/playbook.yml    # Server provisioning
│   └── postgres/init.sql       # Audit log schema
│
├── data/                       # Runtime data (gitignored)
│   ├── synthetic_100k.vcf      # Generated by `ngc generate`
│   └── output.parquet          # Written by `ngc run`
│
├── assets/                     # README screenshots + diagrams
├── docker-compose.yml          # PostgreSQL container
├── flake.nix                   # Nix dev environment + `ngc` CLI
└── .github/workflows/ci.yml    # GitHub Actions CI (Rust + Python)
```

---

## API Endpoints

All endpoints (except `/health`) require an `Authorization: Bearer <key>` header. The default key is set by the `NGC_API_KEY` environment variable.

| Method | Endpoint | Description |
| :----- | :------- | :---------- |
| `GET` | `/health` | Liveness check. Returns `{"status": "ok"}`. No auth required. |
| `GET` | `/variants` | Query genomic variants from Parquet. Params: `chr`, `pos_min`, `pos_max`, `limit` (default `1000`, max `5000`). |
| `GET` | `/alleles` | Compute allele frequencies grouped by variant signature. Params: `chr`, `pos_min`, `pos_max`. Returns top 100 results. |
| `GET` | `/datasets` | List datasets registered in Postgres. Populated when an ingest pipeline writes metadata after processing. |

**Example Requests:**
```bash
# All variants on chromosome 1 between positions 100 and 500
curl -H "Authorization: Bearer ngc" \
  "http://localhost:8000/variants?chr=1&pos_min=100&pos_max=500&limit=50"

# Allele frequencies for chromosome X
curl -H "Authorization: Bearer ngc" \
  "http://localhost:8000/alleles?chr=X"
```

Interactive API documentation (Swagger UI) is auto-generated at `http://localhost:8000/docs` when the server is running.

---

## Performance & Scalability

**Rust Ingestion Pipeline — measured with Criterion:**

| Benchmark | Result |
| :--- | :--- |
| BLAKE3 cryptographic hash (per sample ID) | `~130 ns` |
| VCF string parsing (raw parse, no I/O) | `~12.8 ms` |
| **Full pipeline: 100k variants → Parquet** | **`~20.2 ms`** |

**FastAPI Enclave — Locust load test, 100 concurrent users:**

| Metric | Result |
| :--- | :--- |
| Throughput | `322 RPS` sustained |
| p50 response time | `~6ms` |
| p95 response time | `~27ms` (incl. cold-cache warm-up spike; steady-state `<10ms`) |
| Failure rate | **0%** |
| `/variants` payload (GZip, 1,000 rows) | `~3.3KB` wire (down from `95KB`) |
| `/alleles` payload (GZip, 100 rows) | `~2KB` wire (down from `8.7KB`) |

**Concurrency model:** DuckDB calls are offloaded to a thread pool via `asyncio.to_thread`. The TTL cache is protected by a `threading.Lock` to prevent thundering-herd cache stampedes under high concurrency.

**Current scale boundary:** Benchmarks are against a 100k variant synthetic dataset. Performance at multi-million variant scale will depend on Parquet file size, available RAM, and whether partition pruning is enabled. The architecture is designed to scale horizontally — the stateless API can be replicated behind a load balancer.

> All figures measured locally over loopback (`127.0.0.1`) against a **GRCh38-based 100k variant synthetic dataset** (all 25 chromosomes, realistic positions). Real-world figures will vary with network latency and dataset size.

*(Replicate with `ngc bench` for Rust benchmarks or `ngc locust` for API load testing.)*

---

## Measurements

Here are the latest runtime measurements from a local test environment:

### Python Enclave (Locust API Load Test)
![Locust Load Test Charts](assets/screenshot1.jpg)

![Locust Load Test Statistics](assets/screenshot2.jpg)

### Rust Processor (Criterion Benchmarks)
![Rust Criterion Benchmarks](assets/screenshot3.jpg)

---

<div align="center">
    <i>NGC Data Node is a data platform designed to process, store, and protect genomic variant information.</i>
</div>
