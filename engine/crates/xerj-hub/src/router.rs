//! Corpus Hub v2 — the question router (`docs/CORPUS_HUB_V2_IMPLEMENTATION.md`,
//! step 5, "Router").
//!
//! Given a question, the working directory and the signed [`Catalogue`], decide
//! which corpus answers it — **before** anything is downloaded. Three kinds of
//! evidence are gathered, each on its own scale, then merged per slug:
//!
//! 1. **Project dependencies** (score `1.0`). The strongest signal: if the
//!    project the agent is standing in declares a dependency a corpus is built
//!    for, that corpus almost certainly holds the answer. Dependency names are
//!    read from the lockfiles found walking from `cwd` up to the git root
//!    ([`parse_project_deps`]).
//! 2. **Hosted federated search** (score `0.9 × hit/top`). When the hosted node
//!    is consulted, its ranked hits are normalised to the best one so a strong
//!    hosted match sits just under a dependency match. The node lives behind the
//!    [`HostedSearch`] trait so this module stays node-free and unit-testable.
//! 3. **Term sketch** (score `≤ 0.8`). Offline, from the catalogue alone: the
//!    idf-weighted share of the question's terms a corpus's Bloom
//!    [`sketch`](crate::sketch) reports present. Each term is weighted by its
//!    inverse document frequency over the catalogue (`ln((N + 1) / (df + 0.5))`),
//!    so a word most corpora hold says little and one few hold says a lot. The
//!    score is then scaled by the fraction of the question's terms *any* corpus
//!    holds, so a question full of out-of-hub words cannot reach a confident
//!    score on its one in-hub term.
//! 4. **The corpus the question names** (score `1.0`, [`named_slugs`]). The
//!    asker spelling a slug is the plainest signal of all.
//!
//! The merged scores decide: a dominant, high-scoring corpus is
//! [`Routing::Confident`]; a cluster of plausible ones is
//! [`Routing::Ambiguous`] (best-first, for the caller to disambiguate with
//! `--corpus`); nothing credible is [`Routing::NoCorpus`]. A corpus already
//! cached locally gets a small nudge so a tie breaks toward the pack the agent
//! already has.
//!
//! Why idf and not a fixed "common" cut: the first rule halved a term present in
//! more than 25% of the corpora. In a catalogue of four or fewer corpora a term
//! held by ONE corpus is already over 25%, so every match was halved and no
//! question could score above `0.4` — below the `0.6` confident bar
//! (`xerj "how does zstd pick the window level"` against the three published
//! packs returned "no hub corpus matches"). `benchmarks/hub-routing-scale/` has
//! the measurement.

use std::collections::{HashMap, HashSet};
use std::fs;
use std::path::Path;

use serde::Deserialize;
use xerj_common::hub::Catalogue;

use crate::sketch;

/// Where a piece of [`Evidence`] came from. Kept on the evidence so a caller (or
/// a test) can see *why* a corpus was proposed, even though [`Routing`] itself
/// only carries slugs.
#[derive(Debug, Clone, PartialEq)]
pub enum EvidenceSource {
    /// The project declares this dependency name (which a corpus answers for).
    ProjectDependency(String),
    /// The hosted node's federated search returned this corpus.
    Hosted,
    /// The corpus's term sketch matched some of the question's tokens.
    Sketch,
    /// The question names this corpus by its slug (`… in lz4?`, `snappy's …`).
    Named,
}

/// One corpus proposed for a question, with the score it earned on its source's
/// scale. Several pieces may name the same slug; [`route`] keeps the max.
#[derive(Debug, Clone)]
pub struct Evidence {
    pub slug: String,
    pub score: f32,
    pub source: EvidenceSource,
}

/// The routing verdict. `Ambiguous` holds the candidate slugs best-first.
#[derive(Debug, Clone, PartialEq)]
pub enum Routing {
    /// One corpus clearly wins; answer from it.
    Confident(String),
    /// Several corpora are plausible (best-first); the caller must pick one.
    Ambiguous(Vec<String>),
    /// Nothing credible matched.
    NoCorpus,
}

/// The hosted node's federated search, behind a trait so the router is
/// node-free. Returns `(slug, best_hit_score)` pairs, best first.
pub trait HostedSearch {
    fn search(&self, question: &str) -> anyhow::Result<Vec<(String, f32)>>;
}

