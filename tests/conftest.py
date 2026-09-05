import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path = [p for p in sys.path if Path(p).resolve() != PROJECT_ROOT.parent.parent.resolve()]
if str(PROJECT_ROOT) in sys.path:
    sys.path.remove(str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT))
for mod in list(sys.modules.keys()):
    if mod == 'mcp' or mod.startswith('mcp.'):
        del sys.modules[mod]

