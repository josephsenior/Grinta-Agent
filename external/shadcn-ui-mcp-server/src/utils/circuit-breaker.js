/**
 * Circuit Breaker states
 */
export var CircuitBreakerState;
(function (CircuitBreakerState) {
    CircuitBreakerState["CLOSED"] = "CLOSED";
    CircuitBreakerState["OPEN"] = "OPEN";
    CircuitBreakerState["HALF_OPEN"] = "HALF_OPEN";
})(CircuitBreakerState || (CircuitBreakerState = {}));
/**
 * Circuit Breaker implementation for external API calls
 */
export class CircuitBreaker {
    state = CircuitBreakerState.CLOSED;
    failures = 0;
    successes = 0;
    lastFailureTime = 0;
    config;
    constructor(config = {}) {
        this.config = {
            failureThreshold: config.failureThreshold || 5,
            timeout: config.timeout || 60000, // 1 minute
            successThreshold: config.successThreshold || 2,
        };
    }
    /**
     * Execute a function with circuit breaker protection
     */
    async execute(fn) {
        if (this.isOpen()) {
            throw new Error('Service temporarily unavailable due to previous failures');
        }
        try {
            const result = await fn();
            this.onSuccess();
            return result;
        }
        catch (error) {
            this.onFailure();
            throw error;
        }
    }
    /**
     * Check if circuit breaker is open
     */
    isOpen() {
        if (this.state === CircuitBreakerState.OPEN) {
            if (Date.now() - this.lastFailureTime >= this.config.timeout) {
                this.state = CircuitBreakerState.HALF_OPEN;
                this.successes = 0;
                return false;
            }
            return true;
        }
        return false;
    }
    /**
     * Handle successful execution
     */
    onSuccess() {
        this.failures = 0;
        if (this.state === CircuitBreakerState.HALF_OPEN) {
            this.successes++;
            if (this.successes >= this.config.successThreshold) {
                this.state = CircuitBreakerState.CLOSED;
                this.successes = 0;
            }
        }
    }
    /**
     * Handle failed execution
     */
    onFailure() {
        this.failures++;
        this.lastFailureTime = Date.now();
        if (this.state === CircuitBreakerState.CLOSED &&
            this.failures >= this.config.failureThreshold) {
            this.state = CircuitBreakerState.OPEN;
        }
        else if (this.state === CircuitBreakerState.HALF_OPEN) {
            this.state = CircuitBreakerState.OPEN;
            this.successes = 0;
        }
    }
    /**
     * Get current state
     */
    getState() {
        return this.state;
    }
    /**
     * Get failure count
     */
    getFailureCount() {
        return this.failures;
    }
    /**
     * Reset circuit breaker
     */
    reset() {
        this.state = CircuitBreakerState.CLOSED;
        this.failures = 0;
        this.successes = 0;
        this.lastFailureTime = 0;
    }
}
/**
 * Circuit breaker instances for different services
 */
export const circuitBreakers = {
    github: new CircuitBreaker({ failureThreshold: 3, timeout: 30000 }),
    external: new CircuitBreaker({ failureThreshold: 5, timeout: 60000 }),
};