/// Score a dependency match earns (the strongest evidence).
const DEP_SCORE: f32 = 1.0;
/// Hosted hits are scaled by this, relative to the top hosted hit.
const HOSTED_WEIGHT: f32 = 0.9;
/// Full idf-weighted coverage of the question earns this.
const SKETCH_WEIGHT: f32 = 0.8;
/// A cached corpus gets this added to its merged score.
const CACHED_BONUS: f32 = 0.05;
/// The top score must reach this to be `Confident`.
const CONFIDENT_MIN: f32 = 0.6;
/// `Confident` also needs the top to beat the runner-up by this factor.
const DOMINANCE: f32 = 1.5;
/// A slug must reach this to be an `Ambiguous` candidate.
const CANDIDATE_MIN: f32 = 0.3;
/// Score a corpus named in the question earns (it outranks everything: the
/// asker said which corpus they mean).
const NAMED_SCORE: f32 = 1.0;
/// Slugs shorter than this are never matched as a name (too likely to be a
/// stray word or abbreviation).
const NAMED_MIN_LEN: usize = 2;

/// Route a question to a corpus.
///
/// `hosted` is consulted only when `Some`; `cached` lists slugs whose packs are
/// already on disk (they get a small bonus). The working directory `cwd` is
/// searched for lockfiles up to the git root.
pub fn route(
    question: &str,
    cwd: &Path,
    cat: &Catalogue,
    hosted: Option<&dyn HostedSearch>,
    cached: &[String],
) -> Routing {
    route_ranked(question, cwd, cat, hosted, cached).0
}

/// [`route`], plus every corpus that earned any evidence at all as
/// `(slug, merged score)`, best first. The verdict is exactly [`route`]'s; the
/// ranking is what a caller prints when the verdict is [`Routing::NoCorpus`] — the
/// closest corpora, so the asker can name one with `--corpus` instead of being told
/// only that nothing matched.
pub fn route_ranked(
    question: &str,
    cwd: &Path,
    cat: &Catalogue,
    hosted: Option<&dyn HostedSearch>,
    cached: &[String],
) -> (Routing, Vec<(String, f32)>) {
    let mut evidence: Vec<Evidence> = Vec::new();

    // 1. Project dependencies — any corpus the project already depends on.
    let deps = parse_project_deps(cwd);
    if !deps.is_empty() {
        let dep_set: HashSet<&str> = deps.iter().map(String::as_str).collect();
        for entry in &cat.corpora {
            if let Some(hit) = entry
                .dependency_names
                .iter()
                .find(|name| dep_set.contains(name.as_str()))
            {
                evidence.push(Evidence {
                    slug: entry.slug.clone(),
                    score: DEP_SCORE,
                    source: EvidenceSource::ProjectDependency(hit.clone()),
                });
            }
        }
    }

    // 2. Hosted federated search, normalised to the top hit.
    if let Some(node) = hosted {
        if let Ok(results) = node.search(question) {
            let top = results
                .iter()
                .map(|(_, s)| *s)
                .fold(f32::NEG_INFINITY, f32::max);
            if top > 0.0 {
                for (slug, score) in results {
                    evidence.push(Evidence {
                        slug,
                        score: HOSTED_WEIGHT * (score / top),
                        source: EvidenceSource::Hosted,
                    });
                }
            }
        }
    }

    // 3. Term sketch — the question's terms against each corpus, idf-weighted.
    let Coverage { share, known } = coverage(question, cat);
    for (entry, &cov) in cat.corpora.iter().zip(&share) {
        if cov > 0.0 {
            evidence.push(Evidence {
                slug: entry.slug.clone(),
                score: SKETCH_WEIGHT * cov * known,
                source: EvidenceSource::Sketch,
            });
        }
    }

    // 4. The corpus the question names. Asking "what is X in lz4?" names the
    //    corpus outright; the sketch alone could not see that, because the
    //    question's other words (and the name itself — zstd's sources mention
    //    lz4) also hit the neighbouring corpora. One named corpus decides; several
    //    ("lz4 or zstd?") are the candidates, in the order the evidence ranks them.
    let named = named_slugs(question, cat);
    for slug in &named {
        evidence.push(Evidence {
            slug: slug.clone(),
            score: NAMED_SCORE,
            source: EvidenceSource::Named,
        });
    }

    let (routing, ranked) = decide(evidence, cached);
    match named.len() {
        0 => (routing, ranked),
        1 => (Routing::Confident(named[0].clone()), ranked),
        _ => {
            let in_order: Vec<String> = ranked
                .iter()
                .filter(|(slug, _)| named.contains(slug))
                .map(|(slug, _)| slug.clone())
                .collect();
            (Routing::Ambiguous(in_order), ranked)
        }
    }
}

