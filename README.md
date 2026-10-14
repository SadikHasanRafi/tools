# Tools Monorepo

This repo is organized as a simple monorepo where each tool is its own app in `apps/`.

There is no shared library layer by default. If you create a new tool, you make a new folder under `apps/` and keep all of its code inside that folder.

## Structure

- `apps/` — each tool lives here as a separate app
  - `apps/scrap-erki/` — Python Selenium scraper
  - `apps/web/` — JavaScript app placeholder

## Rule

Each app is independent:

- one folder = one tool
- one tool = its own code, dependencies, config, and runtime
- no shared package unless you specifically decide to add one later

## Example

```bash
apps/
  scrap-erki/
    scrapper.py
  web/
    package.json
    src/
```

## Running apps

Python tool:

```bash
cd apps/scrap-erki
python3 scrapper.py
```

JavaScript tool:

```bash
cd apps/web
npm install
npm run dev
```
