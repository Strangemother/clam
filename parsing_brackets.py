def extract_outer_brackets(text):
    results = []
    stack = []
    start = None

    for i, char in enumerate(text):
        if char == '[':
            if not stack:  # Outer bracket start
                start = i
            stack.append('[')
            continue
        if char == ']':
            if not stack:
                continue
            stack.pop()
            if not stack and start is not None:
                # Completed an outer bracketed section
                results.append(text[start:i+1])
                start = None
    return results

# Test
text = """this is a sentence with some [square square] content branckets.
Multiple [here] and [here]. And a torture test of nested
brackets [with content [frog] content ] milkshake and oprah but not this missing open close]."""

print('\n'.join(extract_outer_brackets(text)))
