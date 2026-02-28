import random

with open("data/synthetic_100k.vcf", "w") as f:
    f.write("##fileformat=VCFv4.2\n")
    f.write("#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tSAMPLE_1\n")
    for i in range(1, 100001):
        # We use a smaller pool of chromosomes and positions to force "collisions" (shared variants)
        chrom = random.choice(["1", "2"])
        pos = random.randint(1, 1000)
        f.write(f"{chrom}\t{pos}\t.\tA\tG\t100\tPASS\t.\tGT\t0/1\n")
