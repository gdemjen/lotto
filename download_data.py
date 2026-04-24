"""
Download the latest lottery CSV files and re-import them into lotto.db.

Sources:
    https://bet.szerencsejatek.hu/cmsfiles/otos.csv
    https://bet.szerencsejatek.hu/cmsfiles/hatos.csv

Usage:
    python download_data.py
"""

import urllib.request
import os
import importlib

FILES = {
    "otos.csv":  "https://bet.szerencsejatek.hu/cmsfiles/otos.csv",
    "hatos.csv": "https://bet.szerencsejatek.hu/cmsfiles/hatos.csv",
}

DIR = os.path.dirname(__file__)


def download(filename: str, url: str):
    dest = os.path.join(DIR, filename)
    print(f"Downloading {filename} ...", end=" ", flush=True)
    urllib.request.urlretrieve(url, dest)
    size = os.path.getsize(dest)
    print(f"done ({size:,} bytes)")


def reimport(module_name: str):
    """Run the import script for the given game."""
    print(f"Importing {module_name} ...")
    mod = importlib.import_module(module_name)
    mod.main()


def main():
    # Download both CSV files
    for filename, url in FILES.items():
        download(filename, url)

    print()

    # Re-import both into lotto.db
    reimport("import_otos")
    print()
    reimport("import_hatos")

    print("\nAll done.")


if __name__ == "__main__":
    main()
