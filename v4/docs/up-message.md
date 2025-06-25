# Streams

The client can send a message the server:

    {
        text: "hello"
        _meta: 'foo'
    }

The `_meta` key is a unique value, to track the inbound response from the server. The receipt provides an `origin_id`, with the associated message

    {
        accept: 36
        code: 1111
        ok: true
        origin_id: "fa09ac4c-ea19-4678-81c9-3ce60787f9f0"
        _meta: "foo"
    }

The origin_id remains through all incoming messages. code `1111` denotes server receipt accepts the message of `36` bytes.

Next message denotes a stream:

    {
        "meta": {
            "origin_id": "fa09ac4c-ea19-4678-81c9-3ce60787f9f0"
        },
        "code": 1515,
        "text": "open stream request",
        "origin_id": "2d8daa98-646b-4514-a4e6-5ad4cb93b166"
    }

The `meta` contains the origin of the starter message. The new origin is bound to the incoming stream

    {"raw": "Hello", "origin_id": "fa09ac4c-ea19-4678-81c9-3ce60787f9f0"}
    {"raw": "!", "origin_id": "fa09ac4c-ea19-4678-81c9-3ce60787f9f0"}
    ...
    {"raw": "", "origin_id": "fa09ac4c-ea19-4678-81c9-3ce60787f9f0"}

The stream will close:

    {
        "origin_id": "fa09ac4c-ea19-4678-81c9-3ce60787f9f0",
        "code": 1516, "text": "close stream request"
    }

And can return a finished request

    {
        "result": {
            "model": "smollm2:360m-instruct-fp16", "created_at": "2025-06-25T02:10:37.9715934Z",
            "message": {"role": "assistant", "content": "Hello! How can I help you today?"
        },
        "done_reason": "stop",
        "done": true,
        "total_duration": 384769400,
        "load_duration": 8212300,
        "prompt_eval_count": 31,
        "prompt_eval_duration": 1534500,
        "eval_count": 10,
        "eval_duration": 374510100},
        "origin_id": "fa09ac4c-ea19-4678-81c9-3ce60787f9f0",
        "session_id": "75a9c634-b2dc-437d-86b8-b296b7f14990",
        "message_id": "66ab3c9f-e100-4a6c-8f99-e50ec3b67ee6"
    }


---

If there is no responder on the stream, nothing happens after the receipt:

    {"text":"hi","_meta":"0.0o9e6tpbk3"}
    {"ok": true, "code": 1111, "accept": 36, "origin_id": "bcdfa23b-d74d-4738-8782-f520e6b2047f", "_meta": "0.0o9e6tpbk3"}
    # no messages...

