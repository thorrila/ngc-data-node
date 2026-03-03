use anyhow::Result;
use clap::Parser;
use noodles_vcf as vcf;
use processor::stream_variants_to_parquet;
use std::fs::File;
use std::io::BufReader;
use std::path::PathBuf;

/// Number of VCF rows buffered in RAM before flushing to the Parquet file.
/// 10k rows ≈ a few MB — safe even on machines with very limited RAM.
const BATCH_SIZE: usize = 10_000;

// CLI argument struct — Clap reads --input and --output from the command line
#[derive(Parser)]
#[command(
    name = "processor",
    about = "VCF → Parquet converter with anonymization"
)]
struct Cli {
    /// Input VCF file path
    #[arg(short, long)]
    input: PathBuf,

    /// Output Parquet file path
    #[arg(short, long)]
    output: PathBuf,
}

fn main() -> Result<()> {
    // Parse CLI args — Clap fills the struct from argv automatically
    let cli = Cli::parse();

    // Open the VCF file; BufReader adds buffering for efficient line-by-line reading
    let file = File::open(&cli.input)?;
    let mut reader = vcf::io::Reader::new(BufReader::new(file));

    // Read the VCF header (contains sample names, contig definitions, FORMAT/INFO fields)
    let header = reader.read_header()?;

    println!("Streaming {:?} → {:?} ...", cli.input, cli.output);

    // Stream variants in fixed-size batches — peak RAM = BATCH_SIZE rows, not the whole file
    let row_count = stream_variants_to_parquet(&mut reader, &header, &cli.output, BATCH_SIZE)?;

    println!("Done. Wrote {row_count} variants.");
    Ok(())
}
