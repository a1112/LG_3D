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
    let normalized_scheme = if scheme == "mysql" || scheme.starts_with("mysql+") {
        "mysql"
    } else if matches!(scheme.as_str(), "postgres" | "postgresql")
        || scheme.starts_with("postgres+")
        || scheme.starts_with("postgresql+")
    {
        "postgresql"
    } else {
        return Err(anyhow!(
            "unsupported database scheme; expected MySQL or PostgreSQL"
        ));
    };

    url.set_scheme(normalized_scheme)
        .map_err(|_| anyhow!("failed to normalize database url scheme"))?;
    // Keep PostgreSQL SSL/application options; SQLx supports the standard URI keys.
    // Preserve the established MySQL behavior that removes SQLAlchemy charset options.
    if normalized_scheme == "mysql" && url.query().is_some() {
        url.set_query(None);
    }
    Ok(url.to_string())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn normalizes_sqlalchemy_mysql_url() {
        let url = normalize_database_url(
            "mysql+pymysql://user:password@127.0.0.1:3306/coil?charset=utf8mb4",
        )
        .unwrap();
        assert_eq!(url, "mysql://user:password@127.0.0.1:3306/coil");
    }

    #[test]
    fn normalizes_sqlalchemy_postgres_url() {
        let url = normalize_database_url(
            "postgresql+psycopg://user:password@127.0.0.1:5432/coil?application_name=lg3d",
        )
        .unwrap();
        assert_eq!(
            url,
            "postgresql://user:password@127.0.0.1:5432/coil?application_name=lg3d"
        );
    }

    #[test]
    fn rejects_unsupported_database_url() {
        assert!(normalize_database_url("sqlite:///coil.db").is_err());
    }
}
