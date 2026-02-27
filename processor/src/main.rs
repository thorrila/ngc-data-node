use anyhow::Result;
use clap::Parser;
use noodles_vcf as vcf;
use processor::{parquet, process_variants};
use std::fs::File;
use std::io::BufReader;
use std::path::PathBuf;

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

    // Call the newly extracted function
    let records = process_variants(&mut reader, &header)?;

    println!(
        "Parsed {} variants. Writing to {:?}...",
        records.num_rows(),
        cli.output
    );

    // Write all records to the Parquet file
    parquet::write_parquet(&records, &cli.output)?;

    println!("Done.");
    Ok(())
}
