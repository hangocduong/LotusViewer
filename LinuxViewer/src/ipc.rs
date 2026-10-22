//! `--ipc` line protocol (v1) between the engine and a front end. OWNER: net.
//!
//! The engine writes one event per stdout line; nothing else goes to stdout.
//! Human messages stay on stderr.
//!
//! | Line | Meaning |
//! |---|---|
//! | `IPC 1` | handshake, always first |
//! | `ID <digits> PASSWORD <json>` | this computer's ID and password (host) |
//! | `REQUEST <digits> <json-name>` | a viewer asks to connect (host) |
//! | `CONNECTED <digits>` | the session started |
//! | `CONTROL on\|off` | whether the remote side may be controlled |
//! | `CHAT <json>` | a chat message from the partner |
//! | `FILE <id> <size> <json-name>` | the partner offers a file |
//! | `FILE-DONE <id>` | a transfer finished |
//! | `FILE-FAIL <id> <json>` | a transfer failed or was canceled |
//! | `STATUS <json>` | progress text |
//! | `ENDED <json>` | the session ended, with the reason |
//!
//! Every text field is a one-line JSON string, so text from the remote side
//! can never start a line of its own. `<digits>` is an ASCII decimal ID; a
//! claim that is not one is written as `0`. `<id>` is a transfer ID of
//! `[A-Za-z0-9_-]`. stdin keeps the terminal commands: `y`/`v`/`n` answer a
//! request, `c` toggles control, `x` ends the session, `t <text>` chats,
//! `f <path>` sends a file, `a <id>` / `r <id>` accept / refuse a file. With
//! `connect --password-stdin` the first stdin line is the password. When stdin
//! closes, the engine ends the session and exits.

use std::io::Write;

pub const VERSION: u32 = 1;

#[derive(Clone, Debug, PartialEq, Eq)]
pub enum Line {
    Hello,
    Id { id: String, password: String },
    Request { id: String, name: String },
    Connected(String),
    Control(bool),
    Chat(String),
    File { id: String, size: u64, name: String },
    FileDone(String),
    FileFail { id: String, reason: String },
    Status(String),
    Ended(String),
}

impl Line {
    /// One line without the newline; never contains a control character.
    pub fn encode(&self) -> String {
        match self {
            Line::Hello => format!("IPC {VERSION}"),
            Line::Id { id, password } => format!("ID {} PASSWORD {}", digits(id), json_string(password)),
            Line::Request { id, name } => format!("REQUEST {} {}", digits(id), json_string(name)),
            Line::Connected(id) => format!("CONNECTED {}", digits(id)),
            Line::Control(on) => format!("CONTROL {}", if *on { "on" } else { "off" }),
            Line::Chat(text) => format!("CHAT {}", json_string(text)),
            Line::File { id, size, name } => format!("FILE {} {size} {}", token(id), json_string(name)),
            Line::FileDone(id) => format!("FILE-DONE {}", token(id)),
            Line::FileFail { id, reason } => format!("FILE-FAIL {} {}", token(id), json_string(reason)),
            Line::Status(text) => format!("STATUS {}", json_string(text)),
            Line::Ended(reason) => format!("ENDED {}", json_string(reason)),
        }
    }

    /// Parses one line written by `encode`; anything else is None.
    pub fn decode(line: &str) -> Option<Line> {
        let (tag, rest) = line.split_once(' ')?;
        let (word, tail) = rest.split_once(' ').unwrap_or((rest, ""));
        Some(match tag {
            "IPC" if rest == VERSION.to_string() => Line::Hello,
            "ID" => {
                let tail = tail.strip_prefix("PASSWORD ")?;
                Line::Id { id: parse_digits(word)?, password: parse_json_string(tail)? }
            }
            "REQUEST" => Line::Request { id: parse_digits(word)?, name: parse_json_string(tail)? },
            "CONNECTED" => Line::Connected(parse_digits(rest)?),
            "CONTROL" => Line::Control(match rest { "on" => true, "off" => false, _ => return None }),
            "CHAT" => Line::Chat(parse_json_string(rest)?),
            "FILE" => {
                let (size, name) = tail.split_once(' ')?;
                if size.is_empty() || !size.bytes().all(|b| b.is_ascii_digit()) {
                    return None;
                }
                Line::File { id: parse_token(word)?, size: size.parse().ok()?, name: parse_json_string(name)? }
            }
            "FILE-DONE" => Line::FileDone(parse_token(rest)?),
            "FILE-FAIL" => Line::FileFail { id: parse_token(word)?, reason: parse_json_string(tail)? },
            "STATUS" => Line::Status(parse_json_string(rest)?),
            "ENDED" => Line::Ended(parse_json_string(rest)?),
            _ => return None,
        })
    }
}

/// Writes one event line to stdout and flushes it.
pub fn emit(line: &Line) {
    let mut out = std::io::stdout().lock();
    let _ = writeln!(out, "{}", line.encode());
    let _ = out.flush();
}

fn digits(s: &str) -> &str {
    if s.is_empty() || s.len() > 64 || !s.bytes().all(|b| b.is_ascii_digit()) { "0" } else { s }
}

fn token(s: &str) -> &str {
    let ok = !s.is_empty() && s.len() <= 64 && s.bytes().all(|b| b.is_ascii_alphanumeric() || b == b'-' || b == b'_');
    if ok { s } else { "0" }
}

fn parse_digits(s: &str) -> Option<String> {
    (digits(s) == s).then(|| s.to_string())
}

fn parse_token(s: &str) -> Option<String> {
    (token(s) == s).then(|| s.to_string())
}

