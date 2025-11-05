// Re-export the actual implementation from the project's path alias so
// tests that import via a relative path (e.g. ../components/...) continue
// to work without changing many test files.
export { Sidebar } from "#/components/features/sidebar/sidebar";
