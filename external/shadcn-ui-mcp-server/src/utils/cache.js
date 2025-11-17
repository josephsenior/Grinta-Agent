/**
 * Cache utility for storing API responses with configurable TTL
 */
export class Cache {
    static instance;
    storage;
    defaultTTL;
    constructor(defaultTTL = 3600000) {
        // Default TTL: 1 hour
        this.storage = new Map();
        this.defaultTTL = defaultTTL;
    }
    /**
     * Get the singleton instance of the cache
     */
    static getInstance(defaultTTL) {
        if (!Cache.instance) {
            Cache.instance = new Cache(defaultTTL);
        }
        return Cache.instance;
    }
    /**
     * Set an item in the cache
     * @param key Cache key
     * @param value Value to store
     * @param ttl Optional TTL in milliseconds
     */
    set(key, value, ttl = this.defaultTTL) {
        this.storage.set(key, {
            value,
            timestamp: Date.now(),
            ttl,
        });
    }
    /**
     * Get an item from the cache
     * @param key Cache key
     * @returns The cached value or null if not found or expired
     */
    get(key) {
        const item = this.storage.get(key);
        // Return null if the item doesn't exist
        if (!item) {
            return null;
        }
        // Check if the item has expired
        const now = Date.now();
        if (item.ttl > 0 && now - item.timestamp > item.ttl) {
            // Item has expired, remove it from cache
            this.storage.delete(key);
            return null;
        }
        return item.value;
    }
    /**
     * Retrieve a value from cache or compute it if not available
     * @param key Cache key
     * @param fetchFn Function to compute the value if not in cache
     * @param ttl Optional TTL in milliseconds
     * @returns The cached or computed value
     */
    async getOrFetch(key, fetchFn, ttl = this.defaultTTL) {
        const cachedValue = this.get(key);
        if (cachedValue !== null) {
            return cachedValue;
        }
        // Value not in cache or expired, fetch it
        const value = await fetchFn();
        this.set(key, value, ttl);
        return value;
    }
    /**
     * Check if a key exists in the cache and is not expired
     * @param key Cache key
     * @returns Whether the key exists and is not expired
     */
    has(key) {
        const item = this.storage.get(key);
        if (!item) {
            return false;
        }
        const now = Date.now();
        if (item.ttl > 0 && now - item.timestamp > item.ttl) {
            this.storage.delete(key);
            return false;
        }
        return true;
    }
    /**
     * Delete an item from the cache
     * @param key Cache key
     * @returns Whether the item was successfully deleted
     */
    delete(key) {
        return this.storage.delete(key);
    }
    /**
     * Clear all items from the cache
     */
    clear() {
        this.storage.clear();
    }
    /**
     * Delete all expired items from the cache
     * @returns Number of items deleted
     */
    clearExpired() {
        const now = Date.now();
        let deletedCount = 0;
        this.storage.forEach((item, key) => {
            if (item.ttl > 0 && now - item.timestamp > item.ttl) {
                this.storage.delete(key);
                deletedCount++;
            }
        });
        return deletedCount;
    }
    /**
     * Delete items matching a prefix
     * @param prefix Key prefix to match
     * @returns Number of items deleted
     */
    deleteByPrefix(prefix) {
        let deletedCount = 0;
        this.storage.forEach((_, key) => {
            if (key.startsWith(prefix)) {
                this.storage.delete(key);
                deletedCount++;
            }
        });
        return deletedCount;
    }
    /**
     * Get the size of the cache
     * @returns Number of items in the cache
     */
    size() {
        return this.storage.size;
    }
    /**
     * Set the default TTL for cache items
     * @param ttl New default TTL in milliseconds
     */
    setDefaultTTL(ttl) {
        this.defaultTTL = ttl;
    }
}
// Export a singleton instance
export const cache = Cache.getInstance();
