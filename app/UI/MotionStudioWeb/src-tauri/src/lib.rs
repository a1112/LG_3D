use serde::{Deserialize, Serialize};
use std::{
    ffi::OsString,
    path::{Path, PathBuf},
    process::Command,
};
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

#[derive(Debug, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
struct ConnectionSettings {
    server_ip: String,
    server_port: i32,
    databas_port: i32,
    data_port: i32,
    plc_port: i32,
    alg2d_port: i32,
    use_rust_image_server: bool,
    rust_image_server_port: i32,
}

#[derive(Debug, PartialEq, Eq)]
struct CommandSpec {
    program: String,
    args: Vec<String>,
    preview: String,
}

fn normalize_connection_host(value: &str) -> String {
    let trimmed = value.trim();
    if trimmed.is_empty()
        || !trimmed.chars().all(|ch| ch.is_ascii_alphanumeric() || matches!(ch, '.' | '_' | '-'))
    {
        return "127.0.0.1".to_string();
    }
    trimmed.to_string()
}

fn normalize_connection_port(value: i32, fallback: i32) -> i32 {
    if value < 1 || value > 65535 {
        fallback
    } else {
        value
    }
}

fn normalize_connection_settings(settings: ConnectionSettings) -> ConnectionSettings {
    let server_ip = normalize_connection_host(&settings.server_ip);
    ConnectionSettings {
        server_ip,
        server_port: normalize_connection_port(settings.server_port, 5011),
        databas_port: normalize_connection_port(settings.databas_port, 6011),
        data_port: normalize_connection_port(settings.data_port, 6013),
        plc_port: normalize_connection_port(settings.plc_port, 6014),
        alg2d_port: if settings.alg2d_port == 6020 {
            5011
        } else {
            normalize_connection_port(settings.alg2d_port, 5011)
        },
        use_rust_image_server: settings.use_rust_image_server,
        rust_image_server_port: normalize_connection_port(settings.rust_image_server_port, 6013),
    }
}

fn resolve_connection_settings_path(app: &tauri::AppHandle) -> Result<PathBuf, String> {
    let mut config_dir = app.path().app_config_dir().map_err(|err| err.to_string())?;
    std::fs::create_dir_all(&config_dir).map_err(|err| err.to_string())?;
    config_dir.push("connection-settings.json");
    Ok(config_dir)
}

#[tauri::command]
fn read_connection_settings(app: tauri::AppHandle) -> Result<Option<ConnectionSettings>, String> {
    let settings_path = resolve_connection_settings_path(&app)?;
    if !settings_path.exists() {
        return Ok(None);
    }

    let raw = std::fs::read_to_string(&settings_path).map_err(|err| err.to_string())?;
    let parsed: ConnectionSettings = serde_json::from_str(&raw).map_err(|err| err.to_string())?;
    Ok(Some(normalize_connection_settings(parsed)))
}

