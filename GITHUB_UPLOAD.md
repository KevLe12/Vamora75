# Uploading Vamora75 to GitHub

The prepared upload copy is `GitHub/Vamora75` in the original working folder.
Use that copy as the repository root: `README.md`, `PCB/`, `Mechanical/` and
`Source/` should appear directly at the top level on GitHub.

1. Create an empty repository on GitHub (do not initialize it with a README or license).
2. Open a terminal inside the prepared `Vamora75` folder and run:

   ```powershell
   git init
   git add .
   git commit -m "Add Vamora75 revision 1.3 design"
   git branch -M main
   git remote add origin https://github.com/YOUR-USERNAME/YOUR-REPOSITORY.git
   git push -u origin main
   ```

Replace the remote URL with your repository URL. GitHub Desktop can also create
and publish a repository from this folder.

Use Git or GitHub Desktop for the initial upload. Three assembly STEP files exceed
the browser's 25 MiB per-file limit; all included files are below Git's 100 MiB
per-file limit, so this snapshot does not require Git LFS. See
[GitHub's upload documentation](https://docs.github.com/en/repositories/working-with-files/managing-files/adding-a-file-to-a-repository).

## What is included

Editable KiCad projects and local libraries, CAD exports, firmware sources,
generators, manufacturing outputs, renders, reference inputs, validation reports,
and attribution/license notices. `MANIFEST.json` records the included files and
their SHA-256 hashes (excluding itself).

Local archives, Python environments, temporary files, KiCad personal settings and
intermediate build folders are excluded. The original working folder and its
backups remain intact. This copy is a snapshot; later design changes in the working
folder are not automatically copied here.

To regenerate outputs from a fresh clone, follow `Source/README.md` and run the
full build first. `--skip-pcb` and the revision geometry check require intermediate
PCB files created by that build.

## Publication notes

No repository has been published by preparing these files. The design remains a
digitally checked prototype; read `validation/STATUS.md` and
`Manufacturing/FABRICATION.md` before ordering parts.

Keep `ATTRIBUTION.md` and `Licenses/`. No new project-wide license has been chosen
for the team's original work; third-party files retain their existing terms.
