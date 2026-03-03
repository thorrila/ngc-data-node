use criterion::{Criterion, black_box, criterion_group, criterion_main};
use noodles_vcf as vcf;
use processor::{anonymize, process_variants};

// 1. Macrometrics: Benchmarks the entire pipeline end-to-end
// This processes all 100k variants, parses them into structs, hashes their IDs,
// and maps them to an Apache Arrow representation.
fn benchmark_pipeline_macro(c: &mut Criterion) {
    let file_data = std::fs::read("../data/synthetic_100k.vcf")
        .expect("Test data missing. Consider running 'ngc generate' first!");

    c.bench_function("macro_parse_100k_variants", |b| {
        b.iter(|| {
            let mut cursor = std::io::Cursor::new(&file_data);
            let mut reader = vcf::io::Reader::new(&mut cursor);
            let header = reader.read_header().unwrap();

            let records = process_variants(&mut reader, &header).unwrap();
            black_box(records); // Prevent compiler from optimizing the unused list away
        })
    });
}

// 2. Micrometrics: Benchmarks raw VCF string parsing using the Noodles library
// This strips away hashing and struct conversion to just measure exact string handling.
fn benchmark_vcf_parsing_micro(c: &mut Criterion) {
    let file_data = std::fs::read("../data/synthetic_100k.vcf")
        .expect("Test data missing. Consider running 'ngc generate' first!");

    c.bench_function("micro_vcf_string_parsing", |b| {
        b.iter(|| {
            let mut cursor = std::io::Cursor::new(&file_data);
            let mut reader = vcf::io::Reader::new(&mut cursor);
            let _header = reader.read_header().unwrap();

            // We use raw iteration to avoid allocating memory for all 100k variants at once
            // This strictly measures iterator speed, not ArrayList allocation overhead
            for result in reader.records() {
                let _record = result.unwrap();
                black_box(_record);
            }
        })
    });
}

// 3. Micrometrics: Benchmarks purely the Rust math speed of the BLAKE3 hashing algorithm.
// BLAKE3 is a fast, cryptographically secure hash — used here to pseudonymise sample IDs.
fn benchmark_blake3_micro(c: &mut Criterion) {
    c.bench_function("micro_blake3_crypto_hash", |b| {
        b.iter(|| {
            // Simulate hashing a generic string representation of a variant
            // We use the exposed hash_id function to hash a standard signature
            let hash = anonymize::hash_id("chr1_1000_A_T");
            black_box(hash);
        })
    });
}

// We lower the sample_size because parsing 100k variants taking 30ms each is too slow
// for the default 100-sample macro benchmark iteration.
criterion_group! {
    name = benches;
    config = Criterion::default().sample_size(10);
    targets = benchmark_blake3_micro, benchmark_vcf_parsing_micro, benchmark_pipeline_macro
}
criterion_main!(benches);
