# Repository Guidelines

## Project Structure & Module Organization
This repository currently contains project documentation plus Spec Kit scaffolding. The application described in `README.md` is a Next.js launch-site generator. When source files are restored or added, keep the documented layout: `app/api/` for route handlers, `components/` for React UI, `hooks/` for client state, `lib/` for generation, grounding, extraction, and provider wrappers, and `types/` for shared TypeScript types. Keep generated specifications, plans, tasks, and workflow assets under `.specify/`.

## Build, Test, and Development Commands
Use the npm workflow described in `README.md`:

```bash
npm install
cp .env.example .env.local
npm run dev
npm run build
npm test
```

`npm install` installs dependencies. `npm run dev` starts the local Next.js app. `npm run build` should type-check and produce a production build. `npm test` should run the test suite once tests are added.

## Coding Style & Naming Conventions
Use TypeScript for application code. Prefer small, focused modules with descriptive names such as `grounding.ts`, `site-pipeline.ts`, and `profile-extraction.ts`. React components should use PascalCase exports and kebab-case filenames where the existing codebase does, for example `site-wizard.tsx`. Keep API route folder names lowercase and URL-oriented.

## Testing Guidelines
The README notes that automated tests are not present yet. Add tests with each behavioral change once the test framework is available. Name tests after the unit or workflow under test, for example `grounding.test.ts` or `site-pipeline.test.ts`. Cover prompt grounding, HTML post-processing, provider fallbacks, and API route behavior before shipping changes that touch generation.

## Commit & Pull Request Guidelines
Recent history uses short imperative or descriptive subjects, such as `Reset main to README only` and `Initial commit`. Keep commits focused and explain the user-visible change. Pull requests should include a concise summary, linked issue or spec when relevant, environment/configuration notes, and screenshots or generated-site examples for UI changes. Mention any build or test command you could not run.

## Security & Configuration Tips
Do not commit `.env.local`, API keys, generated credentials, or uploaded client files. `OPENROUTER_API_KEY` is the minimum required key; `V0_API_KEY` and `PEXELS_API_KEY` should degrade gracefully when absent.

## Agent-Specific Instructions
This repo includes Spec Kit for Codex. Keep `.agents/skills/` and `.specify/` tracked when Spec Kit is part of the team workflow; they are project scaffolding, not local cache.
