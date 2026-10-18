//! One permission sentence, on every surface an agent reads before it files.
//!
//! Help and the indexing footer are asserted through the functions that
//! print them. The installer banners, the homepage prompt, the agent docs
//! and the MCP `initialize` instructions are committed text, so this reads
//! those files. `xerj init`'s teaching strings are private; the unit test
//! `skill_shows_prefix_on_index_and_query` locks those, and this file locks
//! that the source still contains the sentence.

use std::path::PathBuf;

const PERMISSION_LINE: &str =
    "Show your user the report (`xerj feedback --dry-run`) and ask before sending.";

fn repo_file(rel: &str) -> String {
    let mut path = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    path.push("../../..");
    path.push(rel);
    std::fs::read_to_string(&path).unwrap_or_else(|e| panic!("read {}: {e}", path.display()))
}

#[test]
fn help_asks_before_sending() {
    let help = xerj_autoindex::feedback::help_text(true);
    assert!(
        help.contains(PERMISSION_LINE),
        "xerj feedback --help must carry the permission line near the top:\n{help}"
    );
    assert!(!help.contains("filed automatically"), "{help}");
    assert!(!help.contains("on behalf of a human"), "{help}");
    let top = help.lines().take(6).collect::<Vec<_>>().join("\n");
    assert!(
        top.contains(PERMISSION_LINE),
        "the permission line must be near the top of help, got:\n{top}"
    );

    let invite = xerj_common::feedback::block(true);
    assert!(invite.contains(PERMISSION_LINE));
    assert!(!invite.contains("filed automatically"));
}

#[test]
fn init_banner_homepage_and_mcp_name_the_field_report() {
    let init = repo_file("engine/crates/xerj-autoindex/src/init.rs");
    assert!(
        init.contains(PERMISSION_LINE),
        "the files xerj init writes must include the permission line"
    );
    assert!(
        init.contains("when to file a field report"),
        "xerj init --help must mention the field report"
    );

    for rel in [
        "landing/get",
        "landing/get.ps1",
        "landing/llms.txt",
        "landing/llms-full.txt",
    ] {
        let text = repo_file(rel);
        assert!(
            text.contains(PERMISSION_LINE),
            "{rel} is missing the permission line"
        );
        assert!(
            !text.contains("filed automatically"),
            "{rel} still says the report is filed automatically"
        );
    }

    // The MCP instructions are one string literal. A later unit test names
    // the old wording in an assertion, so this slices only the literal.
    let mcp = repo_file("engine/crates/xerj-mcp/src/lib.rs");
    let start = mcp
        .find("\"instructions\":")
        .expect("initialize instructions");
    let tail = &mcp[start..];
    let marker = "sending.\",";
    let end = tail
        .find(marker)
        .expect("the instructions literal ends with the permission line")
        + "sending.".len();
    let instructions = &tail[..end];
    assert!(
        instructions.contains(PERMISSION_LINE),
        "MCP initialize instructions must carry the permission line:\n{instructions}"
    );
    assert!(
        !instructions.contains("filed automatically"),
        "MCP instructions still say the report is filed automatically"
    );

    let html = repo_file("landing/index.html");
    let prompt = "Install XERJ (docs: https://xerj.org/llms.txt), index this project's sources, and set up reference coding: clone and index the open-source repos closest to what we're building, and search how they solved a problem before writing code. Show your user the report (`xerj feedback --dry-run`) and ask before sending.";
    let visible = format!("<code>{prompt}</code>");
    let copied = format!("data-copy=\"{prompt}\"");
    assert!(
        html.contains(&visible),
        "the homepage prompt a person reads must include the permission line"
    );
    assert!(
        html.contains(&copied),
        "the homepage copy button must carry the same prompt, including the permission line"
    );
}
