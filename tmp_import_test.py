import logging
import forge.metasop.orchestrator as o

logger = logging.getLogger(__name__)
logger.info("IMPORT_OK %s", hasattr(o, "MetaSOPOrchestrator"))