/// The catalogue slugs `question` names as a whole word, case-insensitively,
/// in catalogue order. A word is a run of slug characters (`a-z`, `0-9`, `.`,
/// `_`, `-`) with sentence punctuation (`.`, `-`) trimmed from its ends, so
/// `in lz4?`, `LZ4.`, `snappy's` and `c-ares` all name their corpus while
/// `lz4frame` and `liblz4` do not.
pub fn named_slugs(question: &str, cat: &Catalogue) -> Vec<String> {
    let lower = question.to_ascii_lowercase();
    let words: HashSet<&str> = lower
        .split(|c: char| !(c.is_ascii_alphanumeric() || matches!(c, '.' | '_' | '-')))
        .map(|w| w.trim_matches(|c| c == '.' || c == '-'))
        .filter(|w| w.len() >= NAMED_MIN_LEN)
        .collect();
    let mut out: Vec<String> = Vec::new();
    for entry in &cat.corpora {
        if words.contains(entry.slug.as_str()) && !out.contains(&entry.slug) {
            out.push(entry.slug.clone());
        }
    }
    out
}

/// Merge evidence by slug (max score), apply the cached bonus, and reach a
/// verdict; the ranking it was reached from comes back with it.
fn decide(evidence: Vec<Evidence>, cached: &[String]) -> (Routing, Vec<(String, f32)>) {
    let mut best: HashMap<String, f32> = HashMap::new();
    for e in evidence {
        let score = e.score;
        best.entry(e.slug)
            .and_modify(|s| *s = s.max(score))
            .or_insert(score);
    }
    if best.is_empty() {
        return (Routing::NoCorpus, Vec::new());
    }
    for (slug, score) in best.iter_mut() {
        if cached.iter().any(|c| c == slug) {
            *score += CACHED_BONUS;
        }
    }

    // Best first; ties broken by slug so the order is deterministic.
    let mut ranked: Vec<(String, f32)> = best.into_iter().collect();
    ranked.sort_by(|a, b| {
        b.1.partial_cmp(&a.1)
            .unwrap_or(std::cmp::Ordering::Equal)
            .then_with(|| a.0.cmp(&b.0))
    });

    let top_score = ranked[0].1;
    let dominant = match ranked.get(1) {
        None => true,
        Some((_, second)) => top_score >= DOMINANCE * *second,
    };
    if top_score >= CONFIDENT_MIN && dominant {
        let slug = ranked[0].0.clone();
        return (Routing::Confident(slug), ranked);
    }

    let candidates: Vec<String> = ranked
        .iter()
        .filter(|(_, s)| *s >= CANDIDATE_MIN)
        .map(|(slug, _)| slug.clone())
        .collect();
    if candidates.len() >= 2 {
        return (Routing::Ambiguous(candidates), ranked);
    }

    (Routing::NoCorpus, ranked)
}

/// English function words and question scaffolding. They carry no routing
/// signal, and a word no corpus holds would otherwise weigh as much as the
/// rarest real term and drag every corpus's coverage down.
const STOP_WORDS: &[&str] = &[
    "about",
    "after",
    "all",
    "also",
    "and",
    "any",
    "are",
    "been",
    "before",
    "best",
    "between",
    "but",
    "can",
    "could",
    "current",
    "development",
    "did",
    "does",
    "doing",
    "done",
    "each",
    "exact",
    "explain",
    "explained",
    "for",
    "from",
    "get",
    "had",
    "has",
    "have",
    "here",
    "how",
    "into",
    "its",
    "let",
    "may",
    "more",
    "most",
    "much",
    "must",
    "need",
    "not",
    "off",
    "one",
    "only",
    "other",
    "our",
    "out",
    "over",
    "should",
    "show",
    "some",
    "source",
    "such",
    "than",
    "that",
    "the",
    "their",
    "them",
    "then",
    "there",
    "these",
    "they",
    "this",
    "those",
    "through",
    "under",
    "use",
    "used",
    "uses",
    "using",
    "value",
    "via",
    "want",
    "was",
    "way",
    "were",
    "what",
    "when",
    "where",
    "which",
    "while",
    "who",
    "why",
    "will",
    "with",
    "would",
    "you",
    "your",
];

/// One question term: the forms probed for it (raw, lower case, and the
/// lower-case singular of a word ending in `s`). The term is held by a corpus
/// when any form is.
struct Term {
    forms: Vec<String>,
}

/// Tokenize a question into terms: each identifier run (regex
/// `[A-Za-z_][A-Za-z0-9_]{2,}`), stop words dropped, deduplicated by lower
/// case. The original case lets a symbol like `LZ4_compress` match a sketch's
/// symbol term; the lower case lets prose match the sketch's lower-case
/// vocabulary; the singular lets `formats` match `format`.
fn question_terms(question: &str) -> Vec<Term> {
    let mut terms: Vec<Term> = Vec::new();
    let mut seen: HashSet<String> = HashSet::new();
    for raw in identifiers(question) {
        let lower = raw.to_ascii_lowercase();
        if STOP_WORDS.contains(&lower.as_str()) || !seen.insert(lower.clone()) {
            continue;
        }
        let mut forms = vec![raw.clone()];
        if lower != raw {
            forms.push(lower.clone());
        }
        if let Some(singular) = singular(&lower) {
            forms.push(singular.to_string());
        }
        terms.push(Term { forms });
    }
    terms
}

