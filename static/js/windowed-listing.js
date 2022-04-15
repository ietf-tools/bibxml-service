(function () {

  /**
   * Sets up a windowed listing, given `itemIDs` (list of strings) and `scrollView`.
   *
   * Items may have hierarchy, by having item IDs that contain forward slashes (`/`).
   *
   * `itemIDs` should contain a list of items (their IDs) to be shown initially.
   * Normally it would be a list of top-level item IDs.
   * If there are IDs that are nested, their parents will be auto-expanded
   * for items to be shown.
   *
   * `scrollView` *must* contain at least one item already; it’ll be used as a template.
   * The template item must contain a link (`<a>`) child with a `<span>` inside,
   * where item label will be rendered.
   *
   * Created item’s DOM element will have `itemID` data attribute set appropriately.
   *
   * Calls `await isExpandable(itemID: string)` when an item is being constructed.
   * If provided and returns true, the item can be expanded.
   *
   * Calls `await getItemLabel(itemID: string)` when an item is being constructed.
   * If not provided or returns a falsey value, raw item ID will be shown.
   *
   * Calls `await getItemChildren(itemID: string)` when an item is expanded.
   * The result should return a list of item IDs to show underneath the expanded item.
   *
   * Calls `onWindowChange(items: Node[])` with the list of DOM elements in view
   * whenever a list of items within the window changes.
   *
   * Calls `onSelectItem(itemID: string, item: Node)` with selected item’s DOM element,
   * letting the user to adjust DOM as needed.
   *
   * Returns an object that represents windowed listing API. The API includes:
   * 
   * - `updateItems()`: can be called with an updater function.
   *   Updater function will receive a list of currently shown item IDs,
   *   and should return a list of item IDs to be shown.
   *   This can be used in search functionality: callers can implement a search widget
   *   that binds `updateItems()` to search query changes.
   */
  function createWindowedListing (
    initialItemIDs,
    scrollView,
    initialSelectedItemID,
    onSelectItem,
    getItemLabel,
    getItemChildren,
    isExpandable,
    onWindowChange,
  ) {
    const DEBOUNCE_SCROLL_MS = 50;
    const EXTRA_ITEMS_BEFORE = 10;
    const EXTRA_ITEMS_AFTER = 10;

    // These three may change at runtime, depending on item expanded state:
    let itemIDs = [...initialItemIDs];
    let itemCount = itemIDs.length;
    let expandedItems = {};  // A map of { [itemID]: true }

    let selectedItemID = initialSelectedItemID;

    // Relative is important, the remaining ones are useful for small viewports (mobile)
    scrollView.style.position = 'relative';
    scrollView.style.overflowY = 'auto';
    // scrollView.classList.add('relative', 'max-h-screen', 'overflow-y-auto');

    // Keep the first child as template
    const firstItem = scrollView.children[0];
    const itemHeight = firstItem.offsetHeight;
    const templateItem = firstItem.cloneNode(true);

    // Clear scroll view and add a height-forcing div
    scrollView.innerHTML = '';
    const heightExpander = document.createElement('div');
    heightExpander.style.height = `${itemCount * itemHeight}px`;
    scrollView.appendChild(heightExpander);

    // If item is selected, scroll the outer element to make it appear in view
    // before initializing item window
    if (initialSelectedItemID) {
      const selectedItemIdx = itemIDs.indexOf(initialSelectedItemID);
      if (selectedItemIdx >= 0) {
        scrollView.scrollTop = (selectedItemIdx * itemHeight);
      }
    }

    // Automatically refresh window on each subsequent scroll
    let scrollTimeout = null;
    function handleScrollDebounced() {
      if (scrollTimeout) { window.clearTimeout(scrollTimeout); }
      scrollTimeout = setTimeout(refreshItemWindow, DEBOUNCE_SCROLL_MS);
    }
    scrollView.addEventListener('scroll', handleScrollDebounced);


    // Window refresh

    let itemWindow = null;

    // Call it in the beginning
    updateItems((() => initialItemIDs), true);

    async function updateItems(updaterFunc, resetExpanded) {
      if (resetExpanded === true) {
        expandedItems = {};
      }

      itemIDs = updaterFunc(itemIDs).filter(function deduplicate(itemID, idx, self) {
        return idx === self.indexOf(itemID);
      });

      function _expandParents(iid, idx) {
        if (iid.indexOf('/') >= 0) {
          const parts = iid.split('/');
          const parentsToExpand = [];

          let currentParent = '';
          for (const part of parts.slice(0, parts.length - 1)) {
            if (currentParent) {
              currentParent = `${currentParent}/${part}`;
            } else {
              currentParent = part;
            }
            parentsToExpand.push(currentParent);
          }

          parentsToExpand.reverse();
          for (const par of parentsToExpand) {
            expandedItems[par] = true;
            if (itemIDs.indexOf(par) < 0) {
              itemIDs.splice(idx, 0, par);
            }
          }
        }
      }

      // Expand parents of shown items, if needed
      if (isExpandable) {
        for (const [idx, iid] of itemIDs.entries()) {
          _expandParents(iid, idx);
        }
      }

      itemCount = itemIDs.length;

      await refreshItemWindow();
    }

    async function onToggleItem(itemID) {
      if (expandedItems[itemID]) {
        return onCollapseItem(itemID);
      } else if (isExpandable) {
        return onExpandItem(itemID);
      }
    }

    async function onExpandItem(itemID) {
      if (isExpandable && getItemChildren && await isExpandable(itemID)) {
        const childrenIDs = await getItemChildren(itemID);
        const itemIdx = itemIDs.indexOf(itemID);
        if (itemIdx >= 0 && childrenIDs) {
          expandedItems[itemID] = true;
          await updateItems(items => [
            ...items.slice(0, itemIdx + 1),
            ...childrenIDs,
            ...items.slice(itemIdx + 1),
          ]);
        }
        if (childrenIDs.length == 1) {
          await onExpandItem(childrenIDs[0]);
        } else {
          for (const cid of childrenIDs) {
            if (expandedItems[cid]) {
              await onExpandItem(cid);
            }
          }
        }
      }
    }
    async function onCollapseItem(itemID) {
      if (expandedItems[itemID]) {
        expandedItems[itemID] = false;
        delete expandedItems[itemID];
        await updateItems(items => items.filter(iid => iid.startsWith(`${itemID}/`) !== true));
      }
    }

    async function refreshItemWindow() {
      heightExpander.style.height = `${itemCount * itemHeight}px`;

      // Clean up previous window and xml2rfc resolver-watcher
      if (itemWindow !== null) {
        scrollView.removeChild(itemWindow);
      }

      // Add item window to main scroll view
      itemWindow = scrollView.appendChild(document.createElement('div'));

      // Determine which items to show
      let firstIdx = Math.floor(scrollView.scrollTop / itemHeight) - EXTRA_ITEMS_BEFORE;
      if (firstIdx < 0) {
        firstIdx = 0;
      }
      let lastIdx = firstIdx + Math.ceil(scrollView.offsetHeight / itemHeight) + 1 + EXTRA_ITEMS_AFTER;
      if (lastIdx + 1 >= itemCount) {
        lastIdx = itemCount - 1;
      }

      // Position window absolutely within the large scroll view,
      // depending on which item is first in view
      itemWindow.style.top = `${firstIdx * itemHeight}px`;
      itemWindow.style.position = 'absolute';
      itemWindow.style.right = '0';
      itemWindow.style.left = '0';

      // For each item to show, create element and append it to item window
      for (const [, itemID] of [...itemIDs.entries()].filter(([idx, ]) => idx >= firstIdx && idx <= lastIdx)) {
        const el = itemWindow.appendChild(await makeItem(itemID));
        if (itemID === selectedItemID && onSelectItem) {
          // If this item happens to be selected, make it look so
          onSelectItem(itemID, el);
        }
      }

      if (onWindowChange) {
        onWindowChange([...itemWindow.children]);
      }

      return itemWindow;
    }

    // Constructing items from template

    async function makeItem(itemID) {
      const indentation = itemID.split('/').length;

      const newItem = templateItem.cloneNode(true);

      newItem.dataset.itemID = itemID;
      newItem.setAttribute('title', itemID);
      newItem.style.cursor = 'pointer';

      let labelTemplate = newItem.removeChild(newItem.querySelector('span[data-item-label]'));
      let labelEl;
      if (getItemLabel) {
        labelEl = await getItemLabel(itemID, labelTemplate);
      } else {
        labelEl = labelTemplate;
        labelEl.innerHTML = itemID;
      }
      labelEl.style.paddingLeft = `${indentation - 1}em`;

      if (isExpandable) {
        const iconEl = labelEl.appendChild(document.createElement('i'));
        iconEl.style.width = '1.5em';
        iconEl.style.marginRight = '.5em';
        if (await isExpandable(itemID)) {
          if (expandedItems[itemID]) {
            iconEl.classList.add('fas', 'fa-folder-open');
          } else {
            iconEl.classList.add('fas', 'fa-folder');
          }
        } else {
          iconEl.classList.add('fas', 'fa-file');
        }
      }

      newItem.appendChild(labelEl);

      newItem.addEventListener(
        'click',
        function handleItemClick (evt) {
          selectedItemID = itemID;
          onSelectItem(itemID, newItem);
          onToggleItem(itemID);
        },
      );

      return newItem;
    }

    function getVisibleElements() {
      if (itemWindow) {
        return [...itemWindow.children];
      }
    }

    function getItemIDs() {
      return itemIDs;
    }

    return {
      updateItems,
      getVisibleElements,
      getItemIDs,
    }
  }

  window.createWindowedListing = createWindowedListing;
})();
