todo: add CD, readme, tests, improvements to memory usage, speed etc?

1. Rust Processor (Memory & Speed)
In processor/src/lib.rs, inside the main process_variants loop that parses millions of genomic variants, you have these lines:

rust
ref_builder.append_value(record.reference_bases().to_string().as_str());
alt_builder.append_value(alt.to_string().as_str());
The critique: Calling .to_string() inside a tight loop is a classic performance antipattern. It forces Rust to allocate new memory on the heap for every single variant, copy the string data, and then immediately drop it after appending. On a dataset with 10M+ rows, this will drastically slow down execution and cause massive memory churn. The fix: Avoid heap allocation entirely. The noodles crate usually provides ways to borrow the underlying &str or byte slice directly. You should use something like record.reference_bases().as_ref() (depending on the exact noodles API) so you're just passing a reference to the builder.

Capacity Pre-allocation: Currently, the string builders (StringBuilder::with_capacity(capacity, capacity * 2)) use a hardcoded capacity of 100_000. If you process millions of rows, the underlying vectors will constantly resize, moving data around in memory. If you can't know the exact row count in advance, this is mostly fine, but an interviewer might ask about it.

2. Python Enclave (RAM & Scalability)
In query.py, you are caching the results of DuckDB queries:

python
variant_cache = TTLCache(maxsize=128, ttl=60)
@cached(cache=variant_cache)
def query_variants(...):
    # ...
    result = duckdb.query(sql).fetchall()
    # Convert list of tuples → list of dicts
    return [dict(zip(columns, row)) for row in result]
The critique: fetchall() eagerly loads the entire result set into Python's memory as a list of tuples. Then, you duplicate that data by converting it into a list of dictionaries, and then you store it in the cache. Genomic queries can return huge datasets (millions of rows). If multiple users hit this endpoint concurrently, your Python process will quickly suffer from memory bloat and could crash with an Out of Memory (OOM) error. The fix:

Implement Pagination: Always use LIMIT and OFFSET (or cursor-based pagination) on your endpoints so queries return a predictable, safe amount of data per request (e.g., 1000 rows max).
Use Arrow: DuckDB integrates perfectly with Apache Arrow (duckdb.query().arrow()). Arrow is a zero-copy memory format, which means you can pass the data off to FastAPI directly without creating lists of Python dictionaries, saving massive amounts of RAM and CPU cycles.
3. Regarding leaks <PID> (Applicability)
Yes, using leaks <PID> on macOS is highly relevant and an excellent talking point for your interview!

Because your core processor is written in Rust, which compiles to native binaries without a garbage collector, memory profiling tools like leaks, Instruments (macOS), or valgrind/heaptrack (Linux) are the standard way to verify that your program isn't leaking memory or bloating unnecessarily.
While Rust's borrow checker prevents most traditional memory leaks (like forgetting to free() in C), you can still cause "memory bloat" (holding onto memory for too long) or leak data via reference cycles (Rc/Arc).
If the interviewer asks how you validate the memory footprint of your Rust pipeline, stating that you use leaks <PID> to profile the live process while it parses a heavy VCF file shows incredible maturity in systems engineering.
Overall, the architecture is extremely solid, and addressing these memory allocations in both Rust and Python are exactly the "under-the-hood" details a technical interviewer will love to see you discuss or optimize!