/// `formats` → `format`; not `class`/`ss`, not 3-letter words (`has`, `bus`).
fn singular(lower: &str) -> Option<&str> {
    (lower.len() > 3 && lower.ends_with('s') && !lower.ends_with("ss"))
        .then(|| &lower[..lower.len() - 1])
}

/// The identifier runs of `text` (regex `[A-Za-z_][A-Za-z0-9_]{2,}`), in order.
fn identifiers(text: &str) -> Vec<String> {
    let chars: Vec<char> = text.chars().collect();
    let mut out = Vec::new();
    let mut i = 0;
    while i < chars.len() {
        if !is_ident_char(chars[i]) {
            i += 1;
            continue;
        }
        let start = i;
        while i < chars.len() && is_ident_char(chars[i]) {
            i += 1;
        }
        let run = &chars[start..i];
        // The regex must start at a letter/underscore and span ≥3 chars.
        if let Some(p) = run.iter().position(|&c| is_ident_start(c)) {
            if run.len() - p >= 3 {
                out.push(run[p..].iter().collect());
            }
        }
    }
    out
}

fn is_ident_char(c: char) -> bool {
    c.is_ascii_alphanumeric() || c == '_'
}

fn is_ident_start(c: char) -> bool {
    c.is_ascii_alphabetic() || c == '_'
}

/// What the question's terms say about every corpus.
struct Coverage {
    /// Per corpus (catalogue order): the idf-weighted share of the question's
    /// known terms it holds, in `[0, 1]`.
    share: Vec<f32>,
    /// The fraction of the question's terms that at least one corpus holds.
    known: f32,
}

/// See the module docs for the weighting. Each corpus's sketch is decoded once
/// (not re-base64-decoded per probe) because every question term is probed
/// against every corpus, and a full catalogue has hundreds.
fn coverage(question: &str, cat: &Catalogue) -> Coverage {
    let terms = question_terms(question);
    let n = cat.corpora.len();
    if terms.is_empty() || n == 0 {
        return Coverage {
            share: vec![0.0; n],
            known: 0.0,
        };
    }

    // present[corpus][term]: does the corpus's sketch report the term? The
    // sketch holds the corpus's curated words (slug, ask_for, topics) as well as
    // its symbols and paths — the catalogue builder puts the curated words in
    // first, before the per-corpus cap — so a description word and a symbol are
    // both found here.
    let present: Vec<Vec<bool>> = cat
        .corpora
        .iter()
        .map(|entry| {
            let decoded = sketch::Decoded::new(&entry.term_sketch);
            terms
                .iter()
                .map(|t| {
                    decoded
                        .as_ref()
                        .is_some_and(|d| t.forms.iter().any(|f| d.contains(f)))
                })
                .collect()
        })
        .collect();

    // idf over the terms SOME corpus holds: a word no corpus holds cannot tell
    // corpora apart, and at max idf it would outweigh the corpus's own name (the
    // plain English of "what is the exact value of …" is in no sketch). Unknown
    // words instead dilute every score linearly, through `known`.
    let df: Vec<usize> = (0..terms.len())
        .map(|ti| present.iter().filter(|row| row[ti]).count())
        .collect();
    let idf: Vec<f32> = df
        .iter()
        .map(|&d| {
            if d == 0 {
                0.0
            } else {
                (((n + 1) as f32) / (d as f32 + 0.5)).ln().max(0.0)
            }
        })
        .collect();
    let known = df.iter().filter(|&&d| d > 0).count() as f32 / terms.len() as f32;
    let total: f32 = idf.iter().sum();
    if total <= 0.0 {
        return Coverage {
            share: vec![0.0; n],
            known,
        };
    }
    Coverage {
        share: present
            .iter()
            .map(|row| {
                row.iter()
                    .zip(&idf)
                    .map(|(&p, w)| if p { *w } else { 0.0 })
                    .sum::<f32>()
                    / total
            })
            .collect(),
        known,
    }
}

/// Dependency names declared by the project, read from the lockfiles in `cwd`
/// and every parent up to and including the directory that holds `.git`.
/// Deduplicated, first-seen order. Missing or unparseable files are skipped.
///
/// Parsed: `Cargo.lock` (`[[package]]` names), `package.json`
/// (`dependencies` + `devDependencies` keys), `go.mod` (`require` paths — both
/// the full module path and its last segment), `requirements.txt` and
/// `pyproject.toml` `[project].dependencies` (the name before any version
/// specifier or extras).
pub fn parse_project_deps(cwd: &Path) -> Vec<String> {
    let mut names: Vec<String> = Vec::new();
    let mut seen: HashSet<String> = HashSet::new();

    let mut dir = Some(cwd);
    while let Some(d) = dir {
        collect_dir(d, &mut names, &mut seen);
        if d.join(".git").exists() {
            break;
        }
        dir = d.parent();
    }
    names
}

