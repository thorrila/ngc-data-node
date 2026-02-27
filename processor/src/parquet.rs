use anyhow::Result;
use arrow::record_batch::RecordBatch;
use parquet::arrow::ArrowWriter;
use parquet::file::properties::WriterProperties;
use std::fs::File;
use std::path::Path;

// Writes a RecordBatch to a Snappy-compressed Parquet file
pub fn write_parquet(batch: &RecordBatch, output_path: &Path) -> Result<()> {
    let file = File::create(output_path)?;
    let props = WriterProperties::builder()
        .set_compression(parquet::basic::Compression::SNAPPY)
        .build();
    let mut writer = ArrowWriter::try_new(file, batch.schema(), Some(props))?;
    writer.write(batch)?;
    writer.close()?; // flushes and finalises the file

    Ok(())
}
