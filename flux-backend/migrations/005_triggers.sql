-- Auto-refresh materialized views on task status update
CREATE OR REPLACE FUNCTION refresh_analytics_views()
RETURNS TRIGGER AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY user_weekly_stats;
    REFRESH MATERIALIZED VIEW CONCURRENTLY missed_by_category;
    REFRESH MATERIALIZED VIEW CONCURRENTLY activity_heatmap;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_refresh_analytics ON tasks;
CREATE TRIGGER trigger_refresh_analytics
    AFTER UPDATE OF status ON tasks
    FOR EACH STATEMENT
    EXECUTE FUNCTION refresh_analytics_views();

-- Auto-update patterns.updated_at
CREATE OR REPLACE FUNCTION update_patterns_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_patterns_updated_at ON patterns;
CREATE TRIGGER trigger_patterns_updated_at
    BEFORE UPDATE ON patterns
    FOR EACH ROW
    EXECUTE FUNCTION update_patterns_timestamp();