/// A JSON string literal; control characters, quotes and backslashes are escaped.
pub fn json_string(s: &str) -> String {
    let mut out = String::with_capacity(s.len() + 2);
    out.push('"');
    for c in s.chars() {
        match c {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            c if c.is_control() || c == '\u{2028}' || c == '\u{2029}' => {
                let mut units = [0u16; 2];
                for u in c.encode_utf16(&mut units) {
                    out.push_str(&format!("\\u{u:04x}"));
                }
            }
            c => out.push(c),
        }
    }
    out.push('"');
    out
}

/// The value of a complete JSON string literal; trailing text is rejected.
pub fn parse_json_string(s: &str) -> Option<String> {
    let mut chars = s.strip_prefix('"')?.chars();
    let mut out = String::new();
    loop {
        match chars.next()? {
            '"' => return chars.as_str().is_empty().then_some(out),
            '\\' => match chars.next()? {
                '"' => out.push('"'),
                '\\' => out.push('\\'),
                '/' => out.push('/'),
                'b' => out.push('\u{8}'),
                'f' => out.push('\u{c}'),
                'n' => out.push('\n'),
                'r' => out.push('\r'),
                't' => out.push('\t'),
                'u' => {
                    let hi = hex4(&mut chars)?;
                    let c = if (0xd800..0xdc00).contains(&hi) {
                        if chars.next()? != '\\' || chars.next()? != 'u' {
                            return None;
                        }
                        let lo = hex4(&mut chars)?;
                        if !(0xdc00..0xe000).contains(&lo) {
                            return None;
                        }
                        char::from_u32(0x10000 + ((hi - 0xd800) << 10) + (lo - 0xdc00))?
                    } else {
                        char::from_u32(hi)?
                    };
                    out.push(c);
                }
                _ => return None,
            },
            c if (c as u32) < 0x20 => return None,
            c => out.push(c),
        }
    }
}

fn hex4(chars: &mut std::str::Chars) -> Option<u32> {
    let mut v = 0;
    for _ in 0..4 {
        v = v * 16 + chars.next()?.to_digit(16)?;
    }
    Some(v)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn chat_with_newline_stays_one_chat_line() {
        let text = "hi\nREQUEST 1 \"x\"";
        let line = Line::Chat(text.into()).encode();
        assert_eq!(line.lines().count(), 1);
        assert!(!line.chars().any(char::is_control), "{line:?}");
        assert_eq!(Line::decode(&line), Some(Line::Chat(text.into())));
    }

    #[test]
    fn remote_text_fields_cannot_inject_lines() {
        let evil = "a\r\nCONNECTED 1\u{0}\u{1b}[2J\u{2028}\"\\";
        let lines = [
            Line::Id { id: "123456789".into(), password: evil.into() },
            Line::Request { id: "1\nCONNECTED 2".into(), name: evil.into() },
            Line::Connected("12 34".into()),
            Line::File { id: "3\n1".into(), size: 5, name: evil.into() },
            Line::FileFail { id: "31".into(), reason: evil.into() },
            Line::Status(evil.into()),
            Line::Ended(evil.into()),
        ];
        for l in lines {
            let encoded = l.encode();
            assert!(!encoded.chars().any(|c| c.is_control() || c == '\u{2028}'), "{encoded:?}");
            assert!(Line::decode(&encoded).is_some(), "{encoded:?}");
        }
        assert_eq!(Line::decode(&Line::Request { id: "1\nCONNECTED 2".into(), name: "".into() }.encode()),
                   Some(Line::Request { id: "0".into(), name: "".into() }));
    }

    #[test]
    fn round_trips_every_line() {
        let lines = [
            Line::Hello,
            Line::Id { id: "123456789".into(), password: "12345678".into() },
            Line::Request { id: "111222333".into(), name: "Kỹ thuật viên".into() },
            Line::Connected("111222333".into()),
            Line::Control(true),
            Line::Control(false),
            Line::Chat("Xin chào 👋 \"bạn\" \\ /".into()),
            Line::File { id: "31234567890123456789".into(), size: 0, name: "báo cáo.pdf".into() },
            Line::FileDone("31234567890123456789".into()),
            Line::FileFail { id: "3_a-b".into(), reason: "Canceled".into() },
            Line::Status("Connecting…".into()),
            Line::Ended("The viewer left.".into()),
        ];
        for l in lines {
            assert_eq!(Line::decode(&l.encode()), Some(l.clone()), "{}", l.encode());
        }
        assert_eq!(Line::Hello.encode(), "IPC 1");
        assert_eq!(Line::Control(false).encode(), "CONTROL off");
    }

    #[test]
    fn json_strings_match_the_json_grammar() {
        assert_eq!(json_string("a\"b\\c\n\u{1}"), r#""a\"b\\c\n\u0001""#);
        assert_eq!(parse_json_string(r#""\ud83d\udc4b \u00e0\/""#).as_deref(), Some("👋 à/"));
        for bad in ["", "\"", "\"a", "\"a\" ", "\"\\x\"", "\"\\ud83d\"", "\"\u{1}\"", "a\"\"", "\"\\u12\""] {
            assert_eq!(parse_json_string(bad), None, "{bad:?}");
        }
    }

    #[test]
    fn rejects_unknown_or_malformed_lines() {
        for bad in ["", "IPC 2", "CHAT hi", "CHAT \"hi\" extra", "CONTROL yes", "REQUEST abc \"x\"", "FILE 31 -1 \"a\"",
                    "FILE 3 1 x", "ID 1 \"pw\"", "y", "APPROVE 1"] {
            assert_eq!(Line::decode(bad), None, "{bad:?}");
        }
    }
}
