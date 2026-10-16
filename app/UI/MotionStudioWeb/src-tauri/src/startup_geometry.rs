//! Startup geometry uses logical sizes and physical monitor work areas.
use tauri::{Manager, PhysicalPosition, PhysicalSize, Size, WebviewWindow};

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
        // Native frame measurements still belong to the current display. A move
        // may deliver its DPI event later, so capture this scale before moving.
        let current_scale = window.scale_factor()?;
        let current_inner = window.inner_size()?;
        let current_outer = window.outer_size()?;
        let frame = geometry_policy::logical_frame(
            (current_inner.width, current_inner.height),
            (current_outer.width, current_outer.height),
            current_scale,
        );
        // Apply target-display physical sizes; logical setters can use a stale
        // window scale until the cross-display move has been processed.
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
            geometry_policy::first_size(preferred, (available.width, available.height), cap)
        };
        let min_width = minimum.0.min(cap.0).min(size.0);
        let min_height = minimum.1.min(cap.1).min(size.1);
        let physical_min = geometry_policy::physical_size((min_width, min_height), scale);
        window.set_min_size(Some(Size::Physical(PhysicalSize::new(
            physical_min.0,
            physical_min.1,
        ))))?;
        if !window.is_maximized()? && !window.is_fullscreen()? {
            let physical = geometry_policy::physical_size(size, scale);
            window.set_size(Size::Physical(PhysicalSize::new(physical.0, physical.1)))?;
            // Size/move calls are asynchronous on some platforms. Compute the
            // intended outer rectangle instead of reading the previous size.
            let physical_frame = geometry_policy::physical_size(frame, scale);
            let outer = PhysicalSize::new(
                physical.0.saturating_add(physical_frame.0),
                physical.1.saturating_add(physical_frame.1),
            );
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
