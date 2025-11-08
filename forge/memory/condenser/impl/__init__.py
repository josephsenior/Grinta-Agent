"""Concrete condenser implementations used by the memory subsystem."""

from forge.memory.condenser.impl.amortized_forgetting_condenser import (
    AmortizedForgettingCondenser,
)
from forge.memory.condenser.impl.browser_output_condenser import (
    BrowserOutputCondenser,
)
from forge.memory.condenser.impl.conversation_window_condenser import (
    ConversationWindowCondenser,
)
from forge.memory.condenser.impl.llm_attention_condenser import (
    ImportantEventSelection,
    LLMAttentionCondenser,
)
from forge.memory.condenser.impl.llm_summarizing_condenser import (
    LLMSummarizingCondenser,
)
from forge.memory.condenser.impl.no_op_condenser import NoOpCondenser
from forge.memory.condenser.impl.observation_masking_condenser import (
    ObservationMaskingCondenser,
)
from forge.memory.condenser.impl.pipeline import CondenserPipeline
from forge.memory.condenser.impl.recent_events_condenser import (
    RecentEventsCondenser,
)
from forge.memory.condenser.impl.structured_summary_condenser import (
    StructuredSummaryCondenser,
)
from forge.memory.condenser.impl.semantic_condenser import (
    SemanticCondenser,
)

__all__ = [
    "AmortizedForgettingCondenser",
    "BrowserOutputCondenser",
    "CondenserPipeline",
    "ConversationWindowCondenser",
    "ImportantEventSelection",
    "LLMAttentionCondenser",
    "LLMSummarizingCondenser",
    "NoOpCondenser",
    "ObservationMaskingCondenser",
    "RecentEventsCondenser",
    "SemanticCondenser",
    "StructuredSummaryCondenser",
]
