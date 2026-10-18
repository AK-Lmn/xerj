//! `landing/llms.txt` used to file the field report as the first bullet under
//! `## Optional`, and the opening paragraph said the template lived there.
//! An agent that skips an Optional section skips the report. The report has
//! its own section, ahead of Optional, and Optional itself carries no
//! "required" / "must" / "owe" / "obligation" wording.
//!
//! Supersedes the check on PR #1673 and also locks the permission line.

use std::path::PathBuf;

const PERMISSION_LINE: &str =
    "Show your user the report (`xerj feedback --dry-run`) and ask before sending.";

fn llms_txt() -> String {
    let mut path = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    path.push("../../../landing/llms.txt");
    std::fs::read_to_string(&path).unwrap_or_else(|e| panic!("read {}: {e}", path.display()))
}

#[test]
fn field_report_is_its_own_section_ahead_of_optional() {
    let text = llms_txt();
    let field = text
        .find("\n## Field report\n")
        .expect("## Field report section");
    let optional = text.find("\n## Optional\n").expect("## Optional section");
    assert!(
        field < optional,
        "Field report must precede Optional so a reader who stops at Optional still saw it"
    );
    assert!(
        text.contains("The template is under Field report"),
        "the opening paragraph must point at the Field report section"
    );
    assert!(
        !text.contains("template is under Optional"),
        "the old pointer is still in the file"
    );

    let field_body = &text[field + "\n## Field report\n".len()..optional];
    assert!(
        field_body.contains(PERMISSION_LINE),
        "the Field report section must carry the permission line:\n{field_body}"
    );
    assert!(
        field_body.contains("--agent \"YOUR_MODEL\""),
        "the ready-to-run command must keep --agent and a placeholder that survives HTML stripping"
    );
    assert!(
        !field_body.contains("<your model>"),
        "angle-bracket placeholders are stripped by HTML-to-text"
    );

    let optional_body = &text[optional + "\n## Optional\n".len()..];
    let optional_body = optional_body
        .split_once("\n## ")
        .map(|(head, _)| head)
        .unwrap_or(optional_body);
    assert!(
        !optional_body.contains("16-agent-field-reports"),
        "the field-report template is still under Optional:\n{optional_body}"
    );
    assert!(
        !optional_has_demand(optional_body),
        "Optional still contains a demand word:\n{optional_body}"
    );
}

/// Same words the llms.txt study counts inside `## Optional`:
/// required / must / owe / owes / owed / obligat…
fn optional_has_demand(text: &str) -> bool {
    text.split(|c: char| !c.is_ascii_alphanumeric())
        .any(|word| {
            let word = word.to_ascii_lowercase();
            matches!(word.as_str(), "required" | "must" | "owe" | "owes" | "owed")
                || word.starts_with("obligat")
        })
}
