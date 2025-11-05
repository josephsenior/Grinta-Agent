Repro: react-router dev plugin detection

Steps to reproduce the "React Router Vite plugin not found" behavior locally:

1. From this directory, install dependencies:

   npm install

2. Try the React Router CLI:

   npx react-router dev

3. If the CLI exits with "React Router Vite plugin not found in Vite config", try running Vite directly to confirm the app runs:

   npm run dev

Notes

- This repo intentionally imports `reactRouter()` from `@react-router/dev/vite` in `vite.config.ts` to reproduce detection behavior. The package versions in package.json are placeholders; adjust versions to match your environment.
- If you want, I can run `npm install` and `npx react-router dev` here and paste the logs into this README.