fn collect_dir(dir: &Path, names: &mut Vec<String>, seen: &mut HashSet<String>) {
    if let Ok(text) = fs::read_to_string(dir.join("Cargo.lock")) {
        add_all(parse_cargo_lock(&text), names, seen);
    }
    if let Ok(text) = fs::read_to_string(dir.join("package.json")) {
        add_all(parse_package_json(&text), names, seen);
    }
    if let Ok(text) = fs::read_to_string(dir.join("go.mod")) {
        add_all(parse_go_mod(&text), names, seen);
    }
    if let Ok(text) = fs::read_to_string(dir.join("requirements.txt")) {
        add_all(parse_requirements(&text), names, seen);
    }
    if let Ok(text) = fs::read_to_string(dir.join("pyproject.toml")) {
        add_all(parse_pyproject(&text), names, seen);
    }
}

fn add_all(found: Vec<String>, names: &mut Vec<String>, seen: &mut HashSet<String>) {
    for name in found {
        if !name.is_empty() && seen.insert(name.clone()) {
            names.push(name);
        }
    }
}

fn parse_cargo_lock(text: &str) -> Vec<String> {
    #[derive(Deserialize)]
    struct Lock {
        #[serde(default)]
        package: Vec<Package>,
    }
    #[derive(Deserialize)]
    struct Package {
        #[serde(default)]
        name: String,
    }
    toml::from_str::<Lock>(text)
        .map(|lock| lock.package.into_iter().map(|p| p.name).collect())
        .unwrap_or_default()
}

fn parse_package_json(text: &str) -> Vec<String> {
    #[derive(Deserialize)]
    struct Pkg {
        #[serde(default)]
        dependencies: serde_json::Map<String, serde_json::Value>,
        #[serde(default, rename = "devDependencies")]
        dev_dependencies: serde_json::Map<String, serde_json::Value>,
    }
    match serde_json::from_str::<Pkg>(text) {
        Ok(pkg) => pkg
            .dependencies
            .keys()
            .chain(pkg.dev_dependencies.keys())
            .cloned()
            .collect(),
        Err(_) => Vec::new(),
    }
}

fn parse_go_mod(text: &str) -> Vec<String> {
    let mut out: Vec<String> = Vec::new();
    let mut in_block = false;
    for raw in text.lines() {
        let line = strip_line_comment(raw).trim();
        if line.is_empty() {
            continue;
        }
        if in_block {
            if line == ")" {
                in_block = false;
            } else if let Some(path) = line.split_whitespace().next() {
                push_module(&mut out, path);
            }
        } else if line.starts_with("require (") {
            in_block = true;
        } else if let Some(rest) = line.strip_prefix("require ") {
            if let Some(path) = rest.split_whitespace().next() {
                push_module(&mut out, path);
            }
        }
    }
    out
}

fn push_module(out: &mut Vec<String>, path: &str) {
    let path = path.trim_matches('"');
    if path.is_empty() {
        return;
    }
    out.push(path.to_string());
    if let Some(segment) = path.rsplit('/').next() {
        if segment != path {
            out.push(segment.to_string());
        }
    }
}

fn strip_line_comment(line: &str) -> &str {
    match line.find("//") {
        Some(idx) => &line[..idx],
        None => line,
    }
}

fn parse_requirements(text: &str) -> Vec<String> {
    let mut out: Vec<String> = Vec::new();
    for raw in text.lines() {
        let line = raw.trim();
        // Skip blanks, comments and option lines (`-r`, `--index-url`, …).
        if line.is_empty() || line.starts_with('#') || line.starts_with('-') {
            continue;
        }
        let name = leading_requirement_name(line);
        if !name.is_empty() {
            out.push(name);
        }
    }
    out
}

// KNOWN SCOPE GAP: only PEP 621 `[project].dependencies` is parsed. Poetry's
// `[tool.poetry.dependencies]` table (a map keyed by name, not a PEP 508 list)
// is NOT read, so a pure-Poetry project contributes no dependency hints to
// routing. Left unimplemented deliberately — PEP 621 is the cross-tool standard;
// Poetry support is a separate change, not part of this fix.
fn parse_pyproject(text: &str) -> Vec<String> {
    #[derive(Deserialize)]
    struct PyProject {
        project: Option<Project>,
    }
    #[derive(Deserialize)]
    struct Project {
        #[serde(default)]
        dependencies: Vec<String>,
    }
    let parsed = match toml::from_str::<PyProject>(text) {
        Ok(p) => p,
        Err(_) => return Vec::new(),
    };
    parsed
        .project
        .map(|p| {
            p.dependencies
                .iter()
                .map(|dep| leading_requirement_name(dep.trim()))
                .filter(|name| !name.is_empty())
                .collect()
        })
        .unwrap_or_default()
}

