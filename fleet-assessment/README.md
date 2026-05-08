# Fleet Electrification Assessment
### EV Fleet Readiness & ROI Platform

A professional sales tool for EV charging installers. Guides salespeople through a complete fleet assessment, calculates ROI for the client, and shows your private profit margins.

---

## Features

- **8-step guided questionnaire** — company profile, operations, electrical infra, costs, growth
- **EN / PT / ES** — full multilingual support, switchable at any time
- **Client report** — payback period, annual savings, 5-year cost comparison chart, infrastructure recommendation
- **Private margins tab** — your install profit, kWh markup, Year 1/3/5 cumulative profit
- **Live kWh slider** — adjust your rate and see real-time impact on client payback
- **Auto PDF export** — branded report with charts for the client
- **Saved assessments dashboard** — all past assessments stored in Supabase, searchable

---

## Tech Stack

| Layer | Service | Cost |
|---|---|---|
| Frontend | React + Vite | Free |
| Hosting | Vercel | Free |
| Database | Supabase (PostgreSQL) | Free tier |
| PDF | jsPDF + html2canvas | Open source |

---

## Setup — Step by Step

### 1. Install dependencies

```bash
npm install
```

### 2. Create your Supabase project

1. Go to [supabase.com](https://supabase.com) and create a free account
2. Click **New Project** — give it a name (e.g. `fleet-assessment`)
3. Wait for the project to initialize (~2 min)
4. Go to **SQL Editor** → **New Query**
5. Paste the contents of `supabase-schema.sql` and click **Run**
6. Go to **Settings** → **API**
7. Copy your **Project URL** and **anon / public key**

### 3. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` and fill in your Supabase credentials:

```
VITE_SUPABASE_URL=https://your-project-id.supabase.co
VITE_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### 4. Run locally

```bash
npm run dev
```

Open [http://localhost:5173](http://localhost:5173)

---

## Deploy to Vercel (free)

### Option A — Vercel CLI (fastest)

```bash
npm install -g vercel
vercel
```

Follow the prompts. When asked about environment variables, add:
- `VITE_SUPABASE_URL`
- `VITE_SUPABASE_ANON_KEY`

### Option B — GitHub + Vercel dashboard

1. Push this project to a GitHub repo
2. Go to [vercel.com](https://vercel.com) → **New Project** → Import from GitHub
3. Add your environment variables in the Vercel dashboard under **Settings → Environment Variables**
4. Click **Deploy**

Your app will be live at `https://your-project.vercel.app`

---

## Custom Domain

In Vercel dashboard → **Settings** → **Domains** → add your domain.

---

## Project Structure

```
src/
├── App.jsx                  # Main app, routing between views
├── main.jsx                 # React entry point
├── index.css                # Global styles
├── i18n/
│   └── translations.js      # EN / PT / ES strings
├── lib/
│   ├── supabase.js          # Database CRUD operations
│   ├── calc.js              # All financial calculations
│   └── pdf.js               # PDF generation
└── components/
    ├── Header.jsx            # App header + language switcher
    ├── UI.jsx                # Shared UI primitives
    ├── AssessmentForm.jsx    # 7-step form (steps 0–6)
    ├── Results.jsx           # Client report + private margins
    └── Dashboard.jsx         # Saved assessments list
```

---

## Phase 2 — Shareable Client Links (coming next)

To let a salesperson send a link for the client to fill on their own:

1. Generate a unique token and store it in Supabase with the salesperson's ID
2. Create a public route `/assess/:token` that shows only the client-facing form (no margins)
3. On submission, save to Supabase and email the salesperson

This requires adding Supabase Auth — reach out for the Phase 2 code extension.

---

## Customization

- **Default kWh rate**: edit `yourKwhRate: 0.22` in `AssessmentForm.jsx`
- **Default EV benchmarks**: edit placeholders in step 4 of the form
- **PDF branding**: edit `src/lib/pdf.js` — add your logo as base64 or change colors
- **Add a new language**: add a new key to `src/i18n/translations.js`

---

## Support

Built with React 18, Vite 5, Chart.js 4, jsPDF 2, Supabase JS v2.
