// NOTE: this module relies on TailwindCSS classes.

(function () {
  const els = document.querySelectorAll('[data-xml2rfc-subpath]')

  // Heroicons
  const copyButtonSVG = `
    <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
      <path d="M9 2a2 2 0 00-2 2v8a2 2 0 002 2h6a2 2 0 002-2V6.414A2 2 0 0016.414 5L14 2.586A2 2 0 0012.586 2H9z" />
      <path d="M3 8a2 2 0 012-2v10h8a2 2 0 01-2 2H5a2 2 0 01-2-2V8z" />
    </svg>
  `;
  const selectButtonSVG = `
    <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
      <path fill-rule="evenodd" d="M6.672 1.911a1 1 0 10-1.932.518l.259.966a1 1 0 001.932-.518l-.26-.966zM2.429 4.74a1 1 0 10-.517 1.932l.966.259a1 1 0 00.517-1.932l-.966-.26zm8.814-.569a1 1 0 00-1.415-1.414l-.707.707a1 1 0 101.415 1.415l.707-.708zm-7.071 7.072l.707-.707A1 1 0 003.465 9.12l-.708.707a1 1 0 001.415 1.415zm3.2-5.171a1 1 0 00-1.3 1.3l4 10a1 1 0 001.823.075l1.38-2.759 3.018 3.02a1 1 0 001.414-1.415l-3.019-3.02 2.76-1.379a1 1 0 00-.076-1.822l-10-4z" clip-rule="evenodd" />
    </svg>
  `;

  // If we support permissions
  if (navigator.permissions) {
    navigator.permissions.query({name: "clipboard-write"}).then(result => {
      // And we get them
      if (result.state == "granted" || result.state == "prompt") {
        // Initialize widget with copy button
        els.forEach(initCopyWidget);
      } else {
        // Otherwise, initialize widget with select-all button
        els.forEach(initSelectWidget);
      }
    });
  } else {
    // Otherwise, initialize widget with select-all button
    els.forEach(initCopyWidget);
  }

  /** Initialize with copy button. */
  function initCopyWidget(el) {
    const subpath = el.dataset.xml2rfcSubpath;
    const fullURL = withProtocol(el.dataset.fullUrl);
    const input = el.querySelector('input');

    let destroyAbbreviator = abbreviateUntilHover(el, input);

    function reinitialize() {
      input.value = fullURL;
      destroyAbbreviator = abbreviateUntilHover(el, input);
    }

    function handleXml2rfcUrlCopy() {
      input.select();

      navigator.clipboard.writeText(fullURL).then(function() {
        console.info("Copied xml2rfc path to clipboard");
        destroyAbbreviator();
        input.value = "Copied!";
        setTimeout(reinitialize, 2000);
      }, function(err) {
        console.error("Couldn’t copy xml2rfc path to clipboard", fullURL, err);
        // At least select the text for easier copying
        input.select();
      });
    }

    if (subpath && fullURL) {
      addButton(
        el,
        "Copy this xml2rfc URL to clipboard",
        copyButtonSVG,
        handleXml2rfcUrlCopy,
        input.nextSibling,
      );
    } else {
      console.warning("Cannot initialize copy xml2rfc path widget: missing data attributes", el);
    }
  }

  /** Initialize with select-all button. */
  function initSelectWidget(el) {
    const input = el.querySelector('input');
    const destroyAbbreviator = abbreviateUntilHover(el, input);
    addButton(
      el,
      "Select this xml2rfc URL",
      selectButtonSVG,
      function () {
        input.select();
        destroyAbbreviator();
      },
      input.nextSibling,
    );
  }

  /**
   * Inserts a button within given element.
   *
   * @param {HTMLElement} el container in which to add the button,
   * should contain data-copy-button-class attribute to specify button class
   * @param {string} title button tooltip text
   * @param {string} iconHTML button inner HTML (SVG)
   * @param {function} clickHandler button click handler
   * @param {HTMLElement} (optional) beforeEl child before which to insert the button
   */
  function addButton(el, title, iconHTML, clickHandler, beforeEl) {
    const btnEl = document.createElement('span');
    btnEl.setAttribute('class', el.dataset.copyButtonClass ?? '');
    btnEl.setAttribute('title', title);
    btnEl.innerHTML = iconHTML;
    btnEl.addEventListener('click', clickHandler);
    if (beforeEl) {
      el.insertBefore(btnEl, beforeEl);
    } else {
      el.appendChild(btnEl);
    }
    btnEl.classList.add('cursor-pointer');
  }

  /**
   * Replaces reference element with a span containing
   * abbreviated version, showing the reference on hover.
   *
   * @param {HTMLElement} el container
   * with the data-abbreviate-as attribute.
   * @param {HTMLElement} reference
   * a child of el that contains the full version of the string
   * to abbreviate.
   */
  function abbreviateUntilHover(el, reference) {
    const short = document.createElement('span');
    short.setAttribute('class', reference.getAttribute('class'));
    short.innerText = el.dataset.abbreviateAs;
    el.prepend(short);

    function handleExpand() {
      short.classList.add('hidden');
      reference.classList.remove('hidden');
    }
    function handleAbbreviate() {
      reference.classList.add('hidden');
      short.classList.remove('hidden');
    }

    handleAbbreviate();

    el.addEventListener('mouseenter', handleExpand);
    el.addEventListener('mouseleave', handleAbbreviate);

    return function destroyAbbreviator() {
      el.removeEventListener('mouseenter', handleExpand);
      el.removeEventListener('mouseleave', handleAbbreviate);
      el.removeChild(short);
      handleExpand();
    }
  }

  /**
   * If given URL is protocol-relative, prepend current protocol;
   * otherwise return as is.
   */
  function withProtocol(url) {
    if (url.indexOf('//') === 0) {
      return `${location.protocol}${url}`;
    } else {
      return url;
    }
  }
})();
