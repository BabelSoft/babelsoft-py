"""Exception sets for the backend's best-effort probes.

The backend reads untrusted bytes: fonts the user installed, upstream Unicode
data files, and optional native shapers.  Every probe built on them is
deliberately best-effort — a failure means "no answer for this input", never
"this request is broken" — so the handlers in this package do not let such a
failure escape as an HTTP 500.

Most of the libraries involved are C extensions (fontTools, FreeType,
HarfBuzz, Graphite, Yudit, zlib, brotli).  Their Python bindings report
failures through their own exception classes (``TTLibError``, ``FT_Exception``,
``HarfBuzzError``, ``YuditError`` …), which are *not* subclasses of the
standard ones, so :data:`PROBE_ERRORS` merges the standard families with every
exception class the installed engines define.

Anything *not* listed (``MemoryError``, ``RecursionError``,
``KeyboardInterrupt``, ``SystemExit`` …) is a real problem and is meant to
propagate.
"""

import importlib
import logging
import struct
import zlib

logger = logging.getLogger(__name__)

#: Modules whose own exception classes count as probe failures.  They are
#: imported once, here: the backend needs them as soon as a font or a shaping
#: engine is touched, and a missing or broken native library must not break the
#: import of the package that guards against its errors.
_ENGINE_MODULES: tuple[str, ...] = (
    "fontTools.ttLib",
    "freetype",
    "uharfbuzz",
    "brotli",
    "pyyudit",
    "pygraphite2",
    "pyusp",
    "pydwshape",
    "pyharfrust2",
)


def _engine_error_types() -> tuple[type[BaseException], ...]:
    """Every exception class defined by an installed engine (skips absent ones)."""
    found: list[type[BaseException]] = []
    for module_name in _ENGINE_MODULES:
        try:
            module = importlib.import_module(module_name)
        except BaseException:
            logger.debug("engine %s is unavailable", module_name, exc_info=True)
            continue
        root = module_name.split(".")[0]
        for value in vars(module).values():
            if (
                isinstance(value, type)
                and issubclass(value, BaseException)
                and getattr(value, "__module__", "").split(".")[0] == root
                and value not in found
            ):
                found.append(value)
    return tuple(found)


#: Failures of a font/Unicode probe: malformed or unreadable input, a missing
#: optional dependency, a native shaper that refused the run, or a bug in the
#: data itself.
PROBE_ERRORS: tuple[type[BaseException], ...] = (
    OSError,  # file missing / unreadable / short read
    ImportError,  # optional native module not installed
    RuntimeError,  # libraries that report through RuntimeError
    ValueError,  # bad hex, bad JSON, bad codec (UnicodeDecodeError is a subclass)
    TypeError,  # unexpected object shape coming out of fontTools
    KeyError,  # font table / name record absent
    IndexError,  # truncated binary data
    AttributeError,  # fontTools object lacking the expected sub-table
    struct.error,  # truncated sfnt header
    zlib.error,  # corrupt compressed table
) + _engine_error_types()
