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
                devShells.default = pkgs.mkShell {
                    packages = with pkgs; [
                        # Version control
                        git

                        # Rust
                        cargo
                        rustc
                        clippy  # Rust Linter
                        rustfmt # Rust Formatter    
                        
                        # Python
                        python311
                        uv  # Python Package Manager
                        ruff # PEP8 Python Linter and Formatter
                        pre-commit # Python Pre-commit Hooks

                        # Infrastructure & Databases
                        postgresql 
                        ansible # Configuration Management and Automation Tool
                        docker-client   
                    ];
                    shellHook = ''
                    # Define the 'ngc' command
                    ngc() {
                        # If $1 is empty (-z), "help", "-help", or "--help"
                        if [ -z "$1" ] || [ "$1" = "help" ] || [ "$1" = "-help" ] || [ "$1" = "--help" ]; 
                        then
                            echo "------------------------------------------------------"
                            echo "Commands:"
                            echo "ngc db-up                   - 1. Spins up PostgreSQL database in Docker"
                            echo "ngc setup                   - 2. Installs Python Enclave dependencies"
                            echo "ngc hooks                   - 3. Installs pre-commit Git hooks"
                            echo "ngc run <in.vcf> <out.file> - 4. Converts raw VCFs to Parquet using Rust"
                            echo "ngc serve                   - 5. Starts FastAPI secure enclave on localhost"
                            echo "ngc lint                    - 6. Runs code quality checks"
                            echo "ngc format                  - 7. Auto-formats Rust and Python code"
                            echo "ngc test                    - 8. Runs Rust and Python unit tests"
                            echo "ngc build                   - 9. Compiles Rust Engine for production"
                            echo "ngc deploy                  - 10. Deploys Infrastructure using Ansible"
                            echo "ngc db-down                 - 11. Tears down PostgreSQL database"
                            echo "------------------------------------------------------"                      
                        
                        elif [ "$1" = "run" ]; then
                            # Default values if no arguments are provided
                            INPUT=''${2:-"data/sample.vcf"}
                            OUTPUT=''${3:-"output.json"}
                            
                            echo "Running Rust Processor on $INPUT -> $OUTPUT"
                            cd processor && cargo run -- "../$INPUT" > "../$OUTPUT"
                            cd ..
                        
                        elif [ "$1" = "build" ]; then
                            echo "Building Rust Processor..."
                            cd processor && cargo build --release
                            cd ..
                        
                        elif [ "$1" = "setup" ]; then
                            echo "Setting up Python Enclave..."
                            cd enclave && uv sync
                            cd ..
                        
                        elif [ "$1" = "hooks" ]; then
                            echo "Installing Pre-commit Hooks..."
                            pre-commit install
                            echo "Running Pre-commit checks on all files..."
                            pre-commit run --all-files
                        
                        elif [ "$1" = "serve" ]; then
                            echo "Starting FastAPI Secure Enclave..."
                            # uv run ensures the command runs in the isolated virtual environment
                            cd enclave && uv run fastapi dev api/main.py
                            cd ..
                        
                        elif [ "$1" = "lint" ]; then
                            echo "Running Linters..."
                            echo "1. Running Rust Clippy..."
                            cd processor && cargo clippy -- -D warnings
                            echo "2. Running Python Ruff..."
                            cd ../enclave && uv run ruff check .
                            cd ..
                        
                        elif [ "$1" = "format" ]; then
                            echo "Formatting Codebase..."
                            echo "1. Formatting Rust files..."
                            cd processor && cargo fmt
                            echo "2. Formatting Python files..."
                            cd ../enclave && uv run ruff format .
                            cd ..
                            
                        elif [ "$1" = "test" ]; then
                            echo "Running Test Suites..."
                            echo "1. Testing Rust Engine..."
                            cd processor && cargo test
                            echo "2. Testing Python API..."
                            cd ../enclave && uv run pytest
                            cd ..
                        
                        elif [ "$1" = "db-up" ]; then
                            echo "Starting PostgreSQL Database..."
                            docker compose -f docker-compose.yml up -d
                            
                        elif [ "$1" = "deploy" ]; then
                            echo "Deploying Infrastructure with Ansible..."
                            ansible-playbook deploy.yml
                        
                        elif [ "$1" = "db-down" ]; then
                            echo "Stopping PostgreSQL Database..."
                            docker compose -f docker-compose.yml down
                        
                        else
                            echo "Unknown argument '$1'. Try 'ngc help'"
                        fi
                    }
                    echo "------------------------------------------------------"
                    echo "Welcome to the NGC Data Node Development Environment!"
                    echo "$(python3 --version)"
                    echo "$(ruff --version)"
                    echo "$(cargo --version | cut -d' ' -f1-2)" 
                    echo "Type 'ngc' to see a list of quick commands."
                    echo "Type 'exit' to leave this isolated environment." 
                    echo "------------------------------------------------------"
                '';
                };
            }   
        );
}

        