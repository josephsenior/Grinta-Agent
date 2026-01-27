from forge.events.observation.commands import (
    CmdOutputMetadata,
    CmdOutputObservation,
)


def test_cmd_output_success():
    obs = CmdOutputObservation(
        command="ls",
        content="file1.txt\nfile2.txt",
        metadata=CmdOutputMetadata(exit_code=0),
    )
    assert obs.success is True
    assert obs.error is False
    obs = CmdOutputObservation(
        command="ls",
        content="No such file or directory",
        metadata=CmdOutputMetadata(exit_code=1),
    )
    assert obs.success is False
    assert obs.error is True
