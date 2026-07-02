// Prevents additional console window on Windows in release
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::process::{Child, Command};
#[cfg(target_os = "windows")]
use std::os::windows::process::CommandExt;
use std::sync::Mutex;
use tauri::{Manager, State};

pub struct PythonBackend(pub Mutex<Option<Child>>);

#[tauri::command]
fn start_backend(state: State<PythonBackend>) -> Result<String, String> {
    let mut guard = state.0.lock().map_err(|e| e.to_string())?;
    if guard.is_some() {
        return Ok("Backend already running".into());
    }
    let python_cmd = if cfg!(target_os = "windows") { "python" } else { "python3" };
    let mut cmd = Command::new(python_cmd);
    cmd.args(["backend/server.py"])
        .current_dir(
            std::env::current_dir()
                .unwrap()
                .parent()
                .map(|p| p.to_path_buf())
                .unwrap_or_else(|| std::env::current_dir().unwrap()),
        );
    #[cfg(target_os = "windows")]
    { cmd.creation_flags(0x08000000); }
    let child = cmd.spawn()
        .map_err(|e| format!("Failed to start Python backend: {}", e))?;
    *guard = Some(child);
    Ok("Backend started".into())
}

#[tauri::command]
fn stop_backend(state: State<PythonBackend>) -> Result<String, String> {
    let mut guard = state.0.lock().map_err(|e| e.to_string())?;
    if let Some(mut child) = guard.take() {
        child.kill().map_err(|e| format!("Failed to kill backend: {}", e))?;
        child.wait().ok();
    }
    Ok("Backend stopped".into())
}

#[tauri::command]
fn get_backend_url() -> String {
    "http://127.0.0.1:18080".into()
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
