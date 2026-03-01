// Minimal type declarations for @supabase/ssr (package does not ship types)
declare module "@supabase/ssr" {
  export function createServerClient(
    supabaseUrl: string,
    supabaseKey: string,
    options: {
      cookies: {
        getAll(): Array<{ name: string; value: string }>;
        setAll(cookies: Array<{ name: string; value: string; options?: Record<string, unknown> }>): void;
      };
    }
  ): import("@supabase/supabase-js").SupabaseClient;
}
