import random

# GRCh38 chromosome lengths (base pairs)
CHROMOSOMES = {
    "1": 248_956_422,
    "2": 242_193_529,
    "3": 198_295_559,
    "4": 190_154_279,
    "5": 181_538_259,
    "6": 170_805_979,
    "7": 159_345_973,
    "8": 145_138_636,
    "9": 138_394_717,
    "10": 133_797_422,
    "11": 135_086_622,
    "12": 133_275_309,
    "13": 114_364_328,
    "14": 107_043_718,
    "15": 101_991_189,
    "16": 90_338_345,
    "17": 83_257_441,
    "18": 80_373_285,
    "19": 58_617_616,
    "20": 64_444_167,
    "21": 46_709_983,
    "22": 50_818_468,
    "X": 156_040_895,
    "Y": 57_227_415,
    "MT": 16_569,  # Mitochondrial — very short, few variants
}

BASES = ["A", "C", "G", "T"]

# Realistic genotype frequencies for a variant site
# hom-ref (0/0) is rare at a called variant site; het is most common
GENOTYPES = ["0/0", "0/1", "1/1"]
GENOTYPE_PROBS = [0.15, 0.55, 0.30]

NUM_VARIANTS = 100_000

# Weight chromosome selection by chromosome length —
# larger chromosomes accumulate more variants in real WGS data.
chrom_names = list(CHROMOSOMES.keys())
chrom_lengths = [CHROMOSOMES[c] for c in chrom_names]
total_length = sum(chrom_lengths)
chrom_weights = [length / total_length for length in chrom_lengths]


def random_alt(ref: str) -> str:
    """Pick an ALT base that differs from REF (SNP)."""
    return random.choice([b for b in BASES if b != ref])


def random_qual() -> int:
    """Bimodal quality distribution: mostly high-confidence, some marginal calls."""
    return (
        random.randint(20, 59)  # marginal — ~25% of sites
        if random.random() < 0.25
        else random.randint(60, 500)  # high confidence — ~75%
    )


def make_rsid() -> str:
    """~60% of variants in dbSNP have an rsID."""
    return f"rs{random.randint(100_000, 99_999_999)}" if random.random() < 0.60 else "."


with open("data/synthetic_100k.vcf", "w") as f:
    # --- VCF meta-information header ---
    f.write("##fileformat=VCFv4.2\n")
    f.write("##reference=GRCh38\n")
    for chrom, length in CHROMOSOMES.items():
        f.write(f"##contig=<ID={chrom},length={length}>\n")
    f.write(
        '##INFO=<ID=DP,Number=1,Type=Integer,Description="Total read depth at locus">\n'
    )
    f.write(
        '##INFO=<ID=AF,Number=A,Type=Float,Description="Allele frequency in [0,1]">\n'
    )
    f.write('##FILTER=<ID=q20,Description="Quality below 20">\n')
    f.write('##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">\n')
    f.write('##FORMAT=<ID=GQ,Number=1,Type=Integer,Description="Genotype quality">\n')
    f.write('##FORMAT=<ID=DP,Number=1,Type=Integer,Description="Sample read depth">\n')
    f.write("#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tSAMPLE_1\n")

    # --- Variant records ---
    for _ in range(NUM_VARIANTS):
        chrom = random.choices(chrom_names, weights=chrom_weights, k=1)[0]
        pos = random.randint(1, CHROMOSOMES[chrom])
        ref = random.choice(BASES)
        alt = random_alt(ref)
        qual = random_qual()
        filt = "PASS" if qual >= 20 else "q20"
        gt = random.choices(GENOTYPES, weights=GENOTYPE_PROBS, k=1)[0]
        dp = random.randint(8, 120)  # read depth: 8–120× coverage
        gq = min(99, qual)  # genotype quality capped at 99
        af = round(random.uniform(0.0, 1.0), 4)
        rsid = make_rsid()

        info = f"DP={dp};AF={af}"
        sample = f"{gt}:{gq}:{dp}"

        f.write(
            f"{chrom}\t{pos}\t{rsid}\t{ref}\t{alt}\t{qual}\t{filt}\t{info}\tGT:GQ:DP\t{sample}\n"
        )

print(f"✓ Generated {NUM_VARIANTS:,} variants across {len(CHROMOSOMES)} chromosomes")
print(f"  Chromosomes : {', '.join(chrom_names)}")
print("  Output      : data/synthetic_100k.vcf")
