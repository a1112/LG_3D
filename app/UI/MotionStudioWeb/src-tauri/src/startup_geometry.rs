//! Startup geometry uses logical sizes and physical monitor work areas.
use tauri::{LogicalSize, Manager, PhysicalPosition, Size, WebviewWindow};

pub fn install<R: tauri::Runtime>(
    window: &WebviewWindow<R>,
    preferred: (f64, f64),
    minimum: (f64, f64),
    existing_state: bool,
) -> tauri::Result<()> {
    let path = window
        .app_handle()
        .path()
        .app_local_data_dir()?
        .join(format!("{}-window-geometry.txt", window.label()));
    let saved = if existing_state {
        None
    } else {
        std::fs::read_to_string(&path)
            .ok()
            .and_then(|text| geometry_policy::parse(&text))
    };
    let monitors = window.available_monitors()?;
    let target = saved
        .as_ref()
        .and_then(|v| {
            monitors.iter().find(|monitor| {
                let area = monitor.work_area();
                v[0] >= area.position.x as f64
                    && v[0] < (area.position.x as f64 + area.size.width as f64)
                    && v[1] >= area.position.y as f64
                    && v[1] < (area.position.y as f64 + area.size.height as f64)
            })
        })
        .cloned()
        .or(window.current_monitor()?)
        .or(window.primary_monitor()?);
    if let Some(monitor) = target {
        let area = monitor.work_area();
        let scale = monitor.scale_factor();
        let available = area.size.to_logical::<f64>(scale);
        // Reserve desktop edges and native title-bar space, without a fixed oversized minimum.
        let cap = (
            (available.width - 64.0).max(1.0),
            (available.height - 96.0).max(1.0),
        );
        // Move to the target display before applying logical sizes (mixed-DPI monitors).
        if let Some(values) = saved.as_ref().filter(|_| {
            !window.is_maximized().unwrap_or(true) && !window.is_fullscreen().unwrap_or(true)
        }) {
            window.set_position(PhysicalPosition::new(
                (values[0] as i32).clamp(
                    area.position.x,
                    area.position.x + area.size.width as i32 - 1,
                ),
                (values[1] as i32).clamp(
                    area.position.y,
                    area.position.y + area.size.height as i32 - 1,
                ),
            ))?;
        }
        let current = window.inner_size()?.to_logical::<f64>(scale);
        let pos = window.outer_position()?;
        let (x, y, width, height) = saved
            .as_ref()
            .map(|v| (v[0] as i32, v[1] as i32, v[2], v[3]))
            .unwrap_or((pos.x, pos.y, current.width, current.height));
        let restored = existing_state || saved.is_some();
        let outer = window.outer_size()?;
        let frame = (
            (outer.width as f64 / scale - current.width).max(0.0),
            (outer.height as f64 / scale - current.height).max(0.0),
        );
        let fits = restored
            && width > 0.0
            && height > 0.0
            && x >= area.position.x
            && y >= area.position.y
            && x as f64 + (width + frame.0) * scale
                <= area.position.x as f64 + area.size.width as f64
            && y as f64 + (height + frame.1) * scale
                <= area.position.y as f64 + area.size.height as f64;
        let size = if restored {
            geometry_policy::restored_size(
                (width, height),
                (available.width, available.height),
                frame,
                cap,
            )
        } else {
            (
                preferred
                    .0
                    .min(available.width * 0.82)
                    .min(cap.0)
                    .max(minimum.0.min(cap.0)),
                preferred
                    .1
                    .min(available.height * 0.84)
                    .min(cap.1)
                    .max(minimum.1.min(cap.1)),
            )
        };
        let min_width = minimum.0.min(cap.0).min(size.0);
        let min_height = minimum.1.min(cap.1).min(size.1);
        window.set_min_size(Some(Size::Logical(LogicalSize::new(min_width, min_height))))?;
        if !window.is_maximized()? && !window.is_fullscreen()? {
            window.set_size(Size::Logical(LogicalSize::new(size.0, size.1)))?;
            let outer = window.outer_size()?;
            let max_x = area.position.x + area.size.width.saturating_sub(outer.width) as i32;
            let max_y = area.position.y + area.size.height.saturating_sub(outer.height) as i32;
            let position = if fits {
                PhysicalPosition::new(x, y)
            } else if restored {
                PhysicalPosition::new(
                    x.clamp(area.position.x, max_x),
                    y.clamp(area.position.y, max_y),
                )
            } else {
                PhysicalPosition::new(
                    area.position.x + (area.size.width.saturating_sub(outer.width) / 2) as i32,
                    area.position.y + (area.size.height.saturating_sub(outer.height) / 2) as i32,
                )
            };
            window.set_position(position)?;
        }
    }
    if !existing_state {
        let tracked = window.clone();
        window.on_window_event(move |event| {
            if matches!(
                event,
                tauri::WindowEvent::Moved(_)
                    | tauri::WindowEvent::Resized(_)
                    | tauri::WindowEvent::CloseRequested { .. }
            ) && !tracked.is_maximized().unwrap_or(true)
                && !tracked.is_fullscreen().unwrap_or(true)
                && !tracked.is_minimized().unwrap_or(true)
            {
                if let (Ok(position), Ok(size), Ok(scale)) = (
                    tracked.outer_position(),
                    tracked.inner_size(),
                    tracked.scale_factor(),
                ) {
                    let size = size.to_logical::<f64>(scale);
                    let _ = geometry_policy::write_atomic(
                        &path,
                        &format!(
                            "{} {} {} {}",
                            position.x, position.y, size.width, size.height
                        ),
                    );
                }
            }
        });
    }
    window.show()?;
    Ok(())
}

#[path = "geometry_policy.rs"]
mod geometry_policy;
