"""
Model registry and versioning for the ai_engine ML package.

Artifacts (trained models, embedding indexes) are written to a directory tree
that lives **outside** version control::

    <artifacts_dir>/<name>/<version>/model.joblib
    <artifacts_dir>/<name>/<version>/metadata.json
    <artifacts_dir>/<name>/latest          # text file holding the latest version

Every artifact carries a ``metadata.json`` manifest describing the seed,
hyper-parameters, library versions and a dataset fingerprint so a run can be
reproduced and audited.
"""

from __future__ import annotations

import hashlib
import json
import platform
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import get_artifacts_dir

try:  # joblib ships with scikit-learn; fall back to pickle if unavailable.
    import joblib

    _SERIALIZER = "joblib"
except Exception:  # pragma: no cover - exercised only without scikit-learn
    import pickle

    joblib = None  # type: ignore[assignment]
    _SERIALIZER = "pickle"

LATEST_POINTER = "latest"
MODEL_FILENAME = "model.joblib"
METADATA_FILENAME = "metadata.json"


@dataclass(frozen=True)
class Artifact:
    """A saved model plus its manifest metadata.

    Attributes:
        name: Logical model name (e.g. ``"recommender"``).
        version: Version identifier (timestamp-based by default).
        path: Directory containing the artifact.
        metadata: Parsed ``metadata.json`` contents.
    """

    name: str
    version: str
    path: Path
    metadata: dict[str, Any]

    @property
    def model_path(self) -> Path:
        """Absolute path to the serialized model object."""
        return self.path / MODEL_FILENAME


def _library_versions() -> dict[str, str]:
    """Return versions of the libraries relevant to reproducibility."""
    versions = {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
    }
    for module_name in ("numpy", "scipy", "pandas", "sklearn"):
        try:
            module = __import__(module_name)
            versions[module_name] = getattr(module, "__version__", "unknown")
        except Exception:  # pragma: no cover - optional dependency
            versions[module_name] = "not-installed"
    return versions


def _git_commit() -> str:
    """Return the current git commit hash, or ``"unknown"``."""
    head = Path(__file__).resolve().parents[3] / ".git" / "HEAD"
    try:
        text = head.read_text(encoding="utf-8").strip()
        if text.startswith("ref:"):
            ref = text.split(" ", 1)[1].strip()
            ref_path = head.parent / ref
            if ref_path.exists():
                return ref_path.read_text(encoding="utf-8").strip()[:12]
        return text[:12]
    except Exception:  # pragma: no cover - git directory may be absent
        return "unknown"


def _new_version(prefix: str = "v") -> str:
    """Return a sortable, timestamp-based version string."""
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return f"{prefix}{stamp}"


def fingerprint(data: Any) -> str:
    """Return a short, stable hash of a JSON-serializable payload.

    Used to detect whether a dataset changed between training runs.
    """
    payload = json.dumps(data, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:16]


def save_artifact(
    name: str,
    obj: Any,
    metadata: dict[str, Any],
    version: str | None = None,
    artifacts_dir: Path | None = None,
    make_latest: bool = True,
) -> Artifact:
    """Serialize ``obj`` and write it with an enriched manifest.

    Args:
        name: Logical model name.
        obj: Any picklable object (fitted estimator, index, ...).
        metadata: Caller-supplied manifest fields.
        version: Explicit version; timestamp-based when omitted.
        artifacts_dir: Override for the artifacts root (used by tests).
        make_latest: Whether to update the ``latest`` pointer.

    Returns:
        The written :class:`Artifact`.
    """
    root = (artifacts_dir or get_artifacts_dir()) / name
    version = version or _new_version()
    target = root / version
    target.mkdir(parents=True, exist_ok=True)

    manifest = {
        "name": name,
        "version": version,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "serializer": _SERIALIZER,
        "git_commit": _git_commit(),
        "libraries": _library_versions(),
        **metadata,
    }

    if _SERIALIZER == "joblib":
        joblib.dump(obj, target / MODEL_FILENAME)
    else:  # pragma: no cover - exercised only without scikit-learn
        with (target / MODEL_FILENAME).open("wb") as handle:
            pickle.dump(obj, handle)

    (target / METADATA_FILENAME).write_text(
        json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
    )

    if make_latest:
        (root / LATEST_POINTER).write_text(version, encoding="utf-8")

    return Artifact(name=name, version=version, path=target, metadata=manifest)


def list_versions(name: str, artifacts_dir: Path | None = None) -> list[str]:
    """Return saved versions for ``name``, sorted oldest first."""
    root = (artifacts_dir or get_artifacts_dir()) / name
    if not root.exists():
        return []
    return sorted(
        entry.name
        for entry in root.iterdir()
        if entry.is_dir() and (entry / METADATA_FILENAME).exists()
    )


def latest_version(name: str, artifacts_dir: Path | None = None) -> str | None:
    """Return the version flagged as latest, or the newest by name."""
    root = (artifacts_dir or get_artifacts_dir()) / name
    pointer = root / LATEST_POINTER
    if pointer.exists():
        value = pointer.read_text(encoding="utf-8").strip()
        if value and (root / value).exists():
            return value
    versions = list_versions(name, artifacts_dir)
    return versions[-1] if versions else None


def load_artifact(
    name: str,
    version: str | None = None,
    artifacts_dir: Path | None = None,
) -> tuple[Any, dict[str, Any]]:
    """Load a serialized model and its manifest.

    Args:
        name: Logical model name.
        version: Specific version or ``None``/``"latest"`` for the newest.
        artifacts_dir: Override for the artifacts root.

    Returns:
        A ``(model, metadata)`` tuple.

    Raises:
        FileNotFoundError: If no artifact is available.
    """
    root = (artifacts_dir or get_artifacts_dir()) / name
    if version in (None, LATEST_POINTER):
        version = latest_version(name, artifacts_dir)
    if not version:
        raise FileNotFoundError(f"No saved artifact for '{name}'.")

    target = root / version
    model_path = target / MODEL_FILENAME
    if not model_path.exists():
        raise FileNotFoundError(f"Artifact '{name}' version '{version}' is missing.")

    if _SERIALIZER == "joblib":
        model = joblib.load(model_path)
    else:  # pragma: no cover - exercised only without scikit-learn
        with model_path.open("rb") as handle:
            model = pickle.load(handle)

    metadata = json.loads((target / METADATA_FILENAME).read_text(encoding="utf-8"))
    return model, metadata
