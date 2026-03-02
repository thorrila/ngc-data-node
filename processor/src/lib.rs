pub mod anonymize;
pub mod parquet;

use anyhow::Result;
use arrow::array::{Int64Builder, StringBuilder};
use arrow::datatypes::{DataType, Field, Schema};
use arrow::record_batch::RecordBatch;
use noodles_vcf as vcf;
use noodles_vcf::variant::record::{AlternateBases, Ids};
use std::sync::Arc;

/// Extracted parsing logic so it can be benchmarked by Criterion
pub fn process_variants<R: std::io::BufRead>(
    reader: &mut vcf::io::Reader<R>,
    header: &vcf::Header,
) -> Result<RecordBatch> {
    // Determine the sample ID hash once
    let sample_id = header
        .sample_names()
        .iter()
        .next()
        .map(|s| s.as_str())
        .unwrap_or("UNKNOWN");
    let sample_id_hash = anonymize::hash_id(sample_id);

    // Create Arrow Column Builders
    // Capacity of 100,000 to prevent resizing on our dataset size
    let capacity = 100_000;
    let mut chrom_builder = StringBuilder::with_capacity(capacity, capacity * 5);
    let mut pos_builder = Int64Builder::with_capacity(capacity);
    let mut id_builder = StringBuilder::with_capacity(capacity, capacity);
    let mut ref_builder = StringBuilder::with_capacity(capacity, capacity * 2);
    let mut alt_builder = StringBuilder::with_capacity(capacity, capacity * 2);
    let mut hash_builder = StringBuilder::with_capacity(capacity, capacity * 64);

    for result in reader.records() {
        let record = result?;

        // Chromosome
        chrom_builder.append_value(record.reference_sequence_name());

        // Position
        let pos = record
            .variant_start()
            .and_then(|r| r.ok())
            .map(usize::from)
            .unwrap_or(0) as i64;
        pos_builder.append_value(pos);

        // ID
        if let Some(id) = record.ids().iter().next() {
            id_builder.append_value(id);
        } else {
            id_builder.append_value(".");
        }

        // Reference
        ref_builder.append_value(record.reference_bases());

        // Alternate
        if let Some(Ok(alt)) = record.alternate_bases().iter().next() {
            alt_builder.append_value(alt);
        } else {
            alt_builder.append_value(".");
        }

        // Hash
        hash_builder.append_value(&sample_id_hash);
    }

    // Define Schema
    let schema = Arc::new(Schema::new(vec![
        Field::new("chrom", DataType::Utf8, false),
        Field::new("pos", DataType::Int64, false),
        Field::new("id", DataType::Utf8, true),
        Field::new("reference", DataType::Utf8, false),
        Field::new("alt", DataType::Utf8, false),
        Field::new("sample_id_hash", DataType::Utf8, false),
    ]));

    // Construct RecordBatch
    let batch = RecordBatch::try_new(
        schema,
        vec![
            Arc::new(chrom_builder.finish()),
            Arc::new(pos_builder.finish()),
            Arc::new(id_builder.finish()),
            Arc::new(ref_builder.finish()),
            Arc::new(alt_builder.finish()),
            Arc::new(hash_builder.finish()),
        ],
    )?;

    Ok(batch)
}
