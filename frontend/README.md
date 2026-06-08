# AISHA AI — Frontend

> React dashboard for the AISHA AI WhatsApp sales assistant.  
> Built with **React + Vite + Tailwind CSS v4**

---

## Tech Stack

| Tool | Version | Purpose |
|---|---|---|
| React | 19.x | UI framework |
| Vite | 6.x | Build tool and dev server |
| Tailwind CSS | 4.x | Utility-first styling |
| @tailwindcss/vite | 4.x | Tailwind's official Vite plugin (replaces PostCSS setup) |

---

## Prerequisites

Make sure you have these installed before anything else.  
Run each command to verify:

```bash
node --version      # Should be v18 or higher
npm --version       # Should be v9 or higher
```

If you don't have Node.js, download it from https://nodejs.org (choose the LTS version).

---

## First-Time Setup (Clone → Run)

### 1. Clone the repository

```bash
git clone https://github.com/YOUR-USERNAME/aisha-ai.git
cd aisha-ai
```

### 2. Create your own branch from dev

**Never work directly on `dev` or `main`.**  
Always branch off `dev` and name your branch after yourself:

```bash
git checkout dev
git pull origin dev
git checkout -b yourname/feature-name
```

Example: `git checkout -b alice/auth-ui`

### 3. Install frontend dependencies

```bash
cd frontend
npm install
```

This reads `package.json` and installs everything listed there —  
React, Vite, Tailwind, and all other packages. You only need to run this once  
(or again if `package.json` changes after a teammate adds a new package).

### 4. Start the development server

```bash
npm run dev
```

Open your browser at **http://localhost:5173**  
The page hot-reloads automatically every time you save a file — no manual refresh needed.

---

## Tailwind CSS v4 — Important Note

This project uses **Tailwind CSS v4**, which works differently from v3.  
Do NOT follow v3 tutorials that tell you to run `npx tailwindcss init`.  
That command does not exist in v4 and will throw an error.

**How v4 is configured in this project:**
```
Bash 
npm install -D @tailwindcss/vite
```

Tailwind is set up via the Vite plugin — no `tailwind.config.js` or `postcss.config.js` needed.

`vite.config.js`:
```js
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
  ],
})
```

`src/index.css`:
```css
@import "tailwindcss";
```

That is the complete Tailwind setup. You use Tailwind classes in JSX exactly the same way as v3 — only the configuration changed.

---

## Folder Structure

```
frontend/
├── public/             # Static assets (favicon, images)
├── src/
│   ├── assets/         # Images, icons used in components
│   ├── components/     # Reusable UI components (Button, Card, Modal...)
│   ├── pages/          # Full page components (Dashboard, Login, Orders...)
│   ├── App.jsx         # Root component — routing lives here
│   └── index.css       # Global styles — only contains @import "tailwindcss"
├── index.html          # HTML entry point
├── vite.config.js      # Vite + Tailwind plugin configuration
└── package.json        # Dependencies and scripts
```

> **Note:** `components/` and `pages/` folders will be created as features are built.  
> Do not create them empty — Git ignores empty folders.

---

## Available Scripts

Run these from inside the `frontend/` directory:

```bash
npm run dev        # Start development server at localhost:5173
npm run build      # Build for production (output goes to dist/)
npm run preview    # Preview the production build locally
```

---

## Branch & PR Workflow

This is the workflow every team member follows every time:

```
1. Work on your branch        →  git add . && git commit -m "feat: ..."
2. Push your branch           →  git push origin yourname/feature-name
3. Open a PR on GitHub        →  base: dev ← compare: yourname/feature-name
4. Teammate reviews and approves
5. Merge into dev
6. Pull dev locally           →  git checkout dev && git pull origin dev
7. Branch off dev again for next feature
```

**Commit message format — please follow this:**

```
feat: add product listing page
fix: correct broken navigation link
chore: update dependencies
refactor: restructure components folder
docs: update README with new setup steps
```

---

## If a Teammate Adds a New npm Package

After pulling their changes, always run:
npm install -D @tailwindcss/vite
```bash
npm install
```

This syncs your local `node_modules` with the updated `package.json`.  
If you skip this, you'll get import errors for packages on their machine but not yours.

---

## Current Status (Week 1 — Scaffolding)

- [x] React + Vite initialized
- [x] Tailwind CSS v4 configured via Vite plugin
- [x] Default Vite boilerplate cleaned up
- [x] Base `App.jsx` created with AISHA placeholder
- [ ] Routing setup (React Router) — Week 2
- [ ] Authentication pages (Login, Register) — Week 2
- [ ] Dashboard layout — Week 3+

---

*Update this README when you complete a feature. Add it to the checklist above.*npm install -D @tailwindcss/vite