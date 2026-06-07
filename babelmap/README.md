# BabelMap — Cross-Platform Unicode Character Map

Modern rebuild of the BabelSoft BabelMap tool using:

| Layer    | Technology            | Purpose                       |
| -------- | --------------------- | ----------------------------- |
| Shell    | Tauri 2 (Rust)        | Native window, lifecycle      |
| Frontend | Svelte 5 + TypeScript | UI components                 |
| Backend  | Python FastAPI        | Unicode data, glyph rendering |
| Data     | `src/` (existing)     | CJK, Unicode, Mappings, etc.  |

## Project Structure

```
babelmap/
├── src-tauri/           # Tauri Rust shell
│   ├── Cargo.toml
│   ├── tauri.conf.json
│   └── src/main.rs
├── frontend/            # Svelte 5 frontend
│   ├── package.json
│   ├── vite.config.ts
│   ├── index.html
│   └── src/
│       ├── App.svelte          # Root layout
│       ├── lib/
│       │   ├── api.ts          # Backend API client
│       │   ├── types.ts        # TypeScript interfaces
│       │   ├── stores.ts       # Svelte 5 reactive state ($state)
│       │   └── components/
│       │       ├── MenuBar.svelte
│       │       ├── PlaneTabs.svelte
│       │       ├── CharacterGrid.svelte
│       │       ├── CharCell.svelte
│       │       ├── GridNav.svelte
│       │       ├── FontToolbar.svelte
│       │       ├── BottomPanel.svelte
│       │       └── StatusBar.svelte
└── backend/             # Python FastAPI server
    ├── server.py
    ├── requirements.txt
    └── __init__.py
```

## Getting Started

### 1. Install frontend dependencies

```bash
cd babelmap/frontend
npm install
```

### 2. Install backend dependencies

```bash
cd babelmap/backend
pip install -r requirements.txt
```

### 3. Start the backend (terminal 1)

```bash
python babelmap/backend/server.py
# → http://127.0.0.1:17890
```

### 4. Start the frontend dev server (terminal 2)

```bash
cd babelmap/frontend
npm run dev
# → http://localhost:5173
```

### 5. Run tests for backend

```bash
python -m pytest babelsoft-py/tests/ -x -q
```

## API Endpoints

| Endpoint                                    | Description                       |
| ------------------------------------------- | --------------------------------- |
| `GET /api/health`                           | Health check                      |
| `GET /api/planes`                           | List all Unicode planes           |
| `GET /api/blocks`                           | List all Unicode blocks           |
| `GET /api/blocks/{plane}`                   | Blocks for a specific plane       |
| `GET /api/grid/{plane}?scroll=&font=&size=` | Character grid (8×16 cells)       |
| `GET /api/grid/{plane}/goto/{cp}`           | Jump to codepoint                 |
| `GET /api/grid/{plane}/block/{name}`        | Jump to block                     |
| `GET /api/grid/{plane}/navigate?direction=` | Navigate grid                     |
| `GET /api/codepoint/{cp}`                   | Detailed codepoint info           |
| `GET /api/glyph/{cp}?font=&size=`           | Glyph PNG as base64               |
| `GET /api/search/name?q=`                   | Search characters by name         |
| `GET /api/fonts`                            | List available fonts              |
| `GET /api/convert/edit?text=&mode=`         | Convert edit buffer between modes |

## Tauri Build (Windows/macOS/Linux)

```bash
# Prerequisites: Rust, Node.js, Python 3
cd babelmap
npm run tauri dev    # Development with hot-reload
npm run tauri build  # Production installer
```
