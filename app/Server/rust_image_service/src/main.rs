mod app_config;
mod image_service;

use std::net::SocketAddr;
use std::path::PathBuf;
use std::sync::Arc;

use anyhow::Context;
use axum::routing::get;
use axum::Router;
use clap::Parser;
use tower_http::trace::TraceLayer;
use tracing::info;
use tracing_subscriber::EnvFilter;

use crate::app_config::RuntimeConfig;
use crate::image_service::{
    area_image_compat, defect_image, health, preview_image, source_image, AppState,
};

#[derive(Debug, Parser)]
#[command(author, version, about = "High-performance image service for LG_3D")]
struct Cli {
    #[arg(long, default_value = "D:\\CONFIG_3D\\configs\\Server3D.json")]
    config: PathBuf,
    #[arg(long, default_value = "0.0.0.0")]
    host: String,
    #[arg(long, default_value_t = 6013)]
    port: u16,
}

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    tracing_subscriber::fmt()
        .with_env_filter(
            EnvFilter::try_from_default_env()
                .unwrap_or_else(|_| EnvFilter::new("rust_image_service=info,tower_http=info")),
        )
        .with_target(false)
        .init();

    let cli = Cli::parse();
    let runtime_config =
        RuntimeConfig::load(&cli.config).with_context(|| format!("failed to load {:?}", cli.config))?;
    let state = Arc::new(AppState::new(runtime_config));

    let app = Router::new()
        .route("/health", get(health))
        .route("/image/preview/{surface_key}/{coil_id}/{type_}", get(preview_image))
        .route("/image/source/{surface_key}/{coil_id}/{type_}", get(source_image))
        .route("/image/area/{surface_key}/{coil_id}", get(area_image_compat))
        .route(
            "/defect_image/{surface_key}/{coil_id}/{type_}/{x}/{y}/{w}/{h}",
            get(defect_image),
        )
        .layer(TraceLayer::new_for_http())
        .with_state(state);

    let addr: SocketAddr = format!("{}:{}", cli.host, cli.port)
        .parse()
        .with_context(|| format!("invalid bind address {}:{}", cli.host, cli.port))?;
    let listener = tokio::net::TcpListener::bind(addr).await?;
    info!("rust image service listening on http://{}", addr);
    axum::serve(listener, app).await?;
    Ok(())
}
