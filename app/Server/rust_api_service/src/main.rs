use std::net::SocketAddr;
use std::sync::Arc;

use anyhow::Context;
use clap::Parser;
use rust_api_service::{
    ApiState, DataRuntimeConfig, MySqlCoilRepository, TestModeConfig, build_app,
    database_url_from_env,
};
use tracing::info;
use tracing_subscriber::EnvFilter;

const DEFAULT_API_HOST: &str = "0.0.0.0";
const DEFAULT_API_PORT: u16 = 5011;
const LEGACY_API_PORT: u16 = 5010;

#[derive(Debug, Parser)]
#[command(author, version, about = "Rust API service for LG_3D Motion Studio")]
struct Cli {
    #[arg(long)]
    host: Option<String>,

    #[arg(long)]
    port: Option<u16>,

    /// When no --port argument is provided, try this legacy port if primary bind fails.
    #[arg(long, default_value_t = false)]
    fallback_legacy_port: bool,
}

fn env_flag(name: &str, fallback: bool) -> bool {
    match std::env::var(name).ok().map(|raw| raw.trim().to_lowercase()) {
        Some(raw) => match raw.as_str() {
            "1" | "true" | "t" | "yes" | "y" | "on" | "enabled" | "enable" => true,
            "0" | "false" | "f" | "no" | "n" | "off" | "disabled" | "disable" => false,
            _ => fallback,
        },
        None => fallback,
    }
}

fn env_u16(name: &str) -> Option<u16> {
    std::env::var(name).ok().and_then(|raw| raw.parse::<u16>().ok())
}

fn resolve_api_host(cli_host: Option<String>) -> String {
    cli_host
        .filter(|host| !host.trim().is_empty())
        .or_else(|| std::env::var("RUST_API_HOST").ok())
        .or_else(|| std::env::var("API_SERVICE_HOST").ok())
        .unwrap_or_else(|| DEFAULT_API_HOST.to_string())
        .trim()
        .to_string()
}

fn resolve_api_port(cli_port: Option<u16>) -> Vec<u16> {
    let requested = cli_port
        .or_else(|| env_u16("RUST_API_PORT"))
        .or_else(|| env_u16("API_SERVICE_PORT"))
        .unwrap_or(DEFAULT_API_PORT);
    vec![requested]
}

