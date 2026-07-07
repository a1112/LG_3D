use anyhow::{Context, Result, anyhow};
use url::Url;

pub const DATABASE_URL_ENV: &str = "COIL_DATABASE_URL";

pub fn database_url_from_env() -> Result<String> {
    let raw = std::env::var(DATABASE_URL_ENV)
        .with_context(|| format!("{DATABASE_URL_ENV} is required"))?;
    normalize_database_url(&raw)
}

pub fn normalize_database_url(raw: &str) -> Result<String> {
    let mut url = Url::parse(raw).with_context(|| "invalid database url")?;
    let scheme = url.scheme().to_ascii_lowercase();
    if scheme == "mysql" || scheme.starts_with("mysql+") {
        url.set_scheme("mysql")
            .map_err(|_| anyhow!("failed to set mysql url scheme"))?;
        url.set_query(None);
        return Ok(url.to_string());
    }
    Err(anyhow!("only MySQL urls are currently supported"))
}
