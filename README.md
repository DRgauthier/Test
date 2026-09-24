# React + Vite

This template provides a minimal setup to get React working in Vite with HMR and some Oxlint rules.

Currently, two official plugins are available:

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react) uses [Oxc](https://oxc.rs)
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react-swc) uses [SWC](https://swc.rs/)

## React Compiler

The React Compiler is not enabled on this template because of its impact on dev & build performances. To add it, see [this documentation](https://react.dev/learn/react-compiler/installation).

## Expanding the Oxlint configuration

If you are developing a production application, we recommend using TypeScript with type-aware lint rules enabled. Check out the [TS template](https://github.com/vitejs/vite/tree/main/packages/create-vite/template-react-ts) for information on how to integrate TypeScript and Oxlint's TypeScript related rules in your project.

## GitHub Pages Deployment

This project uses a custom GitHub Actions workflow (`.github/workflows/deploy.yml`) to build and deploy the Vite application to GitHub Pages.

To ensure the application deploys correctly and does not show a blank white screen (404 error on `/src/main.jsx`), you must configure the repository to use GitHub Actions for deployment instead of the default branch deployment:

1. Go to your repository on GitHub.
2. Navigate to **Settings** > **Pages** (under the "Code and automation" sidebar).
3. Under the **Build and deployment** section, look for the **Source** dropdown.
4. Change the Source from "Deploy from a branch" to **"GitHub Actions"**.

This prevents the default Pages workflow from overriding the compiled build with uncompiled source code.
