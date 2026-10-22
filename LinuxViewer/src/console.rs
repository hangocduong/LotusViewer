//! Terminal side of `linuxviewer connect`: stdin lines become chat, `/send
//! <path>` offers a file, `/accept <id>` saves an offered file, transfers and
//! chat are reported on stdout/stderr, and `--clipboard` keeps the local text
//! clipboard in sync (arboard). With `--ipc`, stdout carries crate::ipc lines
//! and stdin takes the host-style commands instead. OWNER: net.

use crate::chat::ChatEvent;
use crate::client::{ClientEvent, SessionHandle};
use crate::files;
use crate::ipc::{self, Line};
use std::collections::HashMap;
use std::io::BufRead;
use std::path::Path;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::mpsc::{self, RecvTimeoutError, Sender};
use std::sync::{Arc, Mutex};
use std::thread;
use std::time::Duration;

pub const HELP: &str = "Type a line to chat. /send <path> sends a file, /accept <id> saves an offered file, \
                        /cancel <id> refuses or cancels a transfer, /quit disconnects.";

const IPC_HELP: &str = "Commands: t TEXT = chat, f PATH = send a file, a / r ID = accept / refuse a file, x = disconnect.";

/// Wraps `notify` with the console side effects. `chat_on_stdout` prints
/// partner chat (the window front end shows it itself when false). `ipc` is
/// the partner ID in ipc mode.
pub fn wrap(handle: SessionHandle, stdin: bool, clipboard: bool, chat_on_stdout: bool, ipc: Option<&str>,
            notify: Box<dyn Fn(ClientEvent) + Send>) -> Box<dyn Fn(ClientEvent) + Send> {
    let started = AtomicBool::new(false);
    let names: Arc<Mutex<HashMap<String, String>>> = Arc::default();
    let clip: Mutex<Option<Sender<String>>> = Mutex::new(None);
    let partner = ipc.map(str::to_string);
    if stdin && partner.is_some() {
        // Read from the start: the front end may go away before the session does.
        spawn_ipc_stdin(handle.clone());
    }
    Box::new(move |event| {
        let first_init = matches!(event, ClientEvent::Connected { .. }) && !started.swap(true, Ordering::SeqCst);
        if let Some(id) = &partner {
            emit_ipc(&event, id, first_init);
        }
        if first_init {
            if stdin && partner.is_none() {
                eprintln!("{HELP}");
                spawn_stdin(handle.clone(), names.clone());
            }
            if clipboard {
                *clip.lock().unwrap() = spawn_clipboard(handle.clone());
                handle.set_clipboard_sharing(true);
            }
        }
        match &event {
            ClientEvent::Chat(ChatEvent::Message(text)) if chat_on_stdout && partner.is_none() => println!("Partner: {text}"),
            ClientEvent::Clipboard(text) => {
                if let Some(tx) = clip.lock().unwrap().as_ref() {
                    let _ = tx.send(text.clone());
                }
            }
            ClientEvent::File(e) if partner.is_none() => report_file(e, &names),
            _ => {}
        }
        notify(event)
    })
}

fn emit_ipc(event: &ClientEvent, partner_id: &str, first_init: bool) {
    let line = match event {
        ClientEvent::Status(s) => Line::Status(s.clone()),
        ClientEvent::Connected { .. } if first_init => Line::Connected(partner_id.into()),
        ClientEvent::ViewOnly(v) => Line::Control(!v),
        ClientEvent::Chat(ChatEvent::Message(text)) => Line::Chat(text.clone()),
        ClientEvent::File(files::Event::Offer(o)) => Line::File { id: o.transfer_id.clone(), size: o.size, name: o.file_name.clone() },
        ClientEvent::File(files::Event::Completed(id)) => Line::FileDone(id.clone()),
        ClientEvent::File(files::Event::Canceled(id)) => Line::FileFail { id: id.clone(), reason: "Canceled".into() },
        ClientEvent::File(files::Event::Failed(id, reason)) => Line::FileFail { id: id.clone(), reason: reason.clone() },
        ClientEvent::Closed(reason) => Line::Ended(reason.clone()),
        _ => return,
    };
    ipc::emit(&line);
}

/// ipc stdin: one command per line; when stdin closes the session ends.
fn spawn_ipc_stdin(handle: SessionHandle) {
    thread::spawn(move || {
        for line in std::io::stdin().lock().lines() {
            let Ok(line) = line else { break };
            if handle.is_closed() {
                return;
            }
            if let Err(e) = ipc_command(&handle, line.trim()) {
                eprintln!("linuxviewer: {e}");
            }
        }
        handle.close();
    });
}

