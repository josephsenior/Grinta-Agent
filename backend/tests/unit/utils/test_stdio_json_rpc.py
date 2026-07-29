"""Tests for shared Content-Length JSON framing."""

from __future__ import annotations

from backend.utils.http.stdio_json_rpc import (
    encode_json_rpc_message,
    feed_content_length_buffer,
    parse_content_length_json_messages,
)


def test_parse_single_message() -> None:
    body = '{"jsonrpc":"2.0","id":1}'
    blob = f'Content-Length: {len(body.encode("utf-8"))}\r\n\r\n{body}'
    out = parse_content_length_json_messages(blob)
    assert len(out) == 1
    assert out[0]['jsonrpc'] == '2.0'
    assert out[0]['id'] == 1


def test_parse_two_messages() -> None:
    m1 = '{"a":1}'
    m2 = '{"b":2}'
    blob = (
        f'Content-Length: {len(m1.encode("utf-8"))}\r\n\r\n{m1}'
        f'Content-Length: {len(m2.encode("utf-8"))}\r\n\r\n{m2}'
    )
    out = parse_content_length_json_messages(blob)
    assert out == [{'a': 1}, {'b': 2}]


def test_parse_skips_non_content_length_noise() -> None:
    body = '{"x":true}'
    blob = f'noise Content-Length: {len(body.encode("utf-8"))}\r\n\r\n{body}'
    out = parse_content_length_json_messages(blob)
    assert out == [{'x': True}]


def test_parse_invalid_length_value() -> None:
    blob = 'Content-Length: invalid\r\n\r\nContent-Length: 8\r\n\r\n{"a": 1}'
    out = parse_content_length_json_messages(blob)
    assert out == [{'a': 1}]


def test_encode_json_rpc_message() -> None:
    msg = {'jsonrpc': '2.0', 'method': 'test', 'params': {'key': 'val'}}
    encoded = encode_json_rpc_message(msg)
    assert isinstance(encoded, bytes)
    assert encoded.startswith(b'Content-Length: ')
    assert b'\r\n\r\n' in encoded

    # Verify feed_content_length_buffer can decode it back
    msgs, leftover = feed_content_length_buffer(encoded)
    assert msgs == [msg]
    assert leftover == b''


def test_feed_content_length_buffer_multiple_and_partial() -> None:
    m1 = {'id': 1, 'result': 'ok'}
    m2 = {'id': 2, 'result': 'done'}
    e1 = encode_json_rpc_message(m1)
    e2 = encode_json_rpc_message(m2)

    # Full e1 + partial e2
    partial_buf = e1 + e2[:15]
    msgs, leftover = feed_content_length_buffer(partial_buf)
    assert msgs == [m1]
    assert leftover == e2[:15]

    # Now append rest of e2
    msgs2, leftover2 = feed_content_length_buffer(leftover + e2[15:])
    assert msgs2 == [m2]
    assert leftover2 == b''


def test_feed_content_length_buffer_error_branches() -> None:
    # Invalid length int
    buf1 = b'Content-Length: bad\r\n\r\nContent-Length: 8\r\n\r\n{"a": 1}'
    msgs1, leftover1 = feed_content_length_buffer(buf1)
    assert msgs1 == [{'a': 1}]

    # Incomplete headers / no sep
    assert feed_content_length_buffer(b'Content-Length: 10') == (
        [],
        b'Content-Length: 10',
    )
    assert feed_content_length_buffer(b'Content-Length: 10\r\n') == (
        [],
        b'Content-Length: 10\r\n',
    )

    # Incomplete body
    buf_inc = b'Content-Length: 100\r\n\r\nshort'
    assert feed_content_length_buffer(buf_inc) == ([], buf_inc)

    # Invalid JSON payload
    buf_invalid = b'Content-Length: 9\r\n\r\n{invalid}'
    msgs_inv, leftover_inv = feed_content_length_buffer(buf_invalid)
    assert msgs_inv == []
    assert leftover_inv == b''
