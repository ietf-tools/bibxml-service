(function () {

  /**
   * Instantiates a simple localStorage-backed storage.
   *
   * Since localStorage is slow and blocking,
   * under the hood loads data from storage at instantiation
   * and stores it at specified `debounceStoreMs`
   * only if items were set (state is dirty).
   */
  function getCache(cacheKey, initial, options = { ttlMs: undefined, debounceStoreMs: undefined }) {
    const DEFAULT_CACHE_TTL_MS = 3600000; // 1 hour
    const DEFAULT_DEBOUNCE_MS = 10000; // 10 seconds

    const ttl = options?.ttlMs ?? DEFAULT_CACHE_TTL_MS;
    const debounceMs = options?.debounceStoreMs ?? DEFAULT_DEBOUNCE_MS;

    const data = loadCache() ?? initial;

    let dirty = false;
    const cacheStoreInterval = window.setInterval(function cacheTick() {
      if (dirty) {
        storeCache(data);
        dirty = false;
      }
    }, debounceMs);

    function storeCache(data) {
      localStorage.setItem(cacheKey, JSON.stringify({
        ts: Date.now(),
        data,
      }));
    }

    function loadCache() {
      const cached = localStorage.getItem(cacheKey);
      if (cached !== null) {
        let deserialized;
        try {
          deserialized = JSON.parse(cached);
        } catch (e) {
          console.error("Failed to deserialize cached data", cached, e);
          deserialized = null;
        }

        if (deserialized?.ts && deserialized?.data) {
          const freshEnough = deserialized.ts > (Date.now() - ttl);

          if (freshEnough) {
            return deserialized.data;

          } else {
            console.debug("Cached data has expired", deserialized.ts);
            localStorage.removeItem(cacheKey);
          }
        } else {
          console.warn("Unexpected cached data format", deserialized || cached);
          localStorage.removeItem(cacheKey);
        }
      }
      return null;
    }

    return {

      set: function setItem (itemKey, value) {
        data[itemKey] = value;
        dirty = true;
      },

      /** Returns stored item or null. */
      get: function getItem (itemKey) {
        return data[itemKey] ?? null;
      },

      destroy: function destroyCache() {
        window.clearInterval(cacheStoreInterval);
      },

    };

  }

  window.getCache = getCache;

})();
