from simple_bridge import PipRef, SimpleBridge


def test_connect_pips_tracks_downstream_order() -> None:
    bridge = SimpleBridge()

    bridge.easy_connect_pips("alpha", "beta")
    bridge.connect_pips({"id": "alpha", "pip": "out"}, {"id": "gamma", "pip": "in"})

    assert bridge.get_next(PipRef("alpha", "out")) == [
        PipRef("beta", "in"),
        PipRef("gamma", "in"),
    ]
    assert bridge.pip_registry["beta:in"]["from"] == [PipRef("alpha", "out")]
    assert bridge.pip_registry["gamma:in"]["from"] == [PipRef("alpha", "out")]
