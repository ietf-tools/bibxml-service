(function () {

  /**
   * Sets up a windowed listing, given `itemPaths` (list of strings) and `scrollView`.
   * `scrollView` *must* contain at least one item already; it’ll be used as a template.
   *
   * The template item is required to contain an a child with span inside and .resolution
   * as required by `xml2rfcResolver.watchElements()`.
   *
   * Whenever window changes, invokes `xml2rfcResolver.watchElements()` on shown items,
   * passing given `storage` and `globalPrefix`.
   */
  function getWindowedPathListing (itemPaths, scrollView, storage, globalPrefix, selectedPath, markPathElAsSelected) {
    const DEBOUNCE_SCROLL_MS = 100;

    const itemCount = itemPaths.length;
    const itemPathEntries = [...itemPaths.entries()];

    scrollView.classList.add('relative', 'max-h-screen', 'overflow-y-auto');

    const firstItem = scrollView.children[0];
    const itemHeight = firstItem.offsetHeight;
    const templateItem = firstItem.cloneNode(true);
    delete templateItem.dataset.xml2rfcPath;

    scrollView.innerHTML = '';
    const heightExpander = document.createElement('div');
    heightExpander.style.height = `${itemCount * itemHeight}px`;
    scrollView.appendChild(heightExpander);

    let itemWindow = null;
    let cleanUpWatcher = null;

    if (selectedPath) {
      const selectedItemIdx = itemPaths.indexOf(selectedPath);
      if (selectedItemIdx >= 0) {
        scrollView.scrollTop = (selectedItemIdx * itemHeight);
      }
    }
    refreshItemWindow();

    let scrollTimeout = null;
    function handleScrollDebounced() {
      if (scrollTimeout) { window.clearTimeout(scrollTimeout); }
      scrollTimeout = setTimeout(refreshItemWindow, DEBOUNCE_SCROLL_MS);
    }
    scrollView.addEventListener('scroll', handleScrollDebounced);

    function refreshItemWindow() {
      if (itemWindow !== null) {
        scrollView.removeChild(itemWindow);
      }

      cleanUpWatcher?.();

      itemWindow = scrollView.appendChild(document.createElement('div'));
      const firstIdx = Math.floor(scrollView.scrollTop / itemHeight);
      const lastIdx = firstIdx + Math.ceil(scrollView.offsetHeight / itemHeight) + 1;
      if (lastIdx + 1 >= itemCount) {
        lastIdx = itemCount - 1;
      }
      itemWindow.classList.add('absolute', 'left-0', 'right-0');
      itemWindow.style.top = `${firstIdx * itemHeight}px`;

      for (const [, path] of itemPathEntries.filter(([idx, ]) => idx >= firstIdx && idx <= lastIdx)) {
        const el = itemWindow.appendChild(makeItem(path));
        if (path === selectedPath) {
          markPathElAsSelected(el);
        }
      }

      cleanUpWatcher = window.xml2rfcResolver.watchElements(
        storage,
        itemWindow.children,
        scrollView,
        globalPrefix,
      );

      return itemWindow;
    }

    function makeItem(path) {
      const newItem = templateItem.cloneNode(true);
      const linkEl = newItem.querySelector('a');
      const originalHrefParts = linkEl.getAttribute('href').split('/'); 
      const fnameEl = linkEl.querySelector('span');

      newItem.dataset.xml2rfcPath = path;
      newItem.setAttribute('title', path);

      const newHref = `${originalHrefParts.slice(0, originalHrefParts.length - 3).join('/')}/${path}`;
      linkEl.setAttribute('href', newHref);

      const filename = path.split('/').slice(1, 2)[0];
      fnameEl.textContent = filename;

      return newItem;
    }
  }

  window.createWindowedXml2rfcPathListing = getWindowedPathListing;
})();
