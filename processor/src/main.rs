mod anonymize;
mod parquet;

use anyhow::Result;
use clap::Parser;
use noodles_vcf as vcf;
use noodles_vcf::variant::record::AlternateBases;
use noodles_vcf::variant::record::Ids;
use parquet::VcfRecord;
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

    let mut records: Vec<VcfRecord> = Vec::new();

    // Iterate over each variant record in the VCF
    for result in reader.records() {
        let record = result?;

        // Extract the chromosome name (e.g. "1", "17")
        let chrom = record.reference_sequence_name().to_string();

        // Extract the genomic position (1-based in VCF, stored as i64)
        let pos = record
            .variant_start()
            .and_then(|r| r.ok())
            .map(usize::from)
            .unwrap_or(0) as i64;

        // Extract the variant ID (e.g. "rs001"), defaulting to "." if absent
        let id = record
            .ids()
            .iter()
            .next()
            .map(|s: &str| s.to_string())
            .unwrap_or_else(|| ".".to_string());

        // Reference allele (e.g. "A")
        let reference = record.reference_bases().to_string();

        // Alternate allele — take the first one (e.g. "T")
        let alt = record
            .alternate_bases()
            .iter()
            .next()
            .and_then(|r| r.ok())
            .map(|a| a.to_string())
            .unwrap_or_else(|| ".".to_string());

        // Hash the first sample column name (the patient ID) for anonymisation
        let sample_id = header
            .sample_names()
            .iter()
            .next()
            .map(|s| s.as_str())
            .unwrap_or("UNKNOWN");
        let sample_id_hash = anonymize::hash_id(sample_id);

        records.push(VcfRecord {
            chrom,
            pos,
            id,
            reference,
            alt,
            sample_id_hash,
        });
    }

    println!(
        "Parsed {} variants. Writing to {:?}...",
        records.len(),
        cli.output
    );

    // Write all records to the Parquet file
    parquet::write_parquet(&records, &cli.output)?;

    println!("Done.");
    Ok(())
}
