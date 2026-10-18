//! Corpus Hub v2 — catalogue scale measurement (benchmarks/hub-routing-scale).
//!
//! Not part of the shipped binary. Three subcommands:
//!
//! ```text
//! hub_scale extract  <code_home> <registry> <slug> <out_dir>
//! hub_scale catalogue <registry> <terms_dir> <out.json> <seed_hex> [--synthetic-rest]
//! hub_scale route    <catalogue.json> <cases.jsonl> [--verbose]
//! ```
//!
//! `extract` reads a corpus cloned by `xerj corpus add` (the clone `hub
//! build-pack` indexes) and runs the pack builder's node-free extraction
//! ([`xerj_hub::pack::build_defs_and_files`]) and the catalogue builder's term
//! rule ([`xerj_hub::build_catalogue::sketch_terms`]) — so the terms written are
//! exactly the ones `build-catalogue` would hash for that pack, without paying
//! for indexing and a snapshot. Output: `<slug>.terms` (distinct terms, one per
//! line) and `<slug>.stats` (`slug files defs distinct_terms`).
//!
//! `catalogue` builds a signed catalogue through the real
//! [`xerj_hub::catalogue::build_catalogue`] (so metadata, sketch sizing and the
//! canonical bytes are the production ones) from every `<slug>.terms` in
//! `terms_dir`. With `--synthetic-rest`, every other live lane-A corpus in the
//! backlog is added with a SYNTHETIC sketch over its description words, slug
//! parts and topic tags only (the "registry-only" entries of RESULTS.md).
//!
//! `route` loads a catalogue, routes every labelled question (`{"q", "deps",
//! "expected"}`; `expected` may be `null` for an out-of-hub question) and
//! prints verdict precision and per-question routing latency.

use std::collections::BTreeMap;
use std::fs;
use std::path::{Path, PathBuf};
use std::time::Instant;

use serde_json::Value;
use xerj_hub::catalogue::{build_catalogue, canonical_json, CorpusBuildInput};
use xerj_hub::router::{route_ranked, Routing};
use xerj_hub::Catalogue;

fn main() {
    let args: Vec<String> = std::env::args().skip(1).collect();
    let rc = match args.first().map(String::as_str) {
        Some("extract") => extract(&args[1..]),
        Some("catalogue") => catalogue(&args[1..]),
        Some("route") => route_cases(&args[1..]),
        _ => {
            eprintln!("usage: hub_scale extract|catalogue|route …");
            Err(anyhow::anyhow!("bad usage"))
        }
    };
    if let Err(e) = rc {
        eprintln!("hub_scale: {e:#}");
        std::process::exit(1);
    }
}

fn backlog_rows(registry: &Path) -> anyhow::Result<Vec<Value>> {
    let b: Value = serde_json::from_str(&fs::read_to_string(
        registry.join("backlog/backlog-100.json"),
    )?)?;
    Ok(b["corpora"]
        .as_array()
        .cloned()
        .unwrap_or_default()
        .into_iter()
        .filter(|r| r["status"] == "live" && r["lane"] == "A")
        .collect())
}

fn extract(a: &[String]) -> anyhow::Result<()> {
    let [code_home, registry, slug, out] = a else {
        anyhow::bail!("extract <code_home> <registry> <slug> <out_dir>");
    };
    let registry = PathBuf::from(registry);
    let row = backlog_rows(&registry)?
        .into_iter()
        .find(|r| r["slug"] == slug.as_str())
        .ok_or_else(|| anyhow::anyhow!("{slug} is not a live lane-A corpus"))?;
    let manifest: Value =
        serde_json::from_str(&fs::read_to_string(registry.join(format!("{slug}.json")))?)?;
    let root = Path::new(code_home).join("corpora").join(slug);
    let (defs, files) = xerj_hub::pack::build_defs_and_files(&root, &|_| String::new())?;
    let mut terms = xerj_hub::build_catalogue::sketch_terms(
        &defs,
        &files,
        &manifest,
        row["domain"].as_str().unwrap_or(""),
    );
    terms.sort();
    terms.dedup();
    fs::create_dir_all(out)?;
    fs::write(
        Path::new(out).join(format!("{slug}.terms")),
        terms.join("\n") + "\n",
    )?;
    let stats = format!("{slug} {} {} {}\n", files.len(), defs.len(), terms.len());
    fs::write(Path::new(out).join(format!("{slug}.stats")), &stats)?;
    print!("{stats}");
    Ok(())
}

/// Words a synthetic (registry-only) sketch is built from.
fn words(s: &str) -> Vec<String> {
    s.split(|c: char| !c.is_ascii_alphanumeric())
        .filter(|w| w.len() >= 3)
        .map(str::to_ascii_lowercase)
        .collect()
}

