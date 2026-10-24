import shutil

from .api_client import CredentialStore
from .database.local_database import get_default_data_dir


def validate_uninstall() -> bool:
    return input("Are you sure you want to uninstall? (yes/no): ").strip().lower() in {
        "yes",
        "y",
    }


def main() -> None:
    if not validate_uninstall():
        return

    print("Uninstalling...")
    data_dir = get_default_data_dir()
    print(f"Removing data directory: {data_dir}")
    CredentialStore().clear_token()
    if data_dir.exists():
        shutil.rmtree(data_dir)
    print("Uninstallation complete.")


if __name__ == "__main__":
    main()
