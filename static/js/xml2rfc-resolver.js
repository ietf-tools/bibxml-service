(function () {

  /**
   * Creates an intersection observer and watches given elements.
   *
   * Each element is expected to have an `xml2rfc-path` data attribute,
   * and a `.resolution` child in which abbreviated resolution result
   * will be formatted as HTML.
   *
   * Each path is only resolved when the element is scrolled into view,
   * and resolutions are queued to avoid overloading the server.
   *
   * Uses given `storage` (should provide `set` and `get` methods),
   * which can cache data.
   *
   * Returned function disconnects the observer and destroys given storage
   * (not deleting cached data, though).
   */
  function watchElements (storage, elements, scrollView, globalPrefix) {
    // Queue resolutions with concurrency at 1
    const resolutionQueue = async.queue(processResolutionTask, 1);
    resolutionQueue.error(function handleResolutionError (err, path) {
      console.error("Failed to resolve path", path, err);
    });

    // Resolve each path when its element is in view
    const observer = new IntersectionObserver(entries => {
      for (const entry of entries) {
        if (entry.intersectionRatio > 0) {
          const resolution = entry.target.querySelector('.resolution');
          if (resolution) {
            resolutionQueue.push(
              entry.target.dataset['xml2rfc-path']
            );
          }
        }
      }
    }, { root: scrollView, threshold: 0.5 });

    for (const el of elements) {
      if (el.dataset['xml2rfc-path'] && el.querySelector('.resolution')) {
        observer.observe(el);
      } else {
        console.warn("Won’t watch element (no path data or resolution placeholder)", el);
      }
    }

    async function processResolutionTask(subpath) {
      const el = document.querySelector(`[data-xml2rfc-path="${subpath}"]`);
      if (!el) {
        console.warn("Won’t resolve path: element not in DOM", subpath, el);
        return;
      }
      const resolutionEl = el.querySelector('.resolution');
      if (!resolutionEl) {
        console.error("Won’t resolve path: missing resolution placeholder", subpath);
        return;
      }

      let outcome = storage.get(subpath);
      const cacheHit = outcome !== null;
      if (!outcome) {
        try {
          outcome = await resolvePath(`${globalPrefix}${subpath}`);
        } catch (e) {
          outcome = null;
          formatResolutionError(resolutionEl, e);
        } finally {
        }
      }
      if (outcome) {
        formatResolutionOutcome(
          resolutionEl,
          outcome.primaryMethod,
          outcome.succeededMethod);
        if (!cacheHit) {
          storage.set(subpath, outcome);
        }
      }
    }

    return function unwatch() {
      observer.disconnect();
      storage.destroy?.();
    }
  }

  /**
   * Resolves a single path. Returns a promise of resolution outcome.
   *
   * This function does not use the queue and is processed immediately.
   *
   * The minimal resolution outcome looks like:
   * {
   *   primaryMethod: 'manual' | 'auto',
   *   succeededMethod: 'manual' | 'auto' | 'fallback' | null,
   * }
   *
   * `detailed` parameter, if `true`, extends it with the following:
   * { resolvedXML: string | null, methods: MethodOutcome[] }
   *
   * where each MethodOutcome is:
   * { methodName: string, config: string, errorInfo: string | null }
   *
   * `compare` parameter, if `true`, extends it with the following
   * by checking with xml2rfc.tools.ietf.org:
   * { xml2rfcXML: string | null }
   */
  async function resolvePath (path, detailed, compare) {
    const result = await axios.get(`/${path}`);

    const methodsTried = result.headers['x-resolution-methods']?.split(';') ?? [];
    const rawMethodOutcomes = result.headers['x-resolution-outcomes']?.split(';') ?? [];

    const methodOutcomes = [];
    for (const [idx, methodName] of methodsTried.entries()) {
      const rawMethodOutcome = rawMethodOutcomes[idx];
      if (rawMethodOutcome) {
        const [config, err] = rawMethodOutcome.split(',');
        methodOutcomes.push({
          methodName,
          config: config.trim() !== '' ? config : null,
          errorInfo: err.trim() !== '' ? err : null,
        });
      } else {
        methodOutcomes.push({
          methodName,
          config: undefined,
          errorInfo: undefined,
        });
      }
    }

    const primaryMethodOutcome = methodOutcomes.find(o =>
      o.config !== undefined);
    const successfulMethodOutcome = methodOutcomes.find(o =>
      o.config !== undefined && o.errorInfo === null);

    const outcome = {
      succeededMethod: successfulMethodOutcome?.methodName ?? null,
      primaryMethod: primaryMethodOutcome?.methodName ?? null,
    }

    if (detailed) {
      outcome.methods = methodOutcomes;
      outcome.resolvedXML = result.data;
    }

    if (compare) {
      try {
        outcome.xml2rfcXML = (await axios.get(`https://xml2rfc.tools.ietf.org/${path}`)).data;
      } catch (e) {
        console.error("Unable to fetch xml2rfc data for comparison:", e);
        outcome.xml2rfcXML = null;
      }
    }

    return outcome;
  }

  // Main API
  window.xml2rfcResolver = {
    watchElements,
    resolvePath,
  };


  // Resolution info DOM manipulation utilities used by watchElements()

  const resolutionHTMLClasses = {
    success: ['text-emerald-100', 'bg-emerald-600'],
    error: ['text-rose-100', 'bg-rose-600'],
    warning: ['text-amber-100', 'bg-amber-600'],
  };

  function clearResolution(container) {
    for (const clsList of Object.values(resolutionHTMLClasses)) {
      container.classList.remove(
        ...clsList,
      );
    }
  }

  function formatResolutionError(container, err) {
    clearResolution(container);
    container.classList.add(...resolutionHTMLClasses.error);
    container.textContent = err.toString?.() ?? `${err}`;
  }

  function formatResolutionOutcome(container, primaryMeth, succeededMeth) {
    clearResolution(container);
    if (succeededMeth !== 'fallback' && primaryMeth === succeededMeth && succeededMeth !== null) {
      container.classList.add(...resolutionHTMLClasses.success);
    } else if (succeededMeth === 'fallback') {
      container.classList.add(...resolutionHTMLClasses.warning);
    } else {
      container.classList.add(...resolutionHTMLClasses.error);
    }
    container.textContent = succeededMeth ?? 'N/A';
  }
})();
