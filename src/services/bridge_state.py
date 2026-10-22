"""WMI composition of Kernel-owned durable adapter state; no local replay engine."""
import os
from events.bridge_state import BridgeState

_state = None
_path = None


def get_bridge_state():
    global _state, _path
    path = os.getenv('UNIIMENTE_BRIDGE_STATE_PATH', '')
    if not path:
        raise ValueError('UNIIMENTE_BRIDGE_STATE_PATH required')
    if _state is not None and _path != path:
        close_bridge_state()
    if _state is None:
        _state = BridgeState(path, os.getenv('UNIIMENTE_CONSTITUTION_HASH', ''),
            owner='wealthmachine', legal_principal=os.getenv('UNIIMENTE_LEGAL_PRINCIPAL', ''))
        _path = path
    return _state


def close_bridge_state():
    global _state, _path
    if _state is not None:
        _state.close()
    _state = _path = None
