#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::path::PathBuf;
use std::process::{Child, Command};
use std::sync::{Arc, Mutex};
use std::thread;
use std::time::Duration;

use tauri::{api::shell::open, Manager, State};

struct EngineState {
    child: Mutex<Option<Child>>,
    resource_dir: Option<PathBuf>,
}

fn main() {
    tauri::Builder::default()
        .setup(|app| {
            let state = EngineState {
                child: Mutex::new(None),
                resource_dir: app.path_resolver().resource_dir(),
            };
            let state = Arc::new(state);
            spawn_engine(&state);
            start_engine_monitor(app.handle(), Arc::clone(&state));
            app.manage(state);
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![open_path, restart_engine])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}

fn spawn_engine(state: &Arc<EngineState>) {
    let mut child_guard = state.child.lock().expect("lock engine child");
    if child_guard.is_some() {
        return;
    }
    let child = if let Some(dir) = &state.resource_dir {
        let engine_path = dir.join("engine").join("vistar_engine.exe");
        if engine_path.exists() {
            Command::new(engine_path).spawn()
        } else {
            Command::new("python").args(["-m", "vistar_engine"]).spawn()
        }
    } else {
        Command::new("python").args(["-m", "vistar_engine"]).spawn()
    };
    if let Ok(child) = child {
        *child_guard = Some(child);
    }
}

fn start_engine_monitor(handle: tauri::AppHandle, state: Arc<EngineState>) {
    thread::spawn(move || loop {
        let child_opt = {
            let mut guard = state.child.lock().expect("lock engine child");
            guard.take()
        };

        if let Some(mut child) = child_opt {
            let exit_status = child.wait();
            println!("engine exited: {:?}", exit_status);
            let mut guard = state.child.lock().expect("lock engine child");
            *guard = None;
            drop(guard);
            thread::sleep(Duration::from_secs(1));
            spawn_engine(&state);
            let _ = handle.emit_all("engine-restarted", {});
        } else {
            thread::sleep(Duration::from_secs(2));
        }
    });
}

#[tauri::command]
fn open_path(app: tauri::AppHandle, path: String) -> Result<(), String> {
    open(&app.shell_scope(), path, None).map_err(|err| err.to_string())
}

#[tauri::command]
fn restart_engine(state: State<Arc<EngineState>>) -> Result<(), String> {
    let mut guard = state.child.lock().map_err(|_| "lock failed")?;
    if let Some(mut child) = guard.take() {
        let _ = child.kill();
    }
    drop(guard);
    spawn_engine(&state.inner().clone());
    Ok(())
}
