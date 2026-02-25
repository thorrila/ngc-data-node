use anyhow::Result;
use arrow::array::{Int64Array, StringArray};
use arrow::datatypes::{DataType, Field, Schema};
use arrow::record_batch::RecordBatch;
use parquet::arrow::ArrowWriter;
use parquet::file::properties::WriterProperties;
use std::fs::File;
use std::path::Path;
use std::sync::Arc;

// plain data container - one genomic variant row
pub struct VcfRecord {
    // chromosome
    pub chrom: String,
    // position
    pub pos: i64, // 64-bit integer
    // ID
    pub id: String,
    // reference
    pub reference: String,
    // alternate
    pub alt: String,
    // anonymized patient ID
    pub sample_id_hash: String,
}

// Writes a slice of VcfRecords to a Snappy-compressed Parquet file
pub fn write_parquet(records: &[VcfRecord], output_path: &Path) -> Result<()> {
    // Step 1: define the schema — column names and types
    let schema = Arc::new(Schema::new(vec![
        Field::new("chrom", DataType::Utf8, false),     // required
        Field::new("pos", DataType::Int64, false),      // required
        Field::new("id", DataType::Utf8, true),         // nullable ("." in VCF)
        Field::new("reference", DataType::Utf8, false), // required
        Field::new("alt", DataType::Utf8, false),       // required
        Field::new("sample_id_hash", DataType::Utf8, false), // required
    ]));

    // Step 2: build one Arrow array per column (columnar layout)
    let chrom_array = Arc::new(StringArray::from(
        records.iter().map(|r| r.chrom.as_str()).collect::<Vec<_>>(),
    ));
    let pos_array = Arc::new(Int64Array::from(
        records.iter().map(|r| r.pos).collect::<Vec<_>>(),
    ));
    let id_array = Arc::new(StringArray::from(
        records.iter().map(|r| r.id.as_str()).collect::<Vec<_>>(),
    ));
    let ref_array = Arc::new(StringArray::from(
        records
            .iter()
            .map(|r| r.reference.as_str())
            .collect::<Vec<_>>(),
    ));
    let alt_array = Arc::new(StringArray::from(
        records.iter().map(|r| r.alt.as_str()).collect::<Vec<_>>(),
    ));
    let hash_array = Arc::new(StringArray::from(
        records
            .iter()
            .map(|r| r.sample_id_hash.as_str())
            .collect::<Vec<_>>(),
    ));

    // Step 3: bundle all columns + schema into one RecordBatch
    let batch = RecordBatch::try_new(
        schema.clone(),
        vec![
            chrom_array,
            pos_array,
            id_array,
            ref_array,
            alt_array,
            hash_array,
        ],
    )?;

    // Step 4: write to disk with Snappy compression
    let file = File::create(output_path)?;
    let props = WriterProperties::builder()
        .set_compression(parquet::basic::Compression::SNAPPY)
        .build();
    let mut writer = ArrowWriter::try_new(file, schema, Some(props))?;
    writer.write(&batch)?;
    writer.close()?; // flushes and finalises the file

    Ok(())
}
