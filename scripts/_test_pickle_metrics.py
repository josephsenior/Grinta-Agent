import logging
import pickle
from openhands.llm.metrics import Metrics

logger = logging.getLogger("openhands.scripts.test_pickle_metrics")


def main():
    m = Metrics("x")
    m.add_cost(0.1)
    logger.info("metrics ok, class: %s", Metrics)
    d = {"a": m}
    try:
        b = pickle.dumps(d)
        logger.info("pickled len %d", len(b))
    except Exception as e:
        logger.exception("pickle error: %s", e)


if __name__ == "__main__":
    main()
