<div align="center">

# 🧬 NGC Data Node

[![Rust](https://img.shields.io/badge/rust-stable-%23E34F26.svg?style=flat-square&logo=rust)](https://www.rust-lang.org/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg?style=flat-square&logo=python)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com)
[![DuckDB](https://img.shields.io/badge/DuckDB-FFF000?style=flat-square&logo=duckdb)](https://duckdb.org/)
[![Nix](https://img.shields.io/badge/Nix-Reproducible-5277C3.svg?style=flat-square&logo=Nixos)](https://nixos.org/)

**High-Performance, Secure Infrastructure for Genomic Variant Data**

NGC Data Node is a specialized, dual-engine data platform designed to process, store, and protect genomic variant information at scale. By combining the zero-copy memory safety of **Rust** with the analytical power of **DuckDB** and a **FastAPI** secure enclave, the node provides researchers with rapid, audited data access.

</div>

---

## ✨ Features

- **Zero-Copy Parsing:** A custom Rust parser ingests `.VCF` files in streaming batches, writing directly to Apache Parquet without loading the entire file into memory.
- **Sub-5ms API:** DuckDB scans Parquet files and serves results via a thread-safe, TTL-cached async API with a `~2ms` median response time under 100 concurrent users.
- **Secure Enclave:** API access is gatekept with API keys and an immutable Postgres audit log.
- **Safe by Design:** Genomic data is anonymized via BLAKE3 hashing, and all query parameters are fully SQL-injection proof via DuckDB parameterized queries.
- **Reproducible Environment:** Fully isolated dependency management driven by a `flake.nix` configuration.
- **Developer DX:** The `ngc` CLI utility manages the entire stack from code to deployment.

---

## 🛠️ Developer Environment (Nix)

The easiest and most reliable way to work on this project is by using the provided **Nix Flake**, which sets up a fully reproducible development environment and a custom helper CLI.

### 1. Enter the Environment
```bash
nix develop
```

### 2. The `ngc` Developer CLI
While inside the Nix shell, the `ngc` command exposes powerful lifecycle hooks:

| Command | Description |
| :--- | :--- |
| `ngc demo` | **The "Easy Button"**: Runs setup, starts DB, generates data, processes VCF to Parquet, and starts the API. |
| `ngc setup` | Syncs Python dependencies via `uv`. |
| `ngc db-up` / `db-down` | Lifecycle management for the PostgreSQL Docker container. |
| `ngc generate` | Creates a synthetic 100k variant VCF testing file. |
| `ngc run` | Compiles and runs the Rust Processor against the VCF data. |
| `ngc serve` | Starts the FastAPI server and opens the SWAGGER documentation. |
| `ngc test` | Runs the full test suite (Rust unit tests + Python PyTest). |
| `ngc locust` | Triggers the Locust Load Testing tool for performance analysis. |
| `ngc help` | Shows all available developer commands. |

---

## 🚀 Native Workflows (Without Nix)

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

## 🏗️ System Architecture

Our hybrid architecture isolates the heavy "Extract, Transform, Load" (ETL) workload into a highly optimized systems language (Rust), while exposing the flexible query API via Python.

*Architecture diagram — see Evidence section below.*

---

## 🔌 API Endpoints

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

## 🏎️ Performance & Scalability

Our system is rigorously stress-tested at two levels: the low-level data ingestion engine (Rust) and the high-level API enclave (Python).

**Data Ingestion Benchmarks (Rust/Criterion):**
- **Micro: BLAKE3 Crypto Hash:** `~130 ns` per sample ID.
- **Micro: VCF String Parsing:** `~12.8 ms` to parse raw strings.
- **Macro: Parse 100k Variants:** `~20.2 ms` total execution time for the full 100,000 variant ingestion pipeline.

**API Load Testing (Python/FastAPI) — 100 concurrent users, 300+ RPS:**
- **p50 Response Time:** `~2ms` (cache-served requests).
- **p95 Response Time:** `~5ms` (brief spike during initial cache warm-up only; steady-state is sub-5ms).
- **Throughput:** `300+ RPS` sustained with **0% failure rate**.
- **Payload Size:** `~95KB` for `/variants` (1,000 row default limit), `~8.7KB` for `/alleles` (100 row cap).
- **Concurrency Model:** Sync DuckDB calls offloaded to thread pool via `asyncio.to_thread`; cache protected by `threading.Lock` to prevent thundering herd.
- **Scaling Note:** Multi-million variant datasets have not yet been benchmarked; performance will depend on Parquet file size and available memory.

*(Run `ngc bench` to replicate the Rust data pipeline benchmarks, or `ngc locust` for API load testing).*

---

## 📸 Evidence

Here are the latest runtime measurements from our local test environment:

### Python Enclave (Locust API Load Test)
![Locust Load Test Charts](assets/screenshot1.jpg)

![Locust Load Test Statistics](assets/screenshot2.jpg)

### Rust Processor (Criterion Benchmarks)
![Rust Criterion Benchmarks](assets/screenshot3.jpg)

---

<div align="center">
    <i>Built for speed. Secured by design.</i>
</div>
