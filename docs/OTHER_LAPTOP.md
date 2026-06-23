# Run Solar Path on another laptop

You do **not** need Git if you use the ZIP method below.

---

## Easiest: no install at all

Open in any browser:

**https://solar-path.onrender.com/?invite=solarpath-beta-2026**

---

## Method A — Download ZIP (no Git)

1. Open **https://github.com/SyedZain295/solarpath**
2. Click the green **Code** button → **Download ZIP**
3. Unzip the folder (e.g. to `Desktop\solarpath`)
4. Install **Python 3.10+** from https://www.python.org/downloads/  
   - On Windows: check **“Add python.exe to PATH”**
5. Open the unzipped folder, double-click **`SETUP_OTHER_LAPTOP.bat`**

Browser: **http://127.0.0.1:5000**

---

## Method B — Git clone

```powershell
git clone https://github.com/SyedZain295/solarpath.git
cd solarpath
```

Then double-click **`SETUP_OTHER_LAPTOP.bat`** (or **`START.bat`**).

---

## If something fails

| Problem | Fix |
|---------|-----|
| `'python' is not recognized` | Reinstall Python with **Add to PATH** checked |
| `'git' is not recognized` | Use **Method A (ZIP)** instead |
| `pip install failed` | Run: `python -m pip install -r requirements.txt` |
| Blank admin / beta login | Open `.env` and set `ADMIN_TOKEN` and `BETA_ACCESS_PASSWORD` |
| Phones can't reach laptop | Same WiFi + run `EVENT.bat` for the local IP URL |

---

## Copy settings from your main laptop

Copy the `.env` file from your original project folder into the new folder.  
It is **not** on GitHub (private secrets).

Example source: `C:\Users\DELL\Downloads\Solar Website\.env`
