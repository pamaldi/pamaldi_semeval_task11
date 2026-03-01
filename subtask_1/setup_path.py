"""
Add project roots to sys.path so notebooks can import dependent classes.

Dependent modules are copied in lib/ (same folder as this file). This script
adds lib/ to sys.path so imports like "from neurosymbolic_pipeline import ..." work.

Use in the first cell of any notebook in this folder:

    import sys
    from pathlib import Path
    _nb_dir = Path.cwd() / "pamaldi_semeval_11_task1" if (Path.cwd() / "pamaldi_semeval_11_task1").exists() else Path.cwd()
    sys.path.insert(0, str(_nb_dir))
    import setup_path

Then import project modules as usual (e.g. from neurosymbolic_pipeline import ...).
"""

import sys
from pathlib import Path

_THIS_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _THIS_DIR.parent
_LIB = _THIS_DIR / "lib"

# Prefer lib/ (copied dependencies) so the folder is self-contained
if _LIB.exists():
    if str(_LIB) not in sys.path:
        sys.path.insert(0, str(_LIB))
else:
    # Fallback: add repo roots if lib/ is missing
    for _p in [
        _REPO_ROOT,
        _REPO_ROOT / "executed_notebooks",
        _REPO_ROOT / "board_results" / "neurosymbolic",
        _REPO_ROOT / "board_results" / "45_80" / "neurosymbolic",
    ]:
        if _p.exists() and str(_p) not in sys.path:
            sys.path.insert(0, str(_p))

# Optional: add evaluation kit when running official scoring
_eval_kit = _REPO_ROOT / "evaluation_kit" / "task 1 & 3"
if _eval_kit.exists() and str(_eval_kit) not in sys.path:
    sys.path.insert(0, str(_eval_kit))
