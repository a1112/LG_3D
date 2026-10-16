use std::{fs, io, path::Path};

pub fn parse(text: &str) -> Option<Vec<f64>> {
    let values = text
        .split_whitespace()
        .map(str::parse::<f64>)
        .collect::<Result<Vec<_>, _>>()
        .ok()?;
    (values.len() == 4
        && values.iter().all(|v| v.is_finite())
        && values[2] > 0.0
        && values[3] > 0.0)
        .then_some(values)
}

pub fn write_atomic(path: &Path, contents: &str) -> io::Result<()> {
    if let Some(parent) = path.parent().filter(|p| !p.as_os_str().is_empty()) {
        fs::create_dir_all(parent)?;
    }
    let temporary = path.with_extension(format!("tmp-{}", std::process::id()));
    fs::write(&temporary, contents)?;
    match fs::rename(&temporary, path) {
        Ok(()) => Ok(()),
        Err(error) => {
            let _ = fs::remove_file(temporary);
            Err(error)
        }
    }
}

pub fn restored_size(
    saved: (f64, f64),
    available: (f64, f64),
    frame: (f64, f64),
    cap: (f64, f64),
) -> (f64, f64) {
    fn axis(value: f64, available: f64, frame: f64, cap: f64) -> f64 {
        if value <= (available - frame).max(1.0) {
            value
        } else {
            value.min(cap).max(1.0)
        }
    }
    (
        axis(saved.0, available.0, frame.0, cap.0),
        axis(saved.1, available.1, frame.1, cap.1),
    )
}

/// Nominal content minima must not expand a first-run window toward fullscreen
/// on compact displays. The runtime minimum is clamped to this fitted size.
pub fn first_size(preferred: (f64, f64), available: (f64, f64), cap: (f64, f64)) -> (f64, f64) {
    (
        preferred.0.min(available.0 * 0.82).min(cap.0).max(1.0),
        preferred.1.min(available.1 * 0.84).min(cap.1).max(1.0),
    )
}

/// Convert a logical rectangle for a selected display without depending on
/// the window's (possibly not yet updated) DPI after a monitor move.
pub fn physical_size(size: (f64, f64), scale: f64) -> (u32, u32) {
    (
        (size.0 * scale).round() as u32,
        (size.1 * scale).round() as u32,
    )
}

pub fn logical_frame(inner: (u32, u32), outer: (u32, u32), scale: f64) -> (f64, f64) {
    (
        outer.0.saturating_sub(inner.0) as f64 / scale,
        outer.1.saturating_sub(inner.1) as f64 / scale,
    )
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn macbook_air_and_compact_work_areas_keep_first_launch_compact() {
        for scale in [1.0, 2.0] {
            for available in [(1280.0, 720.0), (960.0, 600.0), (1920.0, 1080.0)] {
                let cap = (available.0 - 64.0, available.1 - 96.0);
                let first = first_size((1240.0, 800.0), available, cap);
                let native = physical_size(first, scale);
                assert!(first.0 <= available.0 * 0.82 && first.1 <= available.1 * 0.84);
                assert!(native.0 as f64 <= available.0 * scale);
                assert!(native.1 as f64 <= available.1 * scale);
                let minimum = (
                    1180.0_f64.min(cap.0).min(first.0),
                    720.0_f64.min(cap.1).min(first.1),
                );
                assert!(minimum.0 <= first.0 && minimum.1 <= first.1);
                assert_eq!(
                    restored_size((640.0, 400.0), available, (0.0, 32.0), cap),
                    (640.0, 400.0)
                );
                assert_eq!(
                    restored_size((5000.0, 4000.0), available, (0.0, 32.0), cap),
                    cap
                );
            }
        }
    }

    #[test]
    fn mixed_dpi_uses_target_physical_size_and_original_frame_scale() {
        let logical = (640.0, 400.0);
        assert_eq!(physical_size(logical, 2.0), (1280, 800));
        assert_eq!(physical_size(logical, 1.0), (640, 400));
        assert_eq!(physical_size(logical, 1.5), (960, 600));
        // A current 2x title bar remains 32 logical pixels on a target 1x screen.
        let frame = logical_frame((1280, 800), (1280, 864), 2.0);
        assert_eq!(frame, (0.0, 32.0));
        assert_eq!(physical_size(frame, 1.0), (0, 32));
        assert_eq!(physical_size(frame, 2.0), (0, 64));
        assert_eq!(logical_frame((640, 400), (640, 432), 1.0), frame);
    }

    #[test]
    fn strict_records() {
        assert_eq!(
            parse("-3000 20 640 400").unwrap(),
            vec![-3000.0, 20.0, 640.0, 400.0]
        );
        for text in [
            "0 0 800 600 garbage",
            "0 0 800 600 700",
            "0 0 NaN 600",
            "0 0 inf 600",
            "0 0 0 600",
            "0 0 -1 600",
            "0 0 800",
        ] {
            assert!(parse(text).is_none(), "{text}");
        }
    }
    #[test]
    fn position_repair_does_not_expand_saved_size() {
        assert_eq!(
            restored_size(
                (640.0, 400.0),
                (1280.0, 800.0),
                (0.0, 32.0),
                (1216.0, 704.0)
            ),
            (640.0, 400.0)
        );
    }
    #[test]
    fn keep_valid_edge_dimensions_only_shrink_invalid_axis() {
        assert_eq!(
            restored_size(
                (1280.0, 768.0),
                (1280.0, 800.0),
                (0.0, 32.0),
                (1216.0, 704.0)
            ),
            (1280.0, 768.0)
        );
        assert_eq!(
            restored_size(
                (1280.0, 1000.0),
                (1280.0, 800.0),
                (0.0, 32.0),
                (1216.0, 704.0)
            ),
            (1280.0, 704.0)
        );
        assert_eq!(
            restored_size(
                (1280.0, 768.0),
                (1280.0, 800.0),
                (16.0, 32.0),
                (1216.0, 704.0)
            ),
            (1216.0, 768.0)
        );
    }
    #[test]
    fn high_dpi_and_small_work_areas() {
        assert_eq!(
            restored_size(
                (640.0, 400.0),
                (2560.0 / 2.0, 1600.0 / 2.0),
                (0.0, 32.0),
                (1216.0, 704.0)
            ),
            (640.0, 400.0)
        );
        assert_eq!(
            restored_size(
                (1800.0, 1100.0),
                (640.0, 480.0),
                (0.0, 32.0),
                (576.0, 384.0)
            ),
            (576.0, 384.0)
        );
    }
    #[test]
    fn atomic_save_preserves_old_record_if_temporary_write_fails() {
        let dir = std::env::temp_dir().join(format!("codex-window-policy-{}", std::process::id()));
        fs::create_dir_all(&dir).unwrap();
        let path = dir.join("geometry.txt");
        write_atomic(&path, "0 20 640 400").unwrap();
        let temporary = path.with_extension(format!("tmp-{}", std::process::id()));
        fs::create_dir(&temporary).unwrap();
        assert!(write_atomic(&path, "0 20 800 600").is_err());
        assert_eq!(fs::read_to_string(&path).unwrap(), "0 20 640 400");
        fs::remove_dir_all(dir).unwrap();
    }
}
