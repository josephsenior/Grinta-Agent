from google.protobuf import empty_pb2 as _empty_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class RuntimeHandle(_message.Message):
    __slots__ = ("runtime_id", "session_id", "repository", "branch")
    RUNTIME_ID_FIELD_NUMBER: _ClassVar[int]
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    REPOSITORY_FIELD_NUMBER: _ClassVar[int]
    BRANCH_FIELD_NUMBER: _ClassVar[int]
    runtime_id: str
    session_id: str
    repository: str
    branch: str
    def __init__(self, runtime_id: _Optional[str] = ..., session_id: _Optional[str] = ..., repository: _Optional[str] = ..., branch: _Optional[str] = ...) -> None: ...

class CreateRuntimeRequest(_message.Message):
    __slots__ = ("session_id", "repository", "branch", "repo_root", "user_request")
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    REPOSITORY_FIELD_NUMBER: _ClassVar[int]
    BRANCH_FIELD_NUMBER: _ClassVar[int]
    REPO_ROOT_FIELD_NUMBER: _ClassVar[int]
    USER_REQUEST_FIELD_NUMBER: _ClassVar[int]
    session_id: str
    repository: str
    branch: str
    repo_root: str
    user_request: str
    def __init__(self, session_id: _Optional[str] = ..., repository: _Optional[str] = ..., branch: _Optional[str] = ..., repo_root: _Optional[str] = ..., user_request: _Optional[str] = ...) -> None: ...

class CloseRuntimeRequest(_message.Message):
    __slots__ = ("runtime_id", "wait")
    RUNTIME_ID_FIELD_NUMBER: _ClassVar[int]
    WAIT_FIELD_NUMBER: _ClassVar[int]
    runtime_id: str
    wait: bool
    def __init__(self, runtime_id: _Optional[str] = ..., wait: bool = ...) -> None: ...

class StepOutputSpecMessage(_message.Message):
    __slots__ = ("schema",)
    SCHEMA_FIELD_NUMBER: _ClassVar[int]
    schema: str
    def __init__(self, schema: _Optional[str] = ...) -> None: ...

class SopStepMessage(_message.Message):
    __slots__ = ("id", "role", "task", "outputs", "depends_on", "condition", "lock", "priority")
    ID_FIELD_NUMBER: _ClassVar[int]
    ROLE_FIELD_NUMBER: _ClassVar[int]
    TASK_FIELD_NUMBER: _ClassVar[int]
    OUTPUTS_FIELD_NUMBER: _ClassVar[int]
    DEPENDS_ON_FIELD_NUMBER: _ClassVar[int]
    CONDITION_FIELD_NUMBER: _ClassVar[int]
    LOCK_FIELD_NUMBER: _ClassVar[int]
    PRIORITY_FIELD_NUMBER: _ClassVar[int]
    id: str
    role: str
    task: str
    outputs: StepOutputSpecMessage
    depends_on: _containers.RepeatedScalarFieldContainer[str]
    condition: str
    lock: str
    priority: int
    def __init__(self, id: _Optional[str] = ..., role: _Optional[str] = ..., task: _Optional[str] = ..., outputs: _Optional[_Union[StepOutputSpecMessage, _Mapping]] = ..., depends_on: _Optional[_Iterable[str]] = ..., condition: _Optional[str] = ..., lock: _Optional[str] = ..., priority: _Optional[int] = ...) -> None: ...

class RunStepRequest(_message.Message):
    __slots__ = ("runtime_id", "step", "max_retries", "trace_id")
    RUNTIME_ID_FIELD_NUMBER: _ClassVar[int]
    STEP_FIELD_NUMBER: _ClassVar[int]
    MAX_RETRIES_FIELD_NUMBER: _ClassVar[int]
    TRACE_ID_FIELD_NUMBER: _ClassVar[int]
    runtime_id: str
    step: SopStepMessage
    max_retries: int
    trace_id: str
    def __init__(self, runtime_id: _Optional[str] = ..., step: _Optional[_Union[SopStepMessage, _Mapping]] = ..., max_retries: _Optional[int] = ..., trace_id: _Optional[str] = ...) -> None: ...

class StepUpdate(_message.Message):
    __slots__ = ("runtime_id", "step_id", "update_type", "status", "metadata")
    class MetadataEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    RUNTIME_ID_FIELD_NUMBER: _ClassVar[int]
    STEP_ID_FIELD_NUMBER: _ClassVar[int]
    UPDATE_TYPE_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    METADATA_FIELD_NUMBER: _ClassVar[int]
    runtime_id: str
    step_id: str
    update_type: str
    status: str
    metadata: _containers.ScalarMap[str, str]
    def __init__(self, runtime_id: _Optional[str] = ..., step_id: _Optional[str] = ..., update_type: _Optional[str] = ..., status: _Optional[str] = ..., metadata: _Optional[_Mapping[str, str]] = ...) -> None: ...
