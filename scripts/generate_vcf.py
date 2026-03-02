import random

CHROMOSOMES = ["1", "2", "3", "4", "5", "X", "Y"]
BASES = ["A", "C", "G", "T"]

with open("data/synthetic_100k.vcf", "w") as f:
    # VCF header
    f.write("##fileformat=VCFv4.2\n")
    f.write("##reference=GRCh38\n")
    for chrom in CHROMOSOMES:
        f.write(f"##contig=<ID={chrom}>\n")
    f.write("#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tPATIENT_001\n")

    for i in range(1, 100_001):
        chrom = random.choice(CHROMOSOMES)
        pos = random.randint(1, 10_000)  # smaller pool = more shared variants
        ref = random.choice(BASES)
        alt = random.choice([b for b in BASES if b != ref])  # alt must differ from ref
        f.write(f"{chrom}\t{pos}\t.\t{ref}\t{alt}\t100\tPASS\t.\tGT\t0/1\n")