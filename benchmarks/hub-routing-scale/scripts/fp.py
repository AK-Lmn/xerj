#!/usr/bin/env python3
"""Measure the Bloom false-positive collision rate of a signed hub catalogue.

    python3 -I fp.py <catalogue.json> [n_random_terms]

Re-implements the crate's FNV-1a 64 double hashing (xerj-hub/src/sketch.rs) and
probes every corpus's term sketch with random non-existent terms, reporting how
many corpora falsely report "present" per term. Verified against sketch::contains
on known present/absent terms before trusting the aggregate.
"""
import json, base64, random, sys
from collections import Counter

MASK = (1 << 64) - 1

def fnv1a64(bs):
    h = 0xcbf29ce484222325
    for b in bs:
        h ^= b
        h = (h * 0x100000001b3) & MASK
    return h

def present(term, m, k, bits):
    b = term.encode()
    h1, h2 = fnv1a64(b), fnv1a64(b[::-1])
    for i in range(k):
        p = ((h1 + i * h2) & MASK) % m
        if not (bits[p >> 3] >> (p & 7)) & 1:
            return False
    return True

def main():
    cat = json.load(open(sys.argv[1]))
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 20000
    sk = [(e["slug"], e["term_sketch"]["m_bits"], e["term_sketch"]["k_hashes"],
           base64.b64decode(e["term_sketch"]["bits_base64"])) for e in cat["corpora"]]
    nc = len(sk)
    random.seed(1)
    fp = any_hit = 0
    dist = Counter()
    for _ in range(n):
        t = "".join(random.choice("abcdefghijklmnopqrstuvwxyz0123456789_")
                    for _ in range(random.randint(6, 14)))
        hits = sum(1 for (_, m, k, b) in sk if present(t, m, k, b))
        fp += hits
        any_hit += hits > 0
        dist[hits] += 1
    print(f"corpora={nc}  random terms={n}")
    print(f"per-term per-corpus FP rate = {fp/(n*nc):.6f}")
    print(f"false corpora per random term = {fp/n:.3f}")
    print(f"terms hitting >=1 corpus = {100*any_hit/n:.1f}%")

if __name__ == "__main__":
    main()
