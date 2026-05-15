from prompting_proxy import _lmstudio_model_matches

def test():
    entry = {'loaded_instances': [{'id': 'granite-4.1-8b:2'}]}
    
    # Check 1: Should be True
    res1 = _lmstudio_model_matches(entry, 'granite-4.1-8b')
    print(f"Test 1 (granite-4.1-8b): {res1}")
    assert res1 is True, f"Expected True for granite-4.1-8b, got {res1}"

    # Check 2: Should be False
    res2 = _lmstudio_model_matches(entry, 'other-model')
    print(f"Test 2 (other-model): {res2}")
    assert res2 is False, f"Expected False for other-model, got {res2}"

if __name__ == "__main__":
    try:
        test()
        print("All tests passed!")
    except AssertionError as e:
        print(f"Assertion failed: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")