fn catalogue(a: &[String]) -> anyhow::Result<()> {
    if a.len() < 4 {
        anyhow::bail!("catalogue <registry> <terms_dir> <out.json> <seed_hex> [--synthetic-rest]");
    }
    let registry = PathBuf::from(&a[0]);
    let terms_dir = PathBuf::from(&a[1]);
    let synthetic = a.iter().any(|x| x == "--synthetic-rest");
    let mut inputs = Vec::new();
    let (mut real, mut synth) = (0, 0);
    for row in backlog_rows(&registry)? {
        let slug = row["slug"].as_str().unwrap_or_default().to_string();
        let manifest_path = registry.join(format!("{slug}.json"));
        if !manifest_path.is_file() {
            continue;
        }
        let terms_file = terms_dir.join(format!("{slug}.terms"));
        let terms: Vec<String> = if terms_file.is_file() {
            real += 1;
            fs::read_to_string(&terms_file)?
                .lines()
                .filter(|l| !l.is_empty())
                .map(str::to_string)
                .collect()
        } else if synthetic {
            synth += 1;
            let mut t = words(row["domain"].as_str().unwrap_or(""));
            t.extend(words(&slug));
            for topic in row["tags"]["topics"].as_array().into_iter().flatten() {
                t.extend(words(topic.as_str().unwrap_or("")));
            }
            t
        } else {
            continue;
        };
        inputs.push(CorpusBuildInput {
            manifest_path,
            domain: row["cat"].as_str().unwrap_or("").to_string(),
            refresh_cadence_days: 7,
            pack_bytes: 12_345_678,
            pack_url: format!(
                "https://github.com/xerj-org/xerj/releases/download/pack-{slug}-01234567/{slug}-01234567.hubpack.tar.zst"
            ),
            pack_sha256: "0".repeat(64),
            sig_url: format!(
                "https://github.com/xerj-org/xerj/releases/download/pack-{slug}-01234567/{slug}-01234567.hubpack.tar.zst.sig"
            ),
            quality_grade: None,
            terms,
            pin_sha: String::new(),
            ask_for: row["domain"].as_str().unwrap_or("").to_string(),
        });
    }
    let t = Instant::now();
    let (cat, sig) = build_catalogue(&inputs, "2026-10-17T00:00:00Z", &a[3])?;
    let bytes = canonical_json(&cat)?;
    let build_ms = t.elapsed().as_secs_f64() * 1e3;
    fs::write(&a[2], &bytes)?;
    fs::write(format!("{}.sig", a[2]), &sig)?;
    let sketch_b64: usize = cat
        .corpora
        .iter()
        .map(|e| e.term_sketch.bits_base64.len())
        .sum();
    println!(
        "corpora {} (real {real}, synthetic {synth}) bytes {} sketch_base64_bytes {sketch_b64} build_ms {build_ms:.0}",
        cat.corpora.len(),
        bytes.len()
    );
    Ok(())
}

struct Case {
    q: String,
    deps: Vec<String>,
    expected: Option<String>,
    group: String,
}

fn load_cases(path: &str) -> anyhow::Result<Vec<Case>> {
    let mut out = Vec::new();
    for line in fs::read_to_string(path)?.lines() {
        if line.trim().is_empty() {
            continue;
        }
        let v: Value = serde_json::from_str(line)?;
        out.push(Case {
            q: v["q"].as_str().unwrap_or("").to_string(),
            deps: v["deps"]
                .as_array()
                .into_iter()
                .flatten()
                .filter_map(|d| d.as_str().map(str::to_string))
                .collect(),
            expected: v["expected"].as_str().map(str::to_string),
            group: v["group"].as_str().unwrap_or("").to_string(),
        });
    }
    Ok(out)
}

fn project_dir(base: &Path, i: usize, deps: &[String]) -> anyhow::Result<PathBuf> {
    let dir = base.join(format!("p{i}"));
    fs::create_dir_all(dir.join(".git"))?;
    let lock = dir.join("Cargo.lock");
    if deps.is_empty() {
        let _ = fs::remove_file(&lock);
    } else {
        let mut s = String::from("version = 3\n");
        for d in deps {
            s.push_str(&format!(
                "\n[[package]]\nname = \"{d}\"\nversion = \"1.0.0\"\n"
            ));
        }
        fs::write(lock, s)?;
    }
    Ok(dir)
}

#[derive(Default)]
struct Tally {
    n: usize,
    top1: usize,
    confident: usize,
    confident_right: usize,
    ambiguous: usize,
    ambiguous_contains: usize,
    no_corpus: usize,
    no_corpus_right: usize,
    oob: usize,
    oob_no_corpus: usize,
}

