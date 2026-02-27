use criterion::{Criterion, black_box, criterion_group, criterion_main};
use noodles_vcf as vcf;
use processor::process_variants;

fn benchmark_vcf_parsing(c: &mut Criterion) {
    // We load the 100k variant file into memory as bytes first.
    // This removes File I/O from the benchmark, so we strictly benchmark CPU processing speed.
    let file_data = std::fs::read("../data/synthetic_100k.vcf")
        .expect("Test data missing. Consider running python generate_vcf.py first!");

    c.bench_function("parse_100k_variants", |b| {
        b.iter(|| {
            // Re-create the reader from the in-memory cursor for each iteration
            let mut cursor = std::io::Cursor::new(&file_data);
            let mut reader = vcf::io::Reader::new(&mut cursor);
            let header = reader.read_header().unwrap();

            // Benchmark the actual parsing and record creation logic
            let records = process_variants(&mut reader, &header).unwrap();

            // Prevent the rust compiler from optimizing the unused list away
            black_box(records);
        })
    });
}

// We lower the sample_size because parsing 100k variants 100 times takes too long for a quick benchmark
criterion_group! {
    name = benches;
    config = Criterion::default().sample_size(10);
    targets = benchmark_vcf_parsing
}
criterion_main!(benches);