fn ipc_command(handle: &SessionHandle, line: &str) -> crate::wire::Result<()> {
    let (cmd, arg) = line.split_once(' ').map(|(c, a)| (c, a.trim())).unwrap_or((line, ""));
    match (cmd, arg) {
        ("", _) => Ok(()),
        ("x", "") => {
            handle.close();
            Ok(())
        }
        ("t", text) if !text.is_empty() => handle.send_chat(text),
        ("f", path) if !path.is_empty() => handle.send_file(Path::new(path))
            .map(|o| eprintln!("Offered {} ({} bytes)", o.file_name, o.size)),
        ("a", id) if !id.is_empty() => handle.accept_offer(id).map(|dest| eprintln!("Receiving → {}", dest.display())),
        ("r", id) if !id.is_empty() => handle.cancel_file(id),
        _ => Err(IPC_HELP.into()),
    }
}

fn report_file(e: &files::Event, names: &Mutex<HashMap<String, String>>) {
    let mut names = names.lock().unwrap();
    let name = |id: &str| names.get(id).cloned().unwrap_or_else(|| id.to_string());
    match e {
        files::Event::Offer(o) => {
            eprintln!("Partner offers {} ({} bytes). Type /accept {id} to save it or /cancel {id} to refuse.",
                      o.file_name, o.size, id = o.transfer_id);
            names.insert(o.transfer_id.clone(), o.file_name.clone());
        }
        files::Event::Progress(..) => {}
        files::Event::Completed(id) => eprintln!("Transfer complete: {}", name(id)),
        files::Event::Canceled(id) => eprintln!("Transfer canceled: {}", name(id)),
        files::Event::Failed(id, why) => eprintln!("Transfer failed: {}: {why}", name(id)),
    }
}

fn spawn_stdin(handle: SessionHandle, names: Arc<Mutex<HashMap<String, String>>>) {
    thread::spawn(move || {
        for line in std::io::stdin().lock().lines() {
            let Ok(line) = line else { break };
            if handle.is_closed() {
                break;
            }
            let line = line.trim_end_matches(['\r', '\n']);
            let result = if let Some(path) = line.strip_prefix("/send ") {
                handle.send_file(Path::new(path.trim())).map(|o| {
                    eprintln!("Offered {} ({} bytes)", o.file_name, o.size);
                    names.lock().unwrap().insert(o.transfer_id, o.file_name);
                })
            } else if let Some(id) = line.strip_prefix("/accept ") {
                handle.accept_offer(id.trim()).map(|dest| eprintln!("Receiving → {}", dest.display()))
            } else if let Some(id) = line.strip_prefix("/cancel ") {
                handle.cancel_file(id.trim())
            } else if line == "/quit" {
                handle.close();
                break;
            } else if line == "/help" {
                eprintln!("{HELP}");
                Ok(())
            } else if line.is_empty() {
                Ok(())
            } else {
                handle.send_chat(line)
            };
            if let Err(e) = result {
                eprintln!("linuxviewer: {e}");
            }
        }
    });
}

/// Polls the local clipboard once a second and sends changes; applies partner
/// text sent on the returned channel. Echoes are suppressed both ways.
fn spawn_clipboard(handle: SessionHandle) -> Option<Sender<String>> {
    let (tx, rx) = mpsc::channel::<String>();
    let ready = Arc::new(AtomicBool::new(false));
    let ok = ready.clone();
    let (started_tx, started_rx) = mpsc::channel();
    thread::spawn(move || {
        let mut cb = match arboard::Clipboard::new() {
            Ok(c) => c,
            Err(e) => {
                eprintln!("linuxviewer: clipboard sharing is unavailable: {e}");
                let _ = started_tx.send(());
                return;
            }
        };
        ok.store(true, Ordering::SeqCst);
        let _ = started_tx.send(());
        let mut last = cb.get_text().unwrap_or_default();
        loop {
            match rx.recv_timeout(Duration::from_secs(1)) {
                Ok(remote) => {
                    last = remote.clone();
                    if let Err(e) = cb.set_text(remote) {
                        eprintln!("linuxviewer: could not set the clipboard: {e}");
                    }
                }
                Err(RecvTimeoutError::Disconnected) => return,
                Err(RecvTimeoutError::Timeout) => {
                    if handle.is_closed() {
                        return;
                    }
                    if let Ok(text) = cb.get_text() {
                        if text != last {
                            last = text.clone();
                            if let Err(e) = handle.send_clipboard(&text) {
                                eprintln!("linuxviewer: clipboard not sent: {e}");
                            }
                        }
                    }
                }
            }
        }
    });
    let _ = started_rx.recv_timeout(Duration::from_secs(5));
    ready.load(Ordering::SeqCst).then_some(tx)
}
