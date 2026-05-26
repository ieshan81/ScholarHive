"""Configure LD_LIBRARY_PATH on Nix/Railway for Playwright native deps."""
import glob
import os


def configure_shared_libraries() -> None:
    if os.environ.get("LD_LIBRARY_PATH_CONFIGURED"):
        return
    candidates: list[str] = ["/opt/scholarhive-libs"]
    for pattern in (
        "/nix/store/*-gcc-*-lib/lib",
        "/nix/store/*gcc*/lib",
        "/nix/store/*-stdenv-*/lib",
    ):
        candidates.extend(glob.glob(pattern))
    if candidates:
        existing = os.environ.get("LD_LIBRARY_PATH", "")
        merged = ":".join(dict.fromkeys(candidates + ([existing] if existing else [])))
        os.environ["LD_LIBRARY_PATH"] = merged
    os.environ["LD_LIBRARY_PATH_CONFIGURED"] = "1"
