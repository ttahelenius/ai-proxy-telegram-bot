import pytest

from ..query import Query

class DummyQuery(Query):
    def history_printer(self, l):
        return [{"role": r, "content": t} for (r, t, i) in l]

def test_history():
    query = DummyQuery()
    history = query.get_history(0)

    history.record("How r u?", [4], None)
    history.record("Fine, how bout u?", [16, 17], 4)
    history.record("Fine ty. Waddup?", [22], 16)

    history.record("Feelin fine!", [23], 17)

    history.record("How r u?", [106], 42) # 42 unrelated

    assert history.get(1) == []

    assert history.get(4) == [{"role": "user", "content": "How r u?"}]
    assert history.get(22) == [{"role": "user", "content": "How r u?"},
                               {"role": "assistant", "content": "Fine, how bout u?"},
                               {"role": "user", "content": "Fine ty. Waddup?"}]
    
    assert history.get(23) == [{"role": "user", "content": "How r u?"},
                               {"role": "assistant", "content": "Fine, how bout u?"},
                               {"role": "user", "content": "Feelin fine!"}]
    
    assert history.get(106) == [{"role": "user", "content": "How r u?"}]

def test_history_rewrite():
    query = DummyQuery()
    history = query.get_history(0)

    history.record("How r u?", [4], None)

    history.record("Fine, how bout u?", [16, 17], 4)

    history.record("Fine ty. Waddup?", [22], 16)

    assert history.get(4) == [{"role": "user", "content": "How r u?"}]
    assert history.get(22) == [{"role": "user", "content": "How r u?"},
                               {"role": "assistant", "content": "Fine, how bout u?"},
                               {"role": "user", "content": "Fine ty. Waddup?"}]

    history.record("How are u?", [4], None)
    history.record("Fine thanks. What's up?", [22], 16)

    assert history.get(4) == [{"role": "user", "content": "How are u?"}]
    assert history.get(22) == [{"role": "user", "content": "How are u?"},
                               {"role": "assistant", "content": "Fine, how bout u?"},
                               {"role": "user", "content": "Fine thanks. What's up?"}]

def test_history_serialization():
    query = DummyQuery()
    history = query.get_history(0)
    history.record("How r u?", [4], None)
    history.record("Fine, how bout u?", [16, 17, 18], 4)
    history.record("Fine ty. Waddup?", [22], 16)

    assert Query.History.serialize(history) == '{"17": 16, "18": 16}|{"4": ["How r u?", null, null], "16": ["Fine, how bout u?", null, 4], "22": ["Fine ty. Waddup?", null, 16]}'
    assert Query.History.deserialize(Query.History.serialize(history)) == (history._history, history.id_table)