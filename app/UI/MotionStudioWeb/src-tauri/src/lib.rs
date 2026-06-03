use serde::Serialize;
use tauri::{Manager, WebviewWindow};

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
struct WindowState {
    maximized: bool,
    fullscreen: bool,
    focused: bool,
    visible: bool,
    inner_size: String,
}

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
struct SystemInfo {
    cpu_usage: f32,
    memory_used: u64,
    memory_total: u64,
    memory_percent: f32,
}

#[tauri::command]
fn start_drag_window(window: WebviewWindow) -> Result<(), String> {
    window.start_dragging().map_err(|err| err.to_string())
}

#[tauri::command]
fn minimize_window(window: WebviewWindow) -> Result<(), String> {
    window.minimize().map_err(|err| err.to_string())
}

#[tauri::command]
fn toggle_maximize_window(window: WebviewWindow) -> Result<bool, String> {
    if window.is_maximized().map_err(|err| err.to_string())? {
        window.unmaximize().map_err(|err| err.to_string())?;
        Ok(false)
    } else {
        window.maximize().map_err(|err| err.to_string())?;
        Ok(true)
    }
}

#[tauri::command]
fn toggle_fullscreen_window(window: WebviewWindow) -> Result<bool, String> {
    let next = !window.is_fullscreen().map_err(|err| err.to_string())?;
    window.set_fullscreen(next).map_err(|err| err.to_string())?;
    Ok(next)
}

#[tauri::command]
fn close_window(window: WebviewWindow) -> Result<(), String> {
    window.close().map_err(|err| err.to_string())
}

#[tauri::command]
fn window_state(window: WebviewWindow) -> Result<WindowState, String> {
    let inner_size = window.inner_size().map_err(|err| err.to_string())?;
    Ok(WindowState {
        maximized: window.is_maximized().unwrap_or(false),
        fullscreen: window.is_fullscreen().map_err(|err| err.to_string())?,
        focused: window.is_focused().map_err(|err| err.to_string())?,
        visible: window.is_visible().map_err(|err| err.to_string())?,
        inner_size: format!("{} x {}", inner_size.width, inner_size.height),
    })
}

#[tauri::command]
fn system_info() -> Result<SystemInfo, String> {
    use sysinfo::{get_current_pid, ProcessesToUpdate, System};

    let mut sys = System::new_all();
    sys.refresh_all();
    let current_pid = get_current_pid().map_err(|err| err.to_string())?;
    sys.refresh_processes(ProcessesToUpdate::Some(&[current_pid]), true);

    let (cpu_usage, memory_used) = sys
        .process(current_pid)
        .map(|process| (process.cpu_usage(), process.memory()))
        .unwrap_or((0.0, 0));
    let memory_total = sys.total_memory();
    let memory_percent = if memory_total > 0 {
        (memory_used as f32 / memory_total as f32) * 100.0
    } else {
        0.0
    };

    Ok(SystemInfo {
        cpu_usage,
        memory_used,
        memory_total,
        memory_percent,
    })
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .invoke_handler(tauri::generate_handler![
            start_drag_window,
            minimize_window,
            toggle_maximize_window,
            toggle_fullscreen_window,
            close_window,
            window_state,
            system_info
        ])
        .setup(|app| {
            if let Some(window) = app.get_webview_window("main") {
                let _ = window.set_decorations(false);
            }
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