#[tauri::command]
fn write_connection_settings(app: tauri::AppHandle, settings: ConnectionSettings) -> Result<(), String> {
    let settings_path = resolve_connection_settings_path(&app)?;
    let normalized = normalize_connection_settings(settings);
    let payload = serde_json::to_vec_pretty(&normalized).map_err(|err| err.to_string())?;
    std::fs::write(&settings_path, payload).map_err(|err| err.to_string())?;
    Ok(())
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

fn directory_dialog_directory(default_directory: Option<&str>) -> Option<PathBuf> {
    default_directory
        .map(str::trim)
        .filter(|value| !value.is_empty())
        .map(PathBuf::from)
}

fn pick_directory_path(default_directory: Option<&str>) -> Option<PathBuf> {
    let dialog = rfd::FileDialog::new();
    let dialog = match directory_dialog_directory(default_directory) {
        Some(directory) => dialog.set_directory(directory),
        None => dialog,
    };
    dialog.pick_folder()
}

#[tauri::command]
fn select_directory(default_directory: Option<String>) -> Result<Option<String>, String> {
    Ok(pick_directory_path(default_directory.as_deref())
        .map(|path| path.to_string_lossy().to_string()))
}

fn default_download_directory_from_env<E, F>(env_value: E, path_exists: F) -> Option<PathBuf>
where
    E: Fn(&str) -> Option<OsString>,
    F: Fn(&Path) -> bool,
{
    let mut homes = Vec::new();
    for key in ["USERPROFILE", "HOME"] {
        let Some(value) = env_value(key) else {
            continue;
        };
        if value.is_empty() {
            continue;
        }
        let home = PathBuf::from(value);
        if !homes.iter().any(|existing| existing == &home) {
            homes.push(home);
        }
    }

    for home in &homes {
        let downloads = home.join("Downloads");
        if path_exists(&downloads) {
            return Some(downloads);
        }
    }

    for home in &homes {
        let desktop = home.join("Desktop");
        if path_exists(&desktop) {
            return Some(desktop);
        }
    }

    homes.first().map(|home| home.join("Downloads"))
}

fn default_download_directory_path() -> Option<PathBuf> {
    default_download_directory_from_env(|key| std::env::var_os(key), |path| path.exists())
}

#[tauri::command]
fn default_download_directory() -> Result<Option<String>, String> {
    Ok(default_download_directory_path().map(|path| path.to_string_lossy().to_string()))
}

fn default_desktop_directory_from_env<E, F>(env_value: E, path_exists: F) -> Option<PathBuf>
where
    E: Fn(&str) -> Option<OsString>,
    F: Fn(&Path) -> bool,
{
    let mut homes = Vec::new();
    for key in ["USERPROFILE", "HOME"] {
        let Some(value) = env_value(key) else {
            continue;
        };
        if value.is_empty() {
            continue;
        }
        let home = PathBuf::from(value);
        if !homes.iter().any(|existing| existing == &home) {
            homes.push(home);
        }
    }

    for home in &homes {
        let desktop = home.join("Desktop");
        if path_exists(&desktop) {
            return Some(desktop);
        }
    }

    homes.first().map(|home| home.join("Desktop"))
}

fn default_desktop_directory_path() -> Option<PathBuf> {
    default_desktop_directory_from_env(|key| std::env::var_os(key), |path| path.exists())
}

#[tauri::command]
fn default_desktop_directory() -> Result<Option<String>, String> {
    Ok(default_desktop_directory_path().map(|path| path.to_string_lossy().to_string()))
}

fn default_pictures_directory_from_env<E, F>(env_value: E, path_exists: F) -> Option<PathBuf>
where
    E: Fn(&str) -> Option<OsString>,
    F: Fn(&Path) -> bool,
{
    let mut homes = Vec::new();
    for key in ["USERPROFILE", "HOME"] {
        let Some(value) = env_value(key) else {
            continue;
        };
        if value.is_empty() {
            continue;
        }
        let home = PathBuf::from(value);
        if !homes.iter().any(|existing| existing == &home) {
            homes.push(home);
        }
    }

    for home in &homes {
        let pictures = home.join("Pictures");
        if path_exists(&pictures) {
            return Some(pictures);
        }
    }

    homes.first().map(|home| home.join("Pictures"))
}

fn default_pictures_directory_path() -> Option<PathBuf> {
    default_pictures_directory_from_env(|key| std::env::var_os(key), |path| path.exists())
}

#[tauri::command]
fn default_pictures_directory() -> Result<Option<String>, String> {
    Ok(default_pictures_directory_path().map(|path| path.to_string_lossy().to_string()))
}

fn save_dialog_filter_extensions(default_name: &str) -> (&'static str, Vec<&'static str>) {
    let lower_name = default_name.trim().to_ascii_lowercase();
    if lower_name.ends_with(".db") || lower_name.ends_with(".sql") {
        ("Database Backup", vec!["db", "sql"])
    } else if lower_name.ends_with(".exe")
        || lower_name.ends_with(".msi")
        || lower_name.ends_with(".zip")
    {
        ("Update Package", vec!["exe", "msi", "zip"])
    } else {
        ("Excel Workbook", vec!["xlsx"])
    }
}

fn save_dialog_file_name(default_name: &str) -> &str {
    let trimmed = default_name.trim();
    if trimmed.is_empty() {
        "export.xlsx"
    } else {
        trimmed
    }
}

fn save_dialog_directory(default_directory: Option<&str>) -> Option<PathBuf> {
    default_directory
        .map(str::trim)
        .filter(|value| !value.is_empty())
        .map(PathBuf::from)
}

fn pick_save_file_path(file_name: &str, default_directory: Option<&str>) -> Option<PathBuf> {
    let (filter_name, filter_extensions) = save_dialog_filter_extensions(file_name);
    let dialog = rfd::FileDialog::new()
        .add_filter(filter_name, &filter_extensions)
        .set_file_name(file_name);
    let dialog = match save_dialog_directory(default_directory) {
        Some(directory) => dialog.set_directory(directory),
        None => dialog,
    };
    dialog.save_file()
}

#[tauri::command]
fn save_file_path(
    default_name: String,
    default_directory: Option<String>,
) -> Result<Option<String>, String> {
    Ok(pick_save_file_path(
        save_dialog_file_name(&default_name),
        default_directory.as_deref(),
    )
    .map(|path| path.to_string_lossy().to_string()))
}

#[tauri::command]
fn save_file(
    default_name: String,
    contents: Vec<u8>,
    default_directory: Option<String>,
) -> Result<Option<String>, String> {
    let Some(path) = pick_save_file_path(
        save_dialog_file_name(&default_name),
        default_directory.as_deref(),
    ) else {
        return Ok(None);
    };

    std::fs::write(&path, contents).map_err(|err| err.to_string())?;
    Ok(Some(path.to_string_lossy().to_string()))
}

fn write_file_to_path(path: &str, contents: &[u8]) -> Result<String, String> {
    let trimmed = path.trim();
    if trimmed.is_empty() {
        return Err("path is required".to_string());
    }

    std::fs::write(trimmed, contents).map_err(|err| err.to_string())?;
    Ok(PathBuf::from(trimmed).to_string_lossy().to_string())
}

#[tauri::command]
fn write_file(path: String, contents: Vec<u8>) -> Result<String, String> {
    write_file_to_path(&path, &contents)
}

fn open_path_command_spec(path: &str) -> Result<CommandSpec, String> {
    let trimmed = path.trim();
    if trimmed.is_empty() {
        return Err("path is required".to_string());
    }

    #[cfg(target_os = "windows")]
    {
        Ok(CommandSpec {
            program: "explorer.exe".to_string(),
            args: vec![trimmed.to_string()],
            preview: trimmed.to_string(),
        })
    }

    #[cfg(target_os = "macos")]
    {
        Ok(CommandSpec {
            program: "open".to_string(),
            args: vec![trimmed.to_string()],
            preview: trimmed.to_string(),
        })
    }

    #[cfg(all(unix, not(target_os = "macos")))]
    {
        Ok(CommandSpec {
            program: "xdg-open".to_string(),
            args: vec![trimmed.to_string()],
            preview: trimmed.to_string(),
        })
    }
}

#[tauri::command]
fn open_path(path: String) -> Result<String, String> {
    let spec = open_path_command_spec(&path)?;
    Command::new(&spec.program)
        .args(&spec.args)
        .spawn()
        .map_err(|err| err.to_string())?;
    Ok(spec.preview)
}

fn normalize_maintenance_host(value: &str) -> Option<String> {
    let trimmed = value.trim();
    if trimmed.is_empty() {
        return None;
    }

    let without_protocol = trimmed
        .split_once("://")
        .map(|(_, right)| right)
        .unwrap_or(trimmed);
    let host_port = without_protocol
        .split(['/', '?', '#'])
        .next()
        .unwrap_or("")
        .trim_matches(['[', ']']);
    let host = host_port.split(':').next().unwrap_or("");
    if host.is_empty()
        || !host
            .chars()
            .all(|ch| ch.is_ascii_alphanumeric() || matches!(ch, '.' | '_' | '-'))
    {
        return None;
    }

    Some(host.to_string())
}

fn maintenance_command_spec(action: &str, host: &str) -> Result<CommandSpec, String> {
    let host =
        normalize_maintenance_host(host).ok_or_else(|| "invalid maintenance host".to_string())?;
    match action {
        "remoteDesktop" => Ok(CommandSpec {
            program: "mstsc".to_string(),
            args: vec!["/v".to_string(), host.clone()],
            preview: format!("mstsc /v {host}"),
        }),
        "pingServer" => Ok(CommandSpec {
            program: "cmd".to_string(),
            args: vec![
                "/C".to_string(),
                "start".to_string(),
                "LG3D Ping".to_string(),
                "ping".to_string(),
                host.clone(),
                "-t".to_string(),
            ],
            preview: format!("ping {host} -t"),
        }),
        _ => Err("unsupported maintenance action".to_string()),
    }
}

#[tauri::command]
fn launch_maintenance_tool(action: String, host: String) -> Result<String, String> {
    let spec = maintenance_command_spec(&action, &host)?;
    Command::new(&spec.program)
        .args(&spec.args)
        .spawn()
        .map_err(|err| err.to_string())?;
    Ok(spec.preview)
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
            system_info,
            select_directory,
            default_download_directory,
            default_desktop_directory,
            default_pictures_directory,
            save_file_path,
            save_file,
            write_file,
            open_path,
            launch_maintenance_tool,
            read_connection_settings,
            write_connection_settings
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

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn maintenance_host_normalization_rejects_shell_metacharacters() {
        assert_eq!(
            normalize_maintenance_host(" http://127.0.0.1:5011/path ").as_deref(),
            Some("127.0.0.1")
        );
        assert_eq!(
            normalize_maintenance_host("server-name_01.example.com").as_deref(),
            Some("server-name_01.example.com")
        );
        assert_eq!(normalize_maintenance_host("bad host && del C:\\"), None);
    }

    #[test]
    fn maintenance_command_specs_match_qml_tools_menu_actions() {
        assert_eq!(
            maintenance_command_spec("remoteDesktop", "192.168.1.20").unwrap(),
            CommandSpec {
                program: "mstsc".to_string(),
                args: vec!["/v".to_string(), "192.168.1.20".to_string()],
                preview: "mstsc /v 192.168.1.20".to_string(),
            }
        );
        assert_eq!(
            maintenance_command_spec("pingServer", "192.168.1.20")
                .unwrap()
                .preview,
            "ping 192.168.1.20 -t"
        );
        assert!(maintenance_command_spec("restartServer", "192.168.1.20").is_err());
    }

    #[test]
    fn open_path_command_spec_opens_local_paths_without_shell_concatenation() {
        let spec = open_path_command_spec(" D:\\Downloads\\MotionStudio.exe ").unwrap();
        assert_eq!(spec.preview, "D:\\Downloads\\MotionStudio.exe");
        assert!(spec
            .args
            .iter()
            .any(|arg| arg == "D:\\Downloads\\MotionStudio.exe"));
        assert!(open_path_command_spec("   ").is_err());
    }

    #[test]
    fn write_file_to_path_writes_qml_simple_file_input_selection() {
        let path = std::env::temp_dir().join(format!(
            "motion_studio_report_export_{}.xlsx",
            std::process::id()
        ));
        let _ = std::fs::remove_file(&path);

        let saved_path = write_file_to_path(path.to_string_lossy().as_ref(), &[80, 75, 3, 4])
            .expect("selected export path should be writable");

        assert_eq!(std::path::PathBuf::from(saved_path), path);
        assert_eq!(std::fs::read(&path).unwrap(), vec![80, 75, 3, 4]);
        assert!(write_file_to_path("   ", &[1]).is_err());

        let _ = std::fs::remove_file(path);
    }

    #[cfg(target_os = "windows")]
    #[test]
    fn open_path_command_spec_uses_explorer_for_windows_paths_with_shell_metacharacters() {
        let spec = open_path_command_spec(" D:\\Exports\\A&B\\report.xlsx ").unwrap();

        assert_eq!(spec.program, "explorer.exe");
        assert_eq!(spec.args, vec!["D:\\Exports\\A&B\\report.xlsx".to_string()]);
        assert_eq!(spec.preview, "D:\\Exports\\A&B\\report.xlsx");
    }

    #[test]
    fn default_download_directory_prefers_downloads_and_falls_back_to_desktop() {
        let home = std::path::PathBuf::from("C:\\Users\\operator");
        let env_home = home.as_os_str().to_os_string();

        let downloads = default_download_directory_from_env(
            |key| (key == "USERPROFILE").then(|| env_home.clone()),
            |path| path == home.join("Downloads"),
        )
        .unwrap();
        assert_eq!(downloads, home.join("Downloads"));

        let desktop = default_download_directory_from_env(
            |key| (key == "USERPROFILE").then(|| env_home.clone()),
            |path| path == home.join("Desktop"),
        )
        .unwrap();
        assert_eq!(desktop, home.join("Desktop"));
    }

    #[test]
    fn default_desktop_directory_matches_qml_backup_data_view_desktop_location() {
        let home = std::path::PathBuf::from("C:\\Users\\operator");
        let env_home = home.as_os_str().to_os_string();

        let desktop = default_desktop_directory_from_env(
            |key| (key == "USERPROFILE").then(|| env_home.clone()),
            |path| path == home.join("Desktop"),
        )
        .unwrap();
        assert_eq!(desktop, home.join("Desktop"));

        let candidate = default_desktop_directory_from_env(
            |key| (key == "USERPROFILE").then(|| env_home.clone()),
            |_path| false,
        )
        .unwrap();
        assert_eq!(candidate, home.join("Desktop"));
    }

    #[test]
    fn default_pictures_directory_matches_qml_defect_export_location() {
        let home = std::path::PathBuf::from("C:\\Users\\operator");
        let env_home = home.as_os_str().to_os_string();

        let pictures = default_pictures_directory_from_env(
            |key| (key == "USERPROFILE").then(|| env_home.clone()),
            |path| path == home.join("Pictures"),
        )
        .unwrap();
        assert_eq!(pictures, home.join("Pictures"));

        let candidate = default_pictures_directory_from_env(
            |key| (key == "USERPROFILE").then(|| env_home.clone()),
            |_path| false,
        )
        .unwrap();
        assert_eq!(candidate, home.join("Pictures"));
    }

    #[test]
    fn default_download_directory_keeps_a_downloads_candidate_when_standard_dirs_do_not_exist() {
        let home = std::path::PathBuf::from("C:\\Users\\operator");
        let env_home = home.as_os_str().to_os_string();

        let candidate = default_download_directory_from_env(
            |key| (key == "USERPROFILE").then(|| env_home.clone()),
            |_path| false,
        )
        .unwrap();

        assert_eq!(candidate, home.join("Downloads"));
        assert!(default_download_directory_from_env(|_key| None, |_path| true).is_none());
    }

    #[test]
    fn save_dialog_filters_match_export_and_update_packages() {
        assert_eq!(
            save_dialog_filter_extensions("report.xlsx"),
            ("Excel Workbook", vec!["xlsx"])
        );
        assert_eq!(
            save_dialog_filter_extensions("lg3d_backup_20260701_103015.db"),
            ("Database Backup", vec!["db", "sql"])
        );
        assert_eq!(
            save_dialog_filter_extensions("lg3d_backup_20260701_103015.sql"),
            ("Database Backup", vec!["db", "sql"])
        );
        assert_eq!(
            save_dialog_filter_extensions("MotionStudio.exe"),
            ("Update Package", vec!["exe", "msi", "zip"])
        );
        assert_eq!(
            save_dialog_filter_extensions("MotionStudio.msi"),
            ("Update Package", vec!["exe", "msi", "zip"])
        );
        assert_eq!(
            save_dialog_filter_extensions("archive.zip"),
            ("Update Package", vec!["exe", "msi", "zip"])
        );
    }

    #[test]
    fn save_dialog_directory_uses_qml_desktop_default_when_provided() {
        assert_eq!(
            save_dialog_directory(Some(" C:\\Users\\operator\\Desktop ")).unwrap(),
            PathBuf::from("C:\\Users\\operator\\Desktop")
        );
        assert!(save_dialog_directory(Some("   ")).is_none());
        assert!(save_dialog_directory(None).is_none());
    }

    #[test]
    fn directory_dialog_directory_uses_qml_pictures_default_when_provided() {
        assert_eq!(
            directory_dialog_directory(Some(" C:\\Users\\operator\\Pictures ")).unwrap(),
            PathBuf::from("C:\\Users\\operator\\Pictures")
        );
        assert!(directory_dialog_directory(Some("   ")).is_none());
        assert!(directory_dialog_directory(None).is_none());
    }
}
