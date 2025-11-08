// Local JS/MJS plugin shims to reduce noisy "could not find declaration file" errors
// These export `unknown` so consumers must explicitly cast to the expected shape.
// This is intentionally conservative and safer than `any`.
declare module '*.js' {
	const value: unknown;
	export default value;
}
declare module '*.mjs' {
	const value: unknown;
	export default value;
}
declare module '*.cjs' {
	const value: unknown;
	export default value;
}

// Generic catch-all for local plugin files. Keep as `unknown` to force explicit casts
// where callers expect a particular export shape.
declare module '*/**/*.js' {
	const value: unknown;
	export default value;
}
