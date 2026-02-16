# RISC-V Membership Search (Static Version)

This is a modern, static version of the RISC-V Membership Verification tool, designed to be deployed as a GitHub Page.

## Features
- **Privacy Focused:** Email addresses are hashed (SHA-256) on the client-side before being checked against the membership database.
- **Automated Updates:** A GitHub Action periodically refreshes the membership data from Groups.io.
- **Modern UI:** Built with React, Tailwind CSS, and Lucide icons using the RISC-V color scheme (Berkeley Blue & California Gold).

## Setup
1.  **Secrets:** Ensure the following secrets are set in your GitHub repository:
    - `GROUPSIO_USER`: Your Groups.io service account email.
    - `GROUPSIO_PASSWORD`: Your Groups.io service account password.
2.  **Deployment:** The project is configured to deploy automatically to GitHub Pages via the workflow in `.github/workflows/deploy.yml`.

## Local Development
```bash
npm install
# To generate dummy data for testing
python3 generate_data.py
# To start the dev server
npm run dev
```
