import logging
from forge.metasop.memory import MemoryIndex

logger = logging.getLogger(__name__)
m = MemoryIndex(run_id="probe", max_records=50)
for i in range(200):
    content = "value " + "foo " * (i % 10) + "bar " * (i % 7) + f" unique{i % 5}"
    rationale = None
    m.add(
        step_id=str(i),
        role="assistant",
        artifact_hash=None,
        rationale=rationale,
        content=content,
    )
logger.info("final records: %s", len(m._records))
logger.info("unique_terms: %s", len(m._df))
for r in m._records[-5:]:
    logger.info("%s %s", r.step_id, r.content_excerpt[:60])
