-- Auto-create public.users row when Supabase Auth creates a new user
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
DECLARE
    _name TEXT;
BEGIN
    _name := NEW.raw_user_meta_data->>'name';
    INSERT INTO public.users (id, email, profile)
    VALUES (
        NEW.id,
        NEW.email,
        CASE WHEN _name IS NOT NULL AND _name <> ''
            THEN jsonb_build_object('name', _name)
            ELSE NULL
        END
    )
    ON CONFLICT (id) DO NOTHING;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();
