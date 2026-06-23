# Free event deploy (no laptop)

Host the app for **$0** using **Render** (free web) + **Neon** (free Postgres).

**Time:** ~30 minutes once. **Cost:** $0.

---

## Part 1 — Neon database (5 min)

1. Go to [neon.tech](https://neon.tech) → sign up (free).
2. **New project** → name it `solarpath` → region **EU (Frankfurt)** if available.
3. Copy the **connection string** (starts with `postgresql://...`).
4. Keep it safe — you’ll paste it into Render in Part 3.

---

## Part 2 — GitHub (10 min)

Git is required to connect Render.

1. Install Git: https://git-scm.com/download/win (default options).
2. Create a repo on GitHub: https://github.com/new  
   - Name: `solarpath` (or any name)  
   - **Private** is fine for a beta  
   - Do **not** add README (you already have one)
3. Open **PowerShell** in your project folder:

```powershell
cd "c:\Users\DELL\Downloads\Solar Website"
git init
git add .
git commit -m "SolarPath closed beta for event"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/solarpath.git
git push -u origin main
```

Replace `YOUR_USERNAME` with your GitHub username. Sign in when Git asks.

**Never commit `.env`** — it’s already in `.gitignore`.

---

## Part 3 — Render web app (10 min)

1. Go to [render.com](https://render.com) → sign up (free, connect GitHub).
2. **New → Blueprint**.
3. Connect the repo you just pushed.
4. When asked for the blueprint file, use **`render.free.yaml`** (not `render.yaml`).
5. After the blueprint is created, open the **solarpath** web service → **Environment** and add:

| Key | Value |
|-----|--------|
| `DATABASE_URL` | *(paste Neon connection string)* |
| `SUPPORT_EMAIL` | `zainhaseeb0716@gmail.com` |
| `BETA_ACCESS_PASSWORD` | `H90Gh_ffx_jlSQ` |
| `BETA_INVITE_TOKENS` | `solarpath-beta-2026` |

`SECRET_KEY` and `ADMIN_TOKEN` are auto-generated — copy **ADMIN_TOKEN** from the env list for `/admin`.

6. **Manual Deploy** (or wait for first deploy to finish).
7. Test: `https://YOUR-APP-NAME.onrender.com/health` → `"status":"ok"`.

---

## Part 4 — Event day

Share this link (QR code on your phone):

```
https://YOUR-APP-NAME.onrender.com/?invite=solarpath-beta-2026
```

Main demo flow:

```
https://YOUR-APP-NAME.onrender.com/calculator
```

**Free tier note:** If nobody uses the site for ~15 minutes, the next visitor may wait **30–60 seconds** while it wakes up. At a busy booth it usually stays warm.

---

## After the event

- View metrics: `/admin` with your `ADMIN_TOKEN`
- Delete the Render service and Neon project if you don’t need them anymore (stays free).

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Build fails | Check Render logs; ensure `requirements.txt` installs |
| `/health` degraded | `DATABASE_URL` wrong — use Neon’s **pooled** connection string if offered |
| 502 on first visit | Wait 60s (cold start) or hit `/health` before the event |
| Beta login loop | Set `BETA_ACCESS_PASSWORD` and `BETA_INVITE_TOKENS` in Render env |