fn route_cases(a: &[String]) -> anyhow::Result<()> {
    if a.len() < 2 {
        anyhow::bail!("route <catalogue.json> <cases.jsonl> [--verbose]");
    }
    let verbose = a.iter().any(|x| x == "--verbose");
    let t = Instant::now();
    let raw = fs::read(&a[0])?;
    let read_ms = t.elapsed().as_secs_f64() * 1e3;
    let t = Instant::now();
    let cat: Catalogue = serde_json::from_slice(&raw)?;
    let parse_ms = t.elapsed().as_secs_f64() * 1e3;
    println!(
        "catalogue {} corpora, {} bytes, read {read_ms:.1} ms, parse {parse_ms:.1} ms",
        cat.corpora.len(),
        raw.len()
    );
    let cases = load_cases(&a[1])?;
    let tmp = tempfile::tempdir()?;
    let mut lat: Vec<f64> = Vec::new();
    let mut tallies: BTreeMap<(String, bool), Tally> = BTreeMap::new();
    for (i, c) in cases.iter().enumerate() {
        for with_deps in [true, false] {
            if with_deps && c.deps.is_empty() {
                // Same as without; count it once under "without".
                continue;
            }
            let deps: &[String] = if with_deps { &c.deps } else { &[] };
            let dir = project_dir(tmp.path(), i, deps)?;
            let t = Instant::now();
            let (verdict, ranked) = route_ranked(&c.q, &dir, &cat, None, &[]);
            lat.push(t.elapsed().as_secs_f64() * 1e3);
            for key in [
                (String::from("ALL"), with_deps),
                (c.group.clone(), with_deps),
            ] {
                let tl = tallies.entry(key).or_default();
                score(tl, c, &verdict);
            }
            if verbose {
                let top: Vec<String> = ranked
                    .iter()
                    .take(4)
                    .map(|(s, v)| format!("{s}:{v:.2}"))
                    .collect();
                println!(
                    "{} deps={} exp={:?} -> {:?} | {}",
                    c.q,
                    with_deps,
                    c.expected,
                    short(&verdict),
                    top.join(" ")
                );
            }
        }
    }
    lat.sort_by(|x, y| x.partial_cmp(y).unwrap());
    let pct = |p: f64| lat[((lat.len() as f64 - 1.0) * p).round() as usize];
    println!(
        "route latency over {} calls: p50 {:.2} ms, p95 {:.2} ms, max {:.2} ms",
        lat.len(),
        pct(0.5),
        pct(0.95),
        lat[lat.len() - 1]
    );
    println!("group\tdeps\tn\ttop1\tconf\tconf_prec\tamb\tamb_contains\tnocorp\toob\toob_nocorp");
    for ((g, d), t) in &tallies {
        let r = |a: usize, b: usize| {
            if b == 0 {
                "-".to_string()
            } else {
                format!("{:.1}%", 100.0 * a as f64 / b as f64)
            }
        };
        let in_hub = t.n - t.oob;
        println!(
            "{g}\t{d}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}",
            t.n,
            r(t.top1, in_hub),
            t.confident,
            r(t.confident_right, t.confident),
            t.ambiguous,
            r(t.ambiguous_contains, t.ambiguous),
            t.no_corpus,
            t.oob,
            r(t.oob_no_corpus, t.oob),
        );
        let _ = t.no_corpus_right;
    }
    Ok(())
}

fn short(r: &Routing) -> String {
    match r {
        Routing::Confident(s) => format!("Confident({s})"),
        Routing::Ambiguous(v) => format!(
            "Ambiguous({})",
            v.iter().take(4).cloned().collect::<Vec<_>>().join(",")
        ),
        Routing::NoCorpus => "NoCorpus".into(),
    }
}

fn score(t: &mut Tally, c: &Case, v: &Routing) {
    t.n += 1;
    match (&c.expected, v) {
        (None, r) => {
            t.oob += 1;
            if *r == Routing::NoCorpus {
                t.oob_no_corpus += 1;
                t.no_corpus += 1;
                t.no_corpus_right += 1;
            } else if let Routing::Confident(_) = r {
                t.confident += 1;
            } else {
                t.ambiguous += 1;
            }
        }
        (Some(exp), Routing::Confident(s)) => {
            t.confident += 1;
            if s == exp {
                t.confident_right += 1;
                t.top1 += 1;
            }
        }
        (Some(exp), Routing::Ambiguous(v)) => {
            t.ambiguous += 1;
            if v.contains(exp) {
                t.ambiguous_contains += 1;
            }
            if v.first() == Some(exp) {
                t.top1 += 1;
            }
        }
        (Some(_), Routing::NoCorpus) => {
            t.no_corpus += 1;
        }
    }
}
