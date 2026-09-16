# Setup guide

## 1. Create the special repo
On GitHub, create a **new public repository named exactly `samyogsilwal61-svg`**
(same as your username). GitHub treats a repo with this exact name specially —
its README is shown at the top of your profile page.

## 2. Upload these files
Push everything in this folder to that repo's `main` branch, keeping the structure:
```
samyogsilwal61-svg/
├── .github/workflows/main.yml
├── cache/               (empty folder is fine, the script fills it in)
├── README.md
├── today.py
├── build_svg.py
├── img_to_ascii.py
├── ascii_art.txt
├── requirements.txt
├── dark_mode.svg
└── light_mode.svg
```

## 3. Create a Personal Access Token (PAT)
Go to **Settings → Developer settings → Personal access tokens → Fine-grained tokens → Generate new token**.
- Resource owner: yourself
- Repository access: **All repositories** (so it can walk every repo you've contributed to)
- Permissions needed:
  - Account permissions: **Followers** (read), **Starring** (read)
  - Repository permissions: **Contents** (read), **Metadata** (read), **Commit statuses** (read)
- Generate it and **copy the token now** — GitHub only shows it once.

## 4. Add the token as a repo secret
In the `samyogsilwal61-svg` repo: **Settings → Secrets and variables → Actions → New repository secret**
- Name: `ACCESS_TOKEN`
- Value: paste the token from step 3

## 5. Run it
Go to the **Actions** tab → "Update profile README" → **Run workflow** to trigger it manually the first
time. After that it runs automatically every day (see the `cron` line in `main.yml` — times are UTC).

The first run will be slow (it walks every commit in every repo you own/collaborate on to count
lines of code). After that, `cache/` means it only re-walks a repo if its commit count changed.

## Changing your ASCII art anytime
`ascii_art.txt` is a **drop zone** — whatever plain text is in that file becomes the art on
the card, at whatever size it happens to be. The layout auto-fits to it, so you never touch
`build_svg.py` for this.

**Using an online ASCII-art generator (easiest):**
1. Generate your art at a site like [asciiart.club](https://asciiart.club),
   [ascii-image-converter](https://github.com/TheZoraiz/ascii-image-converter), or any
   photo-to-ASCII tool — choose **plain text** output, not HTML/ANSI-colored.
2. Select all the generated text and paste it into `ascii_art.txt`, replacing everything
   that was there. Save.
3. Run:
   ```bash
   python3 build_svg.py
   ```
4. Commit and push the updated `ascii_art.txt`, `dark_mode.svg`, and `light_mode.svg`.

That's it — width, height, and the info column's position all recompute automatically, so
art of any size or shape will fit. The loader also cleans up common copy-paste issues
(Windows line endings, tabs, stray blank lines) so a messy paste won't break the layout.

**Using your own photo instead:** `img_to_ascii.py` is still there if you'd rather generate
the art from a photo yourself:
```bash
python3 img_to_ascii.py your_new_photo.png ascii_art.txt 90
python3 build_svg.py
```
The last number (90) is the character width — try 70–110 depending on how much detail you want.

## Editing your bio details
Open `build_svg.py` and edit the `STATIC_BLOCKS` list near the top (OS, Host, IDE, languages,
hobbies, contact info) — then re-run `python3 build_svg.py` and commit the two SVGs.
**Don't hand-edit the SVGs directly** for text changes — `today.py` only knows how to update the
numeric stat fields (ids like `repo_data`, `star_data`, etc.), so any other change belongs in
`build_svg.py`, which regenerates the whole layout consistently.
