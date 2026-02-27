import random
with open("data/synthetic_100k.vcf", "w") as f:
    f.write("##fileformat=VCFv4.2\n")
    f.write("#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tSAMPLE_1\n")
    for i in range(1, 100001):
        chrom = random.choice(["1", "2", "3", "X", "Y"])
        pos = 100000 + i
        f.write(f"{chrom}\t{pos}\t.\tA\tG\t100\tPASS\t.\tGT\t0/1\n")