/// The distribution name at the start of a requirement string: the leading run
/// of name characters, which stops at the first version specifier (`==`, `>=`,
/// `<`, `~=`, `!=`), extras (`[`), environment marker (`;`) or whitespace.
fn leading_requirement_name(s: &str) -> String {
    s.chars()
        .take_while(|c| c.is_ascii_alphanumeric() || matches!(c, '.' | '_' | '-'))
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;
    use tempfile::{tempdir, TempDir};
    use xerj_common::hub::{Catalogue, CatalogueEntry, LicenceClass};

    // --- builders ---------------------------------------------------------

    fn entry(slug: &str, deps: &[&str], sketch_terms: &[&str]) -> CatalogueEntry {
        CatalogueEntry {
            slug: slug.to_string(),
            domain: "TEST".to_string(),
            topics: Vec::new(),
            ask_for: String::new(),
            pin_sha: "0".repeat(40),
            pin_date: "2026-01-01".to_string(),
            refresh_cadence_days: 7,
            licence_spdx: "Apache-2.0".to_string(),
            licence_class: LicenceClass::AdaptWithAttribution,
            pack_bytes: 0,
            pack_url: String::new(),
            pack_sha256: String::new(),
            sig_url: String::new(),
            dependency_names: deps.iter().map(|s| s.to_string()).collect(),
            quality_grade: None,
            term_sketch: sketch::build(sketch_terms.iter().map(|s| s.to_string())),
        }
    }

    fn catalogue(entries: Vec<CatalogueEntry>) -> Catalogue {
        Catalogue {
            format_version: 1,
            generated_at: "2026-01-01T00:00:00Z".to_string(),
            corpora: entries,
        }
    }

    /// A temp dir that is a git root with no lockfiles: `parse_project_deps`
    /// stops there and returns nothing.
    fn empty_project() -> TempDir {
        let dir = tempdir().unwrap();
        fs::create_dir(dir.path().join(".git")).unwrap();
        dir
    }

    // --- parse_project_deps ----------------------------------------------

    #[test]
    fn parse_project_deps_reads_all_five_kinds_and_dedupes() {
        let dir = tempdir().unwrap();
        let root = dir.path();
        fs::create_dir(root.join(".git")).unwrap();

        fs::write(
            root.join("Cargo.lock"),
            "version = 3\n\n[[package]]\nname = \"serde\"\nversion = \"1.0\"\n\n\
             [[package]]\nname = \"tokio\"\nversion = \"1.0\"\nsource = \"registry+x\"\n",
        )
        .unwrap();
        fs::write(
            root.join("package.json"),
            r#"{"name":"demo","dependencies":{"react":"^18.0.0"},"devDependencies":{"jest":"^29"}}"#,
        )
        .unwrap();
        fs::write(
            root.join("go.mod"),
            "module example.com/demo\n\ngo 1.21\n\n\
             require (\n\tgithub.com/pkg/errors v0.9.1\n\tgolang.org/x/sync v0.1.0 // indirect\n)\n\n\
             require github.com/spf13/cobra v1.8.0\n",
        )
        .unwrap();
        fs::write(
            root.join("requirements.txt"),
            "# a comment\nrequests==2.28.1\nnumpy>=1.20\nflask[async]\ndjango ; python_version < \"3.8\"\n-r other.txt\n",
        )
        .unwrap();
        fs::write(
            root.join("pyproject.toml"),
            "[project]\nname = \"demo\"\ndependencies = [\"httpx>=0.24\", \"click\"]\n",
        )
        .unwrap();

        let deps = parse_project_deps(root);
        for expected in [
            "serde",
            "tokio",
            "react",
            "jest",
            "github.com/pkg/errors",
            "errors", // go.mod last segment
            "golang.org/x/sync",
            "sync", // go.mod last segment
            "github.com/spf13/cobra",
            "cobra", // go.mod last segment
            "requests",
            "numpy",
            "flask",
            "django",
            "httpx",
            "click",
        ] {
            assert!(
                deps.contains(&expected.to_string()),
                "expected {expected:?} in {deps:?}"
            );
        }

        // No duplicates.
        let mut sorted = deps.clone();
        sorted.sort();
        let mut unique = sorted.clone();
        unique.dedup();
        assert_eq!(sorted, unique, "duplicate dependency names in {deps:?}");
    }

    #[test]
    fn parse_project_deps_finds_parent_lockfile_from_subdir() {
        let dir = tempdir().unwrap();
        let root = dir.path();
        fs::create_dir(root.join(".git")).unwrap();
        fs::write(
            root.join("Cargo.lock"),
            "[[package]]\nname = \"rootcrate\"\nversion = \"1.0\"\n",
        )
        .unwrap();

        let sub = root.join("crates").join("inner");
        fs::create_dir_all(&sub).unwrap();
        fs::write(sub.join("requirements.txt"), "subpkg==1.0\n").unwrap();

        let deps = parse_project_deps(&sub);
        assert!(deps.contains(&"subpkg".to_string()), "{deps:?}");
        assert!(
            deps.contains(&"rootcrate".to_string()),
            "parent Cargo.lock not found walking up: {deps:?}"
        );
    }

    #[test]
    fn parse_project_deps_empty_when_no_lockfiles() {
        let proj = empty_project();
        assert!(parse_project_deps(proj.path()).is_empty());
    }

    // --- route ------------------------------------------------------------

    #[test]
    fn strong_sketch_hit_is_confident() {
        let cat = catalogue(vec![
            entry(
                "alpha",
                &[],
                &["frobnicate", "wizzle", "kelvin", "sprocket"],
            ),
            entry("beta", &[], &["banana", "orange", "grape", "melon"]),
            entry("gamma", &[], &["server", "socket", "packet", "router"]),
            entry("delta", &[], &["ledger", "balance", "invoice", "levy"]),
        ]);
        let proj = empty_project();
        let routing = route("frobnicate wizzle sprocket", proj.path(), &cat, None, &[]);
        assert_eq!(routing, Routing::Confident("alpha".to_string()));
    }

    #[test]
    fn project_dependency_forces_confident_even_with_weak_sketch() {
        let cat = catalogue(vec![
            entry("alpha", &["widgetlib"], &["frobnicate", "wizzle", "kelvin"]),
            entry("beta", &[], &["banana", "orange", "grape"]),
            entry("gamma", &[], &["server", "socket", "packet"]),
            entry("delta", &[], &["ledger", "balance", "invoice"]),
        ]);

        // Question touches alpha's sketch only weakly (one of two tokens) and no
        // other corpus — on its own that is NoCorpus.
        let question = "frobnicate glorptxngq";
        let without = route(question, empty_project().path(), &cat, None, &[]);
        assert_eq!(without, Routing::NoCorpus);

        // With the project depending on widgetlib, alpha is a certainty.
        let proj = empty_project();
        fs::write(
            proj.path().join("Cargo.lock"),
            "[[package]]\nname = \"widgetlib\"\nversion = \"1.0\"\n",
        )
        .unwrap();
        let with = route(question, proj.path(), &cat, None, &[]);
        assert_eq!(with, Routing::Confident("alpha".to_string()));
    }

    #[test]
    fn vague_question_matching_two_corpora_is_ambiguous() {
        let cat = catalogue(vec![
            entry("alpha", &[], &["aaa", "bbb", "ccc", "ddd"]),
            entry("beta", &[], &["aaa", "bbb", "eee", "fff"]),
            entry("gamma", &[], &["server", "socket", "packet", "router"]),
            entry("delta", &[], &["ledger", "balance", "invoice", "levy"]),
        ]);
        let proj = empty_project();
        let routing = route("aaa bbb", proj.path(), &cat, None, &[]);
        match routing {
            Routing::Ambiguous(slugs) => {
                assert!(
                    slugs.contains(&"alpha".to_string()) && slugs.contains(&"beta".to_string()),
                    "both candidates expected, got {slugs:?}"
                );
            }
            other => panic!("expected Ambiguous, got {other:?}"),
        }
    }

    #[test]
    fn nonsense_question_is_no_corpus() {
        let cat = catalogue(vec![
            entry("alpha", &[], &["aaa", "bbb"]),
            entry("beta", &[], &["ccc", "ddd"]),
            entry("gamma", &[], &["eee", "fff"]),
            entry("delta", &[], &["ggg", "hhh"]),
        ]);
        let proj = empty_project();
        let routing = route("zxqwptl vmkrbng unmatchable", proj.path(), &cat, None, &[]);
        assert_eq!(routing, Routing::NoCorpus);
    }

    #[test]
    fn hosted_search_boosts_into_confident() {
        struct Stub;
        impl HostedSearch for Stub {
            fn search(&self, _q: &str) -> anyhow::Result<Vec<(String, f32)>> {
                Ok(vec![("beta".to_string(), 12.0), ("gamma".to_string(), 3.0)])
            }
        }

        let cat = catalogue(vec![
            entry("alpha", &[], &["aaa", "bbb"]),
            entry("beta", &[], &["ccc", "ddd"]),
            entry("gamma", &[], &["eee", "fff"]),
            entry("delta", &[], &["ggg", "hhh"]),
        ]);
        let proj = empty_project();
        let question = "unrelated prose touching nothing";

        // Without the hosted node there is no evidence at all.
        assert_eq!(
            route(question, proj.path(), &cat, None, &[]),
            Routing::NoCorpus
        );

        // The hosted node's top hit (normalised to 0.9) wins outright.
        let stub = Stub;
        assert_eq!(
            route(question, proj.path(), &cat, Some(&stub), &[]),
            Routing::Confident("beta".to_string())
        );
    }

    #[test]
    fn cached_bonus_flips_a_borderline_match() {
        // alpha owns five distinct terms; the question has them plus two noise
        // tokens, so alpha scores 5/7 * 0.8 = 0.571 — under the 0.6 bar and
        // alone, hence NoCorpus. The +0.05 cached bonus lifts it over.
        let cat = catalogue(vec![
            entry("alpha", &[], &["aaa", "bbb", "ccc", "ddd", "eee"]),
            entry("beta", &[], &["ppp1", "ppp2", "ppp3", "ppp4", "ppp5"]),
            entry("gamma", &[], &["qqq1", "qqq2", "qqq3", "qqq4", "qqq5"]),
            entry("delta", &[], &["rrr1", "rrr2", "rrr3", "rrr4", "rrr5"]),
        ]);
        let proj = empty_project();
        let question = "aaa bbb ccc ddd eee noisetokenone noisetokentwo";

        assert_eq!(
            route(question, proj.path(), &cat, None, &[]),
            Routing::NoCorpus
        );
        assert_eq!(
            route(question, proj.path(), &cat, None, &["alpha".to_string()]),
            Routing::Confident("alpha".to_string())
        );
    }

    // --- tokenizer --------------------------------------------------------

    #[test]
    fn named_slugs_match_whole_words_only() {
        let cat = catalogue(vec![
            entry("lz4", &[], &[]),
            entry("c-ares", &[], &[]),
            entry("snappy", &[], &[]),
            entry("h2", &[], &[]),
        ]);
        let names = |q: &str| named_slugs(q, &cat);
        assert_eq!(names("What is LZ4_VERSION_RELEASE in lz4?"), ["lz4"]);
        assert_eq!(names("Does LZ4. handle it"), ["lz4"]);
        assert_eq!(names("how does snappy's decoder work"), ["snappy"]);
        assert_eq!(names("c-ares resolver timeouts"), ["c-ares"]);
        assert_eq!(names("lz4 vs snappy"), ["lz4", "snappy"]);
        // Part of a longer word or identifier is not the name.
        assert!(names("liblz4 and lz4frame and LZ4_compress").is_empty());
        assert!(names("snappyish ares").is_empty());
    }

    #[test]
    fn a_named_corpus_decides_even_against_a_dependency() {
        let cat = catalogue(vec![
            entry("alpha", &["widgetlib"], &["frobnicate", "wizzle"]),
            entry("beta", &[], &["frobnicate", "wizzle"]),
            entry("gamma", &[], &["server"]),
        ]);
        let proj = empty_project();
        fs::write(
            proj.path().join("Cargo.lock"),
            "[[package]]\nname = \"widgetlib\"\nversion = \"1.0\"\n",
        )
        .unwrap();
        let (routing, ranked) =
            route_ranked("how does beta frobnicate", proj.path(), &cat, None, &[]);
        assert_eq!(routing, Routing::Confident("beta".to_string()));
        assert!(ranked.iter().any(|(s, _)| s == "beta"), "{ranked:?}");
        // Two named: ambiguous between exactly those two.
        let both = route("alpha or beta?", empty_project().path(), &cat, None, &[]);
        match both {
            Routing::Ambiguous(mut slugs) => {
                slugs.sort();
                assert_eq!(slugs, ["alpha", "beta"]);
            }
            other => panic!("expected Ambiguous, got {other:?}"),
        }
    }

    #[test]
    fn question_terms_drop_stop_words_and_probe_case_and_singular() {
        let terms = question_terms("How does LZ4_compress handle a 64 byte block formats");
        let firsts: Vec<&str> = terms.iter().map(|t| t.forms[0].as_str()).collect();
        // "How"/"does" are stop words; "a"/"64" are not identifiers.
        assert_eq!(
            firsts,
            ["LZ4_compress", "handle", "byte", "block", "formats"]
        );
        // A mixed-case symbol is probed raw and lower-cased.
        assert_eq!(terms[0].forms, ["LZ4_compress", "lz4_compress"]);
        // A plural is probed as itself and its singular.
        assert_eq!(terms[4].forms, ["formats", "format"]);
        // A lower-case word that is neither plural nor mixed case: one form.
        assert_eq!(terms[1].forms, ["handle"]);
    }
}
