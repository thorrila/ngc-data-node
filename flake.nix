{
    description = "NGC Data Node Development Environment";

    inputs = {
        nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";
        flake-utils.url = "github:numtide/flake-utils";
    };

    outputs = {self, nixpkgs, flake-utils }:
        flake-utils.lib.eachDefaultSystem (system:
            let
                pkgs = nixpkgs.legacyPackages.${system};
            in
            {
                packages.default = pkgs.rustPlatform.buildRustPackage {
                    pname = "ngc-processor";
                    version = "0.1.0";
                    src = ./processor;
                    cargoLock.lockFile = ./processor/Cargo.lock;
                    
                    # Ensure iconv is available for Darwin builds (samply/flamegraph)
                    buildInputs = pkgs.lib.optionals pkgs.stdenv.isDarwin [ pkgs.libiconv ];
                };

                apps.default = {
                    type = "app";
                    program = "${self.packages.${system}.default}/bin/processor";
                };

                devShells.default = pkgs.mkShell {
                    packages = with pkgs; [
                        # Version control
                        git

                        # Rust
                        cargo
                        rustc
                        clippy  # Rust Linter
                        rustfmt # Rust Formatter
                        libiconv # For cargo-flamegraph

                        # Python
                        python311
                        uv  # Python Package Manager
                        ruff # PEP8 Python Linter and Formatter
                        pre-commit # Python Pre-commit Hooks

                        # Infrastructure & Databases
                        postgresql
                        ansible # Infrastructure provisioning
                        docker-client # CLI only — daemon runs on the host system
                    ];
                    shellHook = ''
                    # Absolute path to project root — works from any subdirectory
                    NGC_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)

                    # Define the 'ngc' command
                    ngc() {
                        # If $1 is empty (-z), "help", "-help", or "--help"
                        if [ -z "$1" ] || [ "$1" = "help" ] || [ "$1" = "-help" ] || [ "$1" = "--help" ];
                        then
                            echo "------------------------------------------------------"
                            echo "Commands:"
                            echo "ngc demo                    - 0. runs the full pipeline"
                            echo "ngc setup                   - 1. python dependencies"
                            echo "ngc hooks                   - 2. pre-commit hooks"
                            echo "ngc db-up                   - 3. start database"
                            echo "ngc generate                - 4. generate VCF data"
                            echo "ngc run                     - 5. process VCF → Parquet"
                            echo "ngc serve                   - 6. start API"
                            echo "ngc deploy                  - 7. provision with Ansible"
                            echo "ngc db-down                 - 8. stop database"
                            echo "ngc test                    - 9. run tests (rust + python)"
                            echo "ngc polish                  - 10. format + lint + test in one go"
                            echo "ngc lint                    - 11. code quality checks"
                            echo "ngc format                  - 12. auto-format"
                            echo "ngc build                   - 13. compile release binary"
                            echo "ngc bench                   - 14. benchmarks"
                            echo "ngc profile                 - 15. CPU flamegraph"
                            echo "ngc locust                  - 16. load tests"
                            echo "ngc logs                    - 17. view audit logs"
                            echo "ngc query <sql>             - 18. custom SQL"
                            echo "ngc clean                   - 19. clean artifacts"                            
                            echo "------------------------------------------------------"

                        elif [ "$1" = "run" ]; then
                            # Default values if no arguments are provided
                            INPUT=''${2:-"data/synthetic_100k.vcf"}
                            OUTPUT=''${3:-"data/output.parquet"}

                            echo "Running Rust Processor on $INPUT -> $OUTPUT"
                            (cd "$NGC_ROOT/processor" && cargo run -- --input "$NGC_ROOT/$INPUT" --output "$NGC_ROOT/$OUTPUT")

                        elif [ "$1" = "bench" ]; then
                            echo "Running Micro-Benchmarks cleanly inside Nix Environment..."
                            (cd "$NGC_ROOT/processor" && cargo bench)

                        elif [ "$1" = "profile" ]; then
                            echo "Running CPU Profiler (Samply)..."
                            echo "This will automatically open a Firefox Profiler tab in your browser when finished."
                            (cd "$NGC_ROOT/processor" && samply record cargo bench)

                        elif [ "$1" = "build" ]; then
                            echo "Building Rust Processor..."
                            (cd "$NGC_ROOT/processor" && cargo build --release)

                        elif [ "$1" = "setup" ]; then
                            echo "Setting up Python Enclave..."
                            (cd "$NGC_ROOT/enclave" && uv sync)

                        elif [ "$1" = "hooks" ]; then
                            echo "Installing Pre-commit Hooks..."
                            pre-commit install
                            echo "Running Pre-commit checks on all files..."
                            pre-commit run --all-files

                        elif [ "$1" = "serve" ]; then
                            echo "Starting FastAPI Secure Enclave..."
                            echo "🔗 Documentation: http://127.0.0.1:8000/docs"
                            # Open browser in 2 seconds (giving the server time to start)
                            (sleep 2 && open http://127.0.0.1:8000/docs) &
                            (cd "$NGC_ROOT/enclave" && uv run fastapi dev src/ngc_enclave/main.py)

                        elif [ "$1" = "lint" ]; then
                            echo "Running Linters..."
                            echo "1. Running Rust Clippy..."
                            (cd "$NGC_ROOT/processor" && cargo clippy -- -D warnings)
                            echo "2. Running Python Ruff..."
                            (cd "$NGC_ROOT/enclave" && uv run ruff check .)

                        elif [ "$1" = "format" ]; then
                            echo "Formatting Codebase..."
                            echo "1. Formatting Rust files..."
                            (cd "$NGC_ROOT/processor" && cargo fmt)
                            echo "2. Formatting Python files..."
                            (cd "$NGC_ROOT/enclave" && uv run ruff format .)

                        elif [ "$1" = "test" ]; then
                            echo "Running Tests..."
                            echo "1. Testing Rust Engine..."
                            (cd "$NGC_ROOT/processor" && cargo test)
                            echo "2. Testing Python API..."
                            (cd "$NGC_ROOT/enclave" && uv run pytest)

                        elif [ "$1" = "db-up" ]; then
                            echo "Starting PostgreSQL Database..."
                            docker compose -f "$NGC_ROOT/docker-compose.yml" up -d

                        elif [ "$1" = "logs" ]; then
                            echo "Retrieving access logs..."
                            docker exec -it ngc-data-node-postgres-1 psql -U ngc -d ngc -c "SELECT * FROM audit_log ORDER BY ts DESC LIMIT 20;"

                        elif [ "$1" = "query" ]; then
                            if [ -z "$2" ]; then
                                echo "Error: Please provide a SQL query."
                                echo "Usage: ngc query \"SELECT * FROM audit_log\""
                            else
                                docker exec -it ngc-data-node-postgres-1 psql -U ngc -d ngc -c "$2"
                            fi

                        elif [ "$1" = "deploy" ]; then
                            echo "Deploying NGC Data Node..."
                            ansible-playbook "$NGC_ROOT/infra/ansible/playbook.yml"     

                        elif [ "$1" = "db-down" ]; then
                            echo "Stopping PostgreSQL Database..."
                            docker compose -f "$NGC_ROOT/docker-compose.yml" down

                        elif [ "$1" = "clean" ]; then
                            echo "Cleaning up artifacts and caches..."
                            find "$NGC_ROOT" -name "__pycache__" -type d -exec rm -rf {} +
                            find "$NGC_ROOT" -name ".pytest_cache" -type d -exec rm -rf {} +
                            find "$NGC_ROOT" -name ".ruff_cache" -type d -exec rm -rf {} +
                            rm -fv "$NGC_ROOT"/data/*.parquet 2>/dev/null || true
                            rm -fv "$NGC_ROOT"/data/*.vcf 2>/dev/null || true
                            echo "Project is clean."

                        elif [ "$1" = "generate" ]; then
                            echo "Generating synthetic VCF data..."
                            python3 scripts/generate_vcf.py

                        elif [ "$1" = "polish" ]; then
                            echo "Polishing the codebase (Format -> Lint -> Test)..."
                            ngc format
                            ngc lint
                            ngc db-up
                            ngc test
                            ngc db-down
                            echo "Codebase is polished."

                        elif [ "$1" = "locust" ]; then
                            echo "Starting Locust API Load Tester..."
                            (cd "$NGC_ROOT/enclave" && uv run locust -f ../scripts/locustfile.py)

                        elif [ "$1" = "demo" ]; then
                            echo "Running demo..."
                            ngc setup
                            ngc db-up
                            ngc generate
                            ngc run
                            ngc serve

                        else
                            echo "Unknown argument '$1'. Try 'ngc help'"
                        fi
                    }
                    echo "------------------------------------------------------"
                    echo "Welcome to the NGC Data Node Development Environment!"
                    echo "$(python3 --version)"
                    echo "$(ruff --version)"
                    echo "$(cargo --version | cut -d' ' -f1-2)"
                    echo "Type 'ngc demo' to run the full demo pipeline."
                    echo "Type 'ngc' to see a list of commands."
                    echo "Type 'exit' to leave this isolated environment."
                    echo "------------------------------------------------------"
                '';
                };
            }
        );
}