fn build_bind_ports(requested_ports: Vec<u16>, fallback_enabled: bool) -> Vec<u16> {
    let mut ports = requested_ports;
    let fallback_port = env_u16("RUST_API_LEGACY_PORT").unwrap_or(LEGACY_API_PORT);
    if fallback_enabled && !ports.contains(&fallback_port) {
        ports.push(fallback_port);
    }
    ports
}

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    tracing_subscriber::fmt()
        .with_env_filter(
            EnvFilter::try_from_default_env()
                .unwrap_or_else(|_| EnvFilter::new("rust_api_service=info,tower_http=info")),
        )
        .with_target(false)
        .init();

    let cli = Cli::parse();
    let database_url = database_url_from_env()?;
    let repository = Arc::new(MySqlCoilRepository::connect(&database_url).await?);
    let mut state = ApiState::new(repository).with_test_mode(TestModeConfig::from_env());
    if let Some(data_config) = DataRuntimeConfig::load_default() {
        state = state.with_data_config(data_config);
    }
    let app = build_app(state);
    let host = resolve_api_host(cli.host);
    let fallback_enabled =
        cli.port.is_none() && env_flag("RUST_API_FALLBACK_LEGACY_PORT", cli.fallback_legacy_port);
    let ports = build_bind_ports(resolve_api_port(cli.port), fallback_enabled);

    let mut listener = None;
    let mut bind_error = None;
    for port in ports {
        let addr: SocketAddr = format!("{}:{}", host, port)
            .parse()
            .with_context(|| format!("invalid bind address {}:{}", host, port))?;
        match tokio::net::TcpListener::bind(addr).await {
            Ok(bound_listener) => {
                info!("rust api service listening on http://{}", addr);
                listener = Some(bound_listener);
                break;
            }
            Err(error) => {
                bind_error = Some(error);
                info!(
                    "failed to bind rust api service on {}:{}, trying next candidate if available",
                    host, port
                );
            }
        }
    }

    let listener = listener.with_context(|| {
        let last = bind_error
            .map(|error| error.to_string())
            .unwrap_or_else(|| "unknown error".to_string());
        format!("all api bind attempts failed: {last}")
    })?;

    axum::serve(listener, app).await?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::env;
    use std::sync::{Mutex, OnceLock};

    static ENV_LOCK: OnceLock<Mutex<()>> = OnceLock::new();

    fn with_env_vars<F>(updates: &[(&str, Option<&str>)], test: F)
    where
        F: FnOnce(),
    {
        let _guard = ENV_LOCK.get_or_init(|| Mutex::new(())).lock().unwrap();
        let previous: Vec<(&str, Option<String>)> = updates
            .iter()
            .map(|(key, _)| (*key, env::var(key).ok()))
            .collect();

        for (key, value) in updates {
            unsafe {
                if let Some(next) = value {
                    env::set_var(key, next);
                } else {
                    env::remove_var(key);
                }
            }
        }

        test();

        for (key, value) in previous {
            unsafe {
                match value {
                    Some(old) => env::set_var(key, old),
                    None => env::remove_var(key),
                }
            }
        }
    }

    #[test]
    fn env_flag_parses_truthy_and_falsy_values() {
        with_env_vars(&[("RUST_API_FALLBACK_LEGACY_PORT", Some("1"))], || {
            assert!(env_flag("RUST_API_FALLBACK_LEGACY_PORT", false));
        });
        with_env_vars(&[("RUST_API_FALLBACK_LEGACY_PORT", Some("true"))], || {
            assert!(env_flag("RUST_API_FALLBACK_LEGACY_PORT", false));
        });
        with_env_vars(&[("RUST_API_FALLBACK_LEGACY_PORT", Some("0"))], || {
            assert!(!env_flag("RUST_API_FALLBACK_LEGACY_PORT", true));
        });
        with_env_vars(&[("RUST_API_FALLBACK_LEGACY_PORT", Some("no"))], || {
            assert!(!env_flag("RUST_API_FALLBACK_LEGACY_PORT", true));
        });
        with_env_vars(&[("RUST_API_FALLBACK_LEGACY_PORT", Some("on"))], || {
            assert!(env_flag("RUST_API_FALLBACK_LEGACY_PORT", false));
        });
        with_env_vars(&[("RUST_API_FALLBACK_LEGACY_PORT", Some("off"))], || {
            assert!(!env_flag("RUST_API_FALLBACK_LEGACY_PORT", true));
        });
        with_env_vars(&[("RUST_API_FALLBACK_LEGACY_PORT", Some("nonsense"))], || {
            assert!(!env_flag("RUST_API_FALLBACK_LEGACY_PORT", false));
        });
        with_env_vars(&[("RUST_API_FALLBACK_LEGACY_PORT", None)], || {
            assert!(env_flag("RUST_API_FALLBACK_LEGACY_PORT", true));
            assert!(!env_flag("RUST_API_FALLBACK_LEGACY_PORT", false));
        });
    }

    #[test]
    fn resolve_api_host_prefers_cli_then_env_then_api_host() {
        with_env_vars(
            &[
                ("RUST_API_HOST", Some("env-api-host")),
                ("API_SERVICE_HOST", Some("legacy-host")),
            ],
            || {
                assert_eq!(
                    resolve_api_host(Some("cli-host".to_string())),
                    "cli-host"
                );
                assert_eq!(
                    resolve_api_host(None),
                    "env-api-host"
                );
            },
        );

        with_env_vars(
            &[
                ("RUST_API_HOST", None),
                ("API_SERVICE_HOST", Some("legacy-host")),
            ],
            || {
                assert_eq!(resolve_api_host(Some("".to_string())), "legacy-host");
            },
        );
    }

    #[test]
    fn build_bind_ports_respects_fallback_and_duplicates() {
        with_env_vars(&[("RUST_API_LEGACY_PORT", Some("6010"))], || {
            assert_eq!(
                build_bind_ports(vec![5011], false),
                vec![5011]
            );
            assert_eq!(build_bind_ports(vec![5011], true), vec![5011, 6010]);
            assert_eq!(build_bind_ports(vec![6010], true), vec![6010]);
            assert_eq!(
                build_bind_ports(vec![6000, 7000], true),
                vec![6000, 7000, 6010]
            );
        });

        with_env_vars(&[("RUST_API_LEGACY_PORT", None)], || {
            assert_eq!(build_bind_ports(vec![5011], true), vec![5011, 5010]);
        });
    }
}
