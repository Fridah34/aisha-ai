# Enable modern string-based type hinting to prevent version evaluation crashes
from __future__ import annotations

import uuid
from pathlib import Path

# --- CUSTOM PLATFORM ALARM SYSTEMS (EXCEPTIONS) ---

class TenantPathError(ValueError):
    """Triggered when a user tries to break out of their folder or sends a fake path."""
    pass


class TenantNotProvisionedError(FileNotFoundError):
    """Triggered when someone tries to read files before the business folder is created."""
    pass


# --- THE HIGH-SECURITY RESOLVER CLASS ---

class TenantFileResolver:
    def __init__(self, base_dir: Path | str):
        # Lock down the absolute, literal address of the starting root folder on the hard drive
        self.base_dir = Path(base_dir).resolve()

    def _tenant_dir_name(self, business_id: uuid.UUID | str) -> str:
        """Forces the input identifier to be a valid, unguessable UUID string."""
        try:
            # Check if the business_id can be converted into a perfect 36-character UUIDv4
            parsed = uuid.UUID(str(business_id))
        except (ValueError, AttributeError, TypeError):
            # If it's a number like 101 or a malicious text script, sound the alarm!
            raise TenantPathError(f"Invalid tenant identifier: {business_id!r}")
        return str(parsed)

    def tenant_root(self, business_id: uuid.UUID | str) -> Path:
        """Looks for a business's existing folder on the hard drive to read it."""
        # Join the base path with the verified tenant folder name
        candidate = self.base_dir / self._tenant_dir_name(business_id)
        
        # We use .resolve(strict=False) or resolve normal paths safely
        resolved = candidate.resolve()
        
        # Verify that this folder address hasn't escaped our main system base directory
        self._assert_within_base(resolved)
        
        # If the folder doesn't physically exist yet, throw a clean 'Not Provisioned' error
        if not resolved.is_dir():
            raise TenantNotProvisionedError(
                f"No knowledge base directory provisioned for tenant {business_id}"
            )
        return resolved

    def ensure_tenant_root(self, business_id: uuid.UUID | str) -> Path:
        """The Lazy Provisioner: Automatically creates the folder on disk if it is missing."""
        candidate = self.base_dir / self._tenant_dir_name(business_id)
        
        # FIX: Resolve the path FIRST to guarantee security before modifying the filesystem
        resolved = candidate.resolve()
        self._assert_within_base(resolved)
        
        # Now it is mathematically safe to physically create the folder
        resolved.mkdir(parents=True, exist_ok=True)
        return resolved

    def resolve_within_tenant(self, business_id: uuid.UUID | str, relative_path: str) -> Path:
        """Takes a filename and securely maps its path inside the tenant's folder container."""
        # Ensure the tenant folder exists and grab its root path
        root = self.ensure_tenant_root(business_id)

        rel = Path(relative_path)
        # Block users from passing absolute paths starting from the computer's core root (like /etc)
        if rel.is_absolute():
            raise TenantPathError(f"Absolute paths are not allowed: {relative_path!r}")

        # Mix the tenant root with the user's filename and get the absolute final destination
        candidate = (root / rel).resolve()
        
        # THE CORE CAGE: Verify mathematically that this final path lives INSIDE the tenant's root folder
        self._assert_within(candidate, root)
        return candidate

    @staticmethod
    def _assert_within(path: Path, root: Path) -> None:
        """The Path-Escape Trap: Catches and blocks Directory Traversal Attacks (like ../../)."""
        try:
            # Python checks if 'path' can be written as a sub-path relative to the secure 'root'
            path.relative_to(root)
        except ValueError:
            # If the user typed '../../' and tried to jump outside their folder, block them instantly!
            raise TenantPathError(
                f"Resolved path {path} escapes tenant root {root}"
            ) from None

    def _assert_within_base(self, path: Path) -> None:
        """Ensures that the directory cannot escape our global platform base folders."""
        self._assert_within(path, self.base_dir)
