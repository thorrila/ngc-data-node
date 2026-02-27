pub mod anonymize;
pub mod parquet;

use anyhow::Result;
use noodles_vcf as vcf;
use noodles_vcf::variant::record::AlternateBases;
use noodles_vcf::variant::record::Ids;
pub use parquet::VcfRecord;

/// Extracted parsing logic so it can be benchmarked by Criterion
pub fn process_variants<R: std::io::BufRead>(
    reader: &mut vcf::io::Reader<R>,
    header: &vcf::Header,
) -> Result<Vec<VcfRecord>> {
    let mut records: Vec<VcfRecord> = Vec::new();

    let sample_id = header
        .sample_names()
        .iter()
        .next()
        .map(|s| s.as_str())
        .unwrap_or("UNKNOWN");
    let sample_id_hash = anonymize::hash_id(sample_id);

    for result in reader.records() {
        let record = result?;
        let chrom = record.reference_sequence_name().to_string();
        let pos = record
            .variant_start()
            .and_then(|r| r.ok())
            .map(usize::from)
            .unwrap_or(0) as i64;
        let id = record
            .ids()
            .iter()
            .next()
            .map(|s: &str| s.to_string())
            .unwrap_or_else(|| ".".to_string());
        let reference = record.reference_bases().to_string();
        let alt = record
            .alternate_bases()
            .iter()
            .next()
            .and_then(|r| r.ok())
            .map(|a| a.to_string())
            .unwrap_or_else(|| ".".to_string());

        records.push(VcfRecord {
            chrom,
            pos,
            id,
            reference,
            alt,
            sample_id_hash,
        });
    }
    Ok(records)
}
