import threading
from types import SimpleNamespace

import furigana_ocr.core.dictionary as dictionary


def test_dictionary_lookup_uses_thread_local_jamdict(monkeypatch):
    instances: list[int] = []
    calls: list[tuple[int, str, bool]] = []

    class DummyJamdict:
        def __init__(self) -> None:
            self._local = threading.local()
            # Mimic jamdict initialising thread-local database handles during
            # construction.  Using the instance from another thread would
            # normally trigger the AttributeError observed in production.
            self._local.srcdc = True
            instances.append(threading.get_ident())

        def lookup(self, surface: str, strict: bool = True):  # pragma: no cover - type stub
            if not hasattr(self._local, "srcdc"):
                raise AttributeError("'_thread._local' object has no attribute 'srcdc'")
            calls.append((threading.get_ident(), surface, strict))
            return SimpleNamespace(entries=[])

    monkeypatch.setattr(dictionary, "Jamdict", DummyJamdict)

    lookup = dictionary.DictionaryLookup()

    # First call should create a client for the main thread.
    assert lookup.lookup("猫") == []
    assert len(instances) == 1
    assert calls[-1][1] == "猫"

    # Simulate the thread-local attribute being cleared which previously caused
    # an AttributeError.  The lookup should recover by instantiating a new
    # client for the current thread.
    client = lookup._thread_local.jamdict
    del client._local.srcdc
    assert lookup.lookup("狐") == []
    assert len(instances) == 2
    assert calls[-1][1] == "狐"

    errors: list[BaseException] = []

    def worker() -> None:
        try:
            lookup.lookup("犬")
        except BaseException as exc:  # pragma: no cover - diagnostic helper
            errors.append(exc)

    thread = threading.Thread(target=worker)
    thread.start()
    thread.join()

    assert not errors
    # A separate Jamdict instance should be created for the worker thread.
    assert len(instances) == 3
    assert calls[-1][1] == "犬"
