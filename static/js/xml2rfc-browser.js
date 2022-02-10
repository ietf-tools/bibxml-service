(function () {

  const TAILWIND_SM_BREAKPOINT_PX = 640;

  const pageCacheKey = document.documentElement.dataset['xml2rfc-cache-key'];
  // Is used to invalidate cached path resolution data whenever manual mappings change.

  const dirname = document.documentElement.dataset['xml2rfc-dirname'];
  const globalPrefix = document.documentElement.dataset['xml2rfc-global-prefix'];
  const selectedPath = document.documentElement.dataset['xml2rfc-selected-path'];

  const allPathEls = document.querySelectorAll('[data-xml2rfc-path]');
  const scrollView = document.getElementById('xml2rfcPathScrollView');

  if (dirname && pageCacheKey && scrollView && globalPrefix && allPathEls.length > 0) {

    // Set up item listing

    const cacheKey = `path-resolution-${pageCacheKey}`;
    const cache = window.getCache(cacheKey, {});

    const needJSBrowserForItems = scrollView.dataset['load-js-browser-this-is-too-many-items'];
    if (needJSBrowserForItems) {
      window.createWindowedXml2rfcPathListing(
        JSON.parse(needJSBrowserForItems),
        scrollView,
        cache,
        globalPrefix,
        selectedPath,
        markAsSelected,
      );
    } else {
      window.xml2rfcResolver.watchElements(cache, allPathEls, scrollView, globalPrefix);
      if (selectedPath) {
        const vw = Math.max(document.documentElement.clientWidth || 0, window.innerWidth || 0);
        if (vw > TAILWIND_SM_BREAKPOINT_PX) {
          const el = document.querySelector(`[data-xml2rfc-path="${selectedPath}"]`);
          if (el) {
            // Scroll to selected path if any
            el.parentNode.scrollTop = el.offsetTop - el.parentNode.offsetTop
            markAsSelected(el);
          }
        }
      }
    }


    // Set up testing selected path

    if (selectedPath) {
      const testEl = document.getElementById('resolutionTest');
      const testButton = document.createElement('button');
      testButton.classList.add('button', 'py-2', 'w-full', 'block', 'my-2');
      testButton.textContent = "Test resolution now";

      function makeXMLPreview(outcome) {
        const el = document.createElement('div');
        el.classList.add('grow', 'md:flex', 'flex-col', 'md:overflow-hidden');

        function togglePreview() {
          if (previewEl.dataset['active'] === 'resolved') {
            if (outcome.xml2rfcXML) {
              try {
                previewEl.innerText = window.formatXML(outcome.xml2rfcXML);
              } catch (e) {
                previewEl.innerText = `Error formatting reference XML: ${e.toString?.() ?? e}`;
              }
            } else {
              previewEl.innerText = "Unable to obtain reference XML from xml2rfc tools";
            }
            previewEl.dataset['active'] = 'reference';
            toggleButton.innerText = "Show resolved";
          } else {
            previewEl.innerText = window.formatXML(outcome.resolvedXML);
            previewEl.dataset['active'] = 'resolved';
            toggleButton.innerText = "Show reference";
          }
        }
        const toggleButton = document.createElement('button');
        toggleButton.innerText = "Show reference";
        toggleButton.addEventListener('click', togglePreview);
        toggleButton.classList.add('button', 'w-full', 'py-2');
        el.appendChild(toggleButton);

        const previewEl = document.createElement('pre');
        previewEl.classList.add(
          'font-monospace',
          'text-xs',
          'overflow-auto',
          'grow',
          'p-2',
          'bg-dark-700',
          'text-white',
        );
        previewEl.innerText = window.formatXML(outcome.resolvedXML);
        previewEl.dataset['active'] = 'resolved';
        el.appendChild(previewEl);

        return el;
      }

      async function handleTestClick(evt) {
        evt.preventDefault();
        evt.stopPropagation();

        testButton.setAttribute('disabled', 'disabled');

        document.getElementById('testResult')?.remove();
        const testResultEl = document.createElement('div');
        testResultEl.setAttribute('id', 'testResult');
        testResultEl.textContent = "Requesting…";
        testResultEl.classList.add('grow', 'md:flex', 'flex-col', 'md:overflow-hidden');
        testEl.appendChild(testResultEl);

        let outcome;
        try {
          outcome = await window.xml2rfcResolver.
            resolvePath(`${globalPrefix}${selectedPath}`, true, true);
        } catch (e) {
          testResultEl.textContent = `Error: ${e.toString?.() ?? e}`;
          outcome = null;
        } finally {
          testButton.removeAttribute('disabled');
        }

        if (outcome) {
          testResultEl.innerHTML = '';

          const methodChainEl = document.createElement('ul');
          methodChainEl.classList.add(
            'my-2',
            'whitespace-nowrap',
            'flex',
            'flex-col',
            'text-xs',
            'uppercase',
            'tracking-tight',
          );
          for (const meth of outcome.methods) {
            const el = document.createElement('li');
            if (meth.config !== undefined) {
              el.innerHTML = `
                &rarr;
                ${meth.methodName}${meth.config ? `(${meth.config}): ` : ': '}
                ${meth.errorInfo ?? 'ok'}
              `;
            } else {
              el.innerHTML = `
                &rarr;
                ${meth.methodName}: N/A
              `;
            }
            methodChainEl.appendChild(el);
          }
          testResultEl.appendChild(methodChainEl);

          if (outcome.resolvedXML || outcome.xml2rfcXML) {
            const previewEl = makeXMLPreview(outcome);
            testResultEl.appendChild(previewEl);
          }
        }
      }

      testButton.addEventListener('click', handleTestClick);
      testEl.appendChild(testButton);
    }
  }

  /** Make item look selected. */
  function markAsSelected(el) {
    el.classList.add('bg-sky-800');
    el.classList.add('text-white');
  }

})();
