pub mod anonymize;

// Alias the parquet *crate* so it doesn't conflict with our local `parquet` module.
use ::parquet::arrow::arrow_writer::ArrowWriter;
use ::parquet::basic::Compression;
use ::parquet::file::properties::WriterProperties;

use anyhow::Result;
use arrow::array::{Int64Builder, StringBuilder};
use arrow::datatypes::{DataType, Field};
use arrow::record_batch::RecordBatch;
use noodles_vcf as vcf;
use noodles_vcf::variant::record::{AlternateBases, Ids};
use std::fs::File;
use std::path::Path;
use std::sync::Arc;

/// Shared Arrow schema for genomic variants. Defined once so both functions stay in sync.
fn variant_schema() -> Arc<arrow::datatypes::Schema> {
    Arc::new(arrow::datatypes::Schema::new(vec![
        Field::new("chrom", DataType::Utf8, false),
        Field::new("pos", DataType::Int64, false),
        Field::new("id", DataType::Utf8, true),
        Field::new("reference", DataType::Utf8, false),
        Field::new("alt", DataType::Utf8, false),
        Field::new("sample_id_hash", DataType::Utf8, false),
    ]))
}

/// Helper — builds one RecordBatch from the six column builders.
fn finish_batch(
    schema: Arc<arrow::datatypes::Schema>,
    chrom: &mut StringBuilder,
    pos: &mut Int64Builder,
    id: &mut StringBuilder,
    reference: &mut StringBuilder,
    alt: &mut StringBuilder,
    hash: &mut StringBuilder,
) -> Result<RecordBatch> {
    Ok(RecordBatch::try_new(
        schema,
        vec![
            Arc::new(chrom.finish()),
            Arc::new(pos.finish()),
            Arc::new(id.finish()),
            Arc::new(reference.finish()),
            Arc::new(alt.finish()),
            Arc::new(hash.finish()),
        ],
    )?)
}

/// Streaming writer — reads the VCF and writes Parquet in fixed-size batches.
///
/// Unlike `process_variants`, this never holds more than `batch_size` rows in
/// memory at once, so peak RAM is O(batch_size) rather than O(file size).
/// This is the production entry point for the CLI.
pub fn stream_variants_to_parquet<R: std::io::BufRead>(
    reader: &mut vcf::io::Reader<R>,
    header: &vcf::Header,
    output_path: &Path,
    batch_size: usize,
) -> Result<u64> {
    let sample_id = header
        .sample_names()
        .iter()
        .next()
        .map(|s| s.as_str())
        .unwrap_or("UNKNOWN");
    let sample_id_hash = anonymize::hash_id(sample_id);

    let schema = variant_schema();

    // Open Parquet writer — Snappy compression for a good speed/size trade-off
    let file = File::create(output_path)?;
    let props = WriterProperties::builder()
        .set_compression(Compression::SNAPPY)
        .build();
    let mut writer = ArrowWriter::try_new(file, schema.clone(), Some(props))?;

    // Allocate builders with batch_size capacity; they are re-used per batch.
    let mut chrom_b = StringBuilder::with_capacity(batch_size, batch_size * 5);
    let mut pos_b = Int64Builder::with_capacity(batch_size);
    let mut id_b = StringBuilder::with_capacity(batch_size, batch_size);
    let mut ref_b = StringBuilder::with_capacity(batch_size, batch_size * 2);
    let mut alt_b = StringBuilder::with_capacity(batch_size, batch_size * 2);
    let mut hash_b = StringBuilder::with_capacity(batch_size, batch_size * 16);

    let mut row_count: u64 = 0;
    let mut batch_rows: usize = 0;

    for result in reader.records() {
        let record = result?;

        chrom_b.append_value(record.reference_sequence_name());

        let pos = record
            .variant_start()
            .and_then(|r| r.ok())
            .map(usize::from)
            .unwrap_or(0) as i64;
        pos_b.append_value(pos);

        if let Some(id) = record.ids().iter().next() {
            id_b.append_value(id);
        } else {
            id_b.append_value(".");
        }

        ref_b.append_value(record.reference_bases().to_string().as_str());

        if let Some(Ok(alt)) = record.alternate_bases().iter().next() {
            alt_b.append_value(alt.to_string().as_str());
        } else {
            alt_b.append_value(".");
        }

        hash_b.append_value(&sample_id_hash);

        row_count += 1;
        batch_rows += 1;

        // When we've collected batch_size rows, flush to disk and reset the builders.
        if batch_rows == batch_size {
            let batch = finish_batch(
                schema.clone(),
                &mut chrom_b,
                &mut pos_b,
                &mut id_b,
                &mut ref_b,
                &mut alt_b,
                &mut hash_b,
            )?;
            writer.write(&batch)?;
            batch_rows = 0;
        }
    }

    // Flush any remaining rows that didn't fill a complete batch
    if batch_rows > 0 {
        let batch = finish_batch(
            schema.clone(),
            &mut chrom_b,
            &mut pos_b,
            &mut id_b,
            &mut ref_b,
            &mut alt_b,
            &mut hash_b,
        )?;
        writer.write(&batch)?;
    }

    writer.close()?;
    Ok(row_count)
}

/// Accumulates all variants into a single RecordBatch.
/// Kept for benchmark use — do not use this for large production files.
pub fn process_variants<R: std::io::BufRead>(
    reader: &mut vcf::io::Reader<R>,
    header: &vcf::Header,
) -> Result<RecordBatch> {
    let sample_id = header
        .sample_names()
        .iter()
        .next()
        .map(|s| s.as_str())
        .unwrap_or("UNKNOWN");
    let sample_id_hash = anonymize::hash_id(sample_id);

    let capacity = 100_000;
    let mut chrom_builder = StringBuilder::with_capacity(capacity, capacity * 5);
    let mut pos_builder = Int64Builder::with_capacity(capacity);
    let mut id_builder = StringBuilder::with_capacity(capacity, capacity);
    let mut ref_builder = StringBuilder::with_capacity(capacity, capacity * 2);
    let mut alt_builder = StringBuilder::with_capacity(capacity, capacity * 2);
    let mut hash_builder = StringBuilder::with_capacity(capacity, capacity * 64);

    for result in reader.records() {
        let record = result?;

        chrom_builder.append_value(record.reference_sequence_name());

        let pos = record
            .variant_start()
            .and_then(|r| r.ok())
            .map(usize::from)
            .unwrap_or(0) as i64;
        pos_builder.append_value(pos);

        if let Some(id) = record.ids().iter().next() {
            id_builder.append_value(id);
        } else {
            id_builder.append_value(".");
        }

        // Reference
        ref_builder.append_value(record.reference_bases());

        if let Some(Ok(alt)) = record.alternate_bases().iter().next() {
            alt_builder.append_value(alt);
        } else {
            alt_builder.append_value(".");
        }

        hash_builder.append_value(&sample_id_hash);
    }

    let schema = variant_schema();

    Ok(RecordBatch::try_new(
        schema,
        vec![
            Arc::new(chrom_builder.finish()),
            Arc::new(pos_builder.finish()),
            Arc::new(id_builder.finish()),
            Arc::new(ref_builder.finish()),
            Arc::new(alt_builder.finish()),
            Arc::new(hash_builder.finish()),
        ],
    )?)
}
