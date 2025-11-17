from google.protobuf import empty_pb2 as _empty_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class SessionInfo(_message.Message):
    __slots__ = ("session_id", "user_id", "repository", "branch", "labels")
    class LabelsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    REPOSITORY_FIELD_NUMBER: _ClassVar[int]
    BRANCH_FIELD_NUMBER: _ClassVar[int]
    LABELS_FIELD_NUMBER: _ClassVar[int]
    session_id: str
    user_id: str
    repository: str
    branch: str
    labels: _containers.ScalarMap[str, str]
    def __init__(self, session_id: _Optional[str] = ..., user_id: _Optional[str] = ..., repository: _Optional[str] = ..., branch: _Optional[str] = ..., labels: _Optional[_Mapping[str, str]] = ...) -> None: ...

class StartSessionRequest(_message.Message):
    __slots__ = ("user_id", "repository", "branch", "labels", "session_id")
    class LabelsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    REPOSITORY_FIELD_NUMBER: _ClassVar[int]
    BRANCH_FIELD_NUMBER: _ClassVar[int]
    LABELS_FIELD_NUMBER: _ClassVar[int]
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    user_id: str
    repository: str
    branch: str
    labels: _containers.ScalarMap[str, str]
    session_id: str
    def __init__(self, user_id: _Optional[str] = ..., repository: _Optional[str] = ..., branch: _Optional[str] = ..., labels: _Optional[_Mapping[str, str]] = ..., session_id: _Optional[str] = ...) -> None: ...

class EventEnvelope(_message.Message):
    __slots__ = ("session_id", "event_id", "event_type", "payload", "trace_id", "metadata")
    class MetadataEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    EVENT_ID_FIELD_NUMBER: _ClassVar[int]
    EVENT_TYPE_FIELD_NUMBER: _ClassVar[int]
    PAYLOAD_FIELD_NUMBER: _ClassVar[int]
    TRACE_ID_FIELD_NUMBER: _ClassVar[int]
    METADATA_FIELD_NUMBER: _ClassVar[int]
    session_id: str
    event_id: int
    event_type: str
    payload: bytes
    trace_id: str
    metadata: _containers.ScalarMap[str, str]
    def __init__(self, session_id: _Optional[str] = ..., event_id: _Optional[int] = ..., event_type: _Optional[str] = ..., payload: _Optional[bytes] = ..., trace_id: _Optional[str] = ..., metadata: _Optional[_Mapping[str, str]] = ...) -> None: ...

class PublishEventRequest(_message.Message):
    __slots__ = ("event",)
    EVENT_FIELD_NUMBER: _ClassVar[int]
    event: EventEnvelope
    def __init__(self, event: _Optional[_Union[EventEnvelope, _Mapping]] = ...) -> None: ...

class SubscribeRequest(_message.Message):
    __slots__ = ("session_id", "event_types", "cursor")
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    EVENT_TYPES_FIELD_NUMBER: _ClassVar[int]
    CURSOR_FIELD_NUMBER: _ClassVar[int]
    session_id: str
    event_types: _containers.RepeatedScalarFieldContainer[str]
    cursor: int
    def __init__(self, session_id: _Optional[str] = ..., event_types: _Optional[_Iterable[str]] = ..., cursor: _Optional[int] = ...) -> None: ...

class ReplayRequest(_message.Message):
    __slots__ = ("session_id", "from_cursor", "limit")
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    FROM_CURSOR_FIELD_NUMBER: _ClassVar[int]
    LIMIT_FIELD_NUMBER: _ClassVar[int]
    session_id: str
    from_cursor: int
    limit: int
    def __init__(self, session_id: _Optional[str] = ..., from_cursor: _Optional[int] = ..., limit: _Optional[int] = ...) -> None: ...

class ReplayChunk(_message.Message):
    __slots__ = ("events", "next_cursor", "has_more")
    EVENTS_FIELD_NUMBER: _ClassVar[int]
    NEXT_CURSOR_FIELD_NUMBER: _ClassVar[int]
    HAS_MORE_FIELD_NUMBER: _ClassVar[int]
    events: _containers.RepeatedCompositeFieldContainer[EventEnvelope]
    next_cursor: int
    has_more: bool
    def __init__(self, events: _Optional[_Iterable[_Union[EventEnvelope, _Mapping]]] = ..., next_cursor: _Optional[int] = ..., has_more: bool = ...) -> None: ...
