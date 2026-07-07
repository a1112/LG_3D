mod app_config;
mod depth_data;
mod image_service;

use std::net::SocketAddr;
use std::path::PathBuf;
use std::sync::Arc;

use anyhow::Context;
use axum::Router;
use axum::routing::get;
use clap::Parser;
use tower_http::trace::TraceLayer;
use tracing::info;
use tracing_subscriber::EnvFilter;

use crate::app_config::{RuntimeConfig, default_server_config_path};
use crate::image_service::{
    AppState, area_image_compat, area_image_typed, classifier_image, clip_max_image,
    coil_data_area_image, defect_image, error_image, health, preview_image, render_image,
    source_image,
};

#[derive(Debug, Parser)]
#[command(author, version, about = "High-performance image service for LG_3D")]
struct Cli {
    #[arg(long)]
    config: Option<PathBuf>,
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
    let config_path = cli.config.unwrap_or_else(default_server_config_path);
    let runtime_config = RuntimeConfig::load(&config_path)
        .with_context(|| format!("failed to load {:?}", config_path))?;
    let state = Arc::new(AppState::new(runtime_config));

    let app = Router::new()
        .route("/health", get(health))
        .route(
            "/image/preview/{surface_key}/{coil_id}/{type_}",
            get(preview_image),
        )
        .route(
            "/image/source/{surface_key}/{coil_id}/{type_}",
            get(source_image),
        )
        .route(
            "/coilData/Render/{surfaceKey}/{coil_id}",
            get(render_image),
        )
        .route(
            "/coilData/Area/{surface_key}/{coil_id}",
            get(coil_data_area_image),
        )
        .route("/coilData/Error/{surface_key}/{coil_id}", get(error_image))
        .route(
            "/image/area/{surface_key}/{coil_id}",
            get(area_image_compat),
        )
        .route(
            "/image/area/{surface_key}/{coil_id}/{type_}",
            get(area_image_typed),
        )
        .route(
            "/classifier_image/{coil_id}/{surface_key}/{class_name}/{x}/{y}/{w}/{h}",
            get(classifier_image),
        )
        .route(
            "/defect_image/{surface_key}/{coil_id}/{type_}/{x}/{y}/{w}/{h}",
            get(defect_image),
        )
        .route("/clipMaxImage/{coil_id}/{key}", get(clip_max_image))
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
