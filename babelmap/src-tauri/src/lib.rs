// Prevents additional console window on Windows in release
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::fs::File;
use std::net::TcpStream;
use std::path::{Path, PathBuf};
use std::process::{Child, Command, Stdio};
use std::sync::Mutex;
use std::time::{Duration, Instant};
use tauri::{AppHandle, Manager, State};

#[cfg(target_os = "windows")]
use std::os::windows::process::CommandExt;

/// CREATE_NO_WINDOW — keep the console-less windowed app console-less.
#[cfg(target_os = "windows")]
const CREATE_NO_WINDOW: u32 = 0x0800_0000;

const BACKEND_PORT: u16 = 18080;
const SIDECAR_STEM: &str = "babelmap-backend";

pub struct PythonBackend(pub Mutex<Option<Child>>);

/// Directory holding `babelmap/backend/server.py` plus `babellib/` — only used
/// when the app runs from a source checkout instead of a bundle.
fn find_dev_repo_root() -> Option<PathBuf> {
    let mut dir = std::env::current_exe().ok()?.parent()?.to_path_buf();
    for _ in 0..6 {
        if dir.join("babelmap").join("backend").join("server.py").is_file() {
            return Some(dir);
        }
        if dir.join("backend").join("server.py").is_file() && dir.join("babellib").is_dir() {
            return Some(dir);
        }
        dir = dir.parent()?.to_path_buf();
    }
    None
}

/// The bundled sidecar binary, if this is a packaged build.
fn sidecar_path(app: &AppHandle) -> Option<PathBuf> {
    let name = if cfg!(windows) {
        format!("{SIDECAR_STEM}.exe")
    } else {
        SIDECAR_STEM.to_string()
    };
    if let Ok(exe) = std::env::current_exe() {
        if let Some(dir) = exe.parent() {
            let beside_exe = dir.join(&name);
            if beside_exe.is_file() {
                return Some(beside_exe);
            }
        }
    }
    // Some bundle formats keep external binaries under the resource dir.
    let resource = app.path().resource_dir().ok()?.join(&name);
    resource.is_file().then_some(resource)
}

/// The data tree: a Tauri resource for bundles, `babellib/data` in a checkout.
fn data_dir(app: &AppHandle, repo_root: Option<&Path>) -> Option<PathBuf> {
    if let Ok(resource) = app.path().resource_dir() {
        let bundled = resource.join("data");
        if bundled.is_dir() {
            return Some(bundled);
        }
    }
    repo_root.map(|root| root.join("babellib").join("data"))
}

/// Backend stdout/stderr → `backend.log` in the app log dir (support-friendly).
fn log_stdio(app: &AppHandle) -> Stdio {
    if let Ok(dir) = app.path().app_log_dir() {
        let _ = std::fs::create_dir_all(&dir);
        if let Ok(file) = File::create(dir.join("backend.log")) {
            return Stdio::from(file);
        }
    }
    Stdio::null()
}

fn spawn(
    exe: &Path,
    args: &[&str],
    cwd: Option<&Path>,
    env_data: Option<&Path>,
    app: &AppHandle,
) -> Result<Child, String> {
    let mut cmd = Command::new(exe);
    cmd.args(args)
        .env("BABELMAP_BACKEND_PORT", BACKEND_PORT.to_string())
        .stdout(log_stdio(app))
        .stderr(log_stdio(app));
    if let Some(cwd) = cwd {
        cmd.current_dir(cwd);
    }
    if let Some(data) = env_data {
        cmd.env("BABELSOFT_DATA_DIR", data);
    }
    #[cfg(target_os = "windows")]
    cmd.creation_flags(CREATE_NO_WINDOW);
    cmd.spawn()
        .map_err(|e| format!("failed to start {exe:?}: {e}"))
}

/// Wait until the backend accepts connections so the window does not race the
/// first API calls.
fn wait_until_ready(timeout: Duration) -> bool {
    let deadline = Instant::now() + timeout;
    while Instant::now() < deadline {
        if TcpStream::connect(("127.0.0.1", BACKEND_PORT)).is_ok() {
            return true;
        }
        std::thread::sleep(Duration::from_millis(120));
    }
    TcpStream::connect(("127.0.0.1", BACKEND_PORT)).is_ok()
}

#[tauri::command]
fn start_backend(app: AppHandle, state: State<PythonBackend>) -> Result<String, String> {
    let mut guard = state.0.lock().map_err(|e| e.to_string())?;
    if guard.is_some() {
        return Ok("Backend already running".into());
    }
    if TcpStream::connect(("127.0.0.1", BACKEND_PORT)).is_ok() {
        return Ok("Backend already listening".into());
    }

    let repo_root = find_dev_repo_root();
    let data = data_dir(&app, repo_root.as_deref());

    let child = match sidecar_path(&app) {
        Some(sidecar) => spawn(&sidecar, &[], None, data.as_deref(), &app)?,
        None => {
            let root = repo_root.ok_or_else(|| {
                "Cannot locate the BabelMap backend: no bundled sidecar and no source checkout \
                 (expected babelmap/backend/server.py)."
                    .to_string()
            })?;
            // Prefer uv so the checkout's own venv is used; fall back to python.
            spawn(
                Path::new("uv"),
                &["run", "python", "babelmap/backend/server.py"],
                Some(&root),
                data.as_deref(),
                &app,
            )
            .or_else(|_| {
                let python = if cfg!(windows) { "python" } else { "python3" };
                spawn(
                    Path::new(python),
                    &["babelmap/backend/server.py"],
                    Some(&root),
                    data.as_deref(),
                    &app,
                )
            })?
        }
    };

    *guard = Some(child);
    if wait_until_ready(Duration::from_secs(20)) {
        Ok("Backend started".into())
    } else {
        Err("The backend did not open 127.0.0.1:18080 in time; see backend.log".into())
    }
}

#[tauri::command]
fn stop_backend(state: State<PythonBackend>) -> Result<String, String> {
    let mut guard = state.0.lock().map_err(|e| e.to_string())?;
    if let Some(mut child) = guard.take() {
        child
            .kill()
            .map_err(|e| format!("Failed to kill backend: {}", e))?;
        child.wait().ok();
    }
    Ok("Backend stopped".into())
}

#[tauri::command]
fn get_backend_url() -> String {
    format!("http://127.0.0.1:{BACKEND_PORT}")
}

pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .manage(PythonBackend(Mutex::new(None)))
        .invoke_handler(tauri::generate_handler![
            start_backend,
            stop_backend,
            get_backend_url,
        ])
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::Destroyed = event {
                let state: State<PythonBackend> = window.state();
                if let Ok(mut guard) = state.0.lock() {
                    if let Some(mut child) = guard.take() {
                        child.kill().ok();
                        child.wait().ok();
                    }
                };
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running BabelMap");
}
