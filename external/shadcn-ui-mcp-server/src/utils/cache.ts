/**
 * Cache utility for storing API responses with configurable TTL
 */

type CacheItem<T> = {
  value: T;
  timestamp: number;
  ttl: number; // Time to live in milliseconds
};

export class Cache {
  private static instance: Cache;
  private storage: Map<string, CacheItem<any>>;
  private defaultTTL: number;

  private constructor(defaultTTL = 3600000) {
    // Default TTL: 1 hour
    this.storage = new Map();
    this.defaultTTL = defaultTTL;
  }

  /**
   * Get the singleton instance of the cache
   */
  public static getInstance(defaultTTL?: number): Cache {
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
  public set<T>(key: string, value: T, ttl = this.defaultTTL): void {
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
  public get<T>(key: string): T | null {
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

    return item.value as T;
  }

  /**
   * Retrieve a value from cache or compute it if not available
   * @param key Cache key
   * @param fetchFn Function to compute the value if not in cache
   * @param ttl Optional TTL in milliseconds
   * @returns The cached or computed value
   */
  public async getOrFetch<T>(
    key: string,
    fetchFn: () => Promise<T>,
    ttl = this.defaultTTL
  ): Promise<T> {
    const cachedValue = this.get<T>(key);

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
  public has(key: string): boolean {
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
  public delete(key: string): boolean {
    return this.storage.delete(key);
  }

  /**
   * Clear all items from the cache
   */
  public clear(): void {
    this.storage.clear();
  }

  /**
   * Delete all expired items from the cache
   * @returns Number of items deleted
   */
  public clearExpired(): number {
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
  public deleteByPrefix(prefix: string): number {
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
  public size(): number {
    return this.storage.size;
  }

  /**
   * Set the default TTL for cache items
   * @param ttl New default TTL in milliseconds
   */
  public setDefaultTTL(ttl: number): void {
    this.defaultTTL = ttl;
  }
}

// Export a singleton instance
export const cache = Cache.getInstance();
