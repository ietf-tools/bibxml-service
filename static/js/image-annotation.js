(function () {

  function findInPageElementsMatchingBodySelector(bodies) {
    const matchingCssSelectors = bodies.
    // Find bodies we support
    filter(b =>
      b.type === 'SpecificResource' &&
      b.purpose === 'annotating' &&
      b.source === '#' &&
      b.selector &&
      [b.selector].flat(3).find(s => s.type === 'CssSelector' && s.value)).
    // Get a list of CSS selectors as strings
    map(b => [b.selector]).
    flat(3).
    map(sel => sel.value).
    // Deduplicate selectors
    filter((val, pos, arr) => arr.indexOf(val) === pos);

    const els = [];

    for (const selector of matchingCssSelectors) {
      const linkedEls = document.querySelectorAll(selector);
      for (const el of linkedEls) {
        if (els.indexOf(el) < 0 && !els.find(e => e.isEqualNode(el))) { // Some selectors may overlap
          els.push(el);
        }
      }
    }

    return els;
  }

  /** Editor (read-only) widget for Annotorious. */
  function makeInPageAnnotationBody(args) {
    const ann = args.annotation;
    const linkedEls = findInPageElementsMatchingBodySelector(ann.body);

    const container = document.createElement('div');
    container.classList.add('p-2');
    container.classList.add('text-xs');
    if (linkedEls && linkedEls.length > 0) {
      for (const el of linkedEls) {
        const c = document.createElement('div');
        for (const child of el.childNodes) {
          const cloned = child.cloneNode(true);
          c.appendChild(cloned);
        }
        container.appendChild(c);
      }
    } else {
      console.warn("In-page image annotation: no supporting bodies or matching DOM elements found", ann.body);
      const placeholder = container.appendChild(document.createElement('span'));
      placeholder.innerText = "No annotation";
    }

    return container;
  }

  /**
   * @param {HTMLImageElement} el image element to annotate
   * @param {Object} annotations object mapping annotation IDs to media-frags fragment selector value
   * @returns initialized Annotorious instance
   */
  async function initializeAnnotator(el, annotations) {
    const anno = Annotorious.init({
      image: el,
      widgets: [
        makeInPageAnnotationBody,
        'COMMENT',
      ],
    });

    anno.setAnnotations(annotations);

    // anno.disableEditor = true;
    anno.on('createAnnotation', function (anno) {
      console.info('Created', anno);
    });

    anno.on('updateAnnotation', function (anno) {
      console.info('Updated', anno);
    });

    //anno.readOnly = true;
    //anno.setDrawingTool('polygon')

    function flashElement(el) {
      el.classList.add('outline', 'outline-2', 'outline-offset-2', 'outline-fuchsia-300/50', 'dark:outline-fuchsia-500/50');
      return setTimeout(function () {
        el.classList.remove('outline', 'outline-2', 'outline-offset-2', 'outline-fuchsia-300/50', 'dark:outline-fuchsia-500/50');
      }, 2000);
    }

    anno.on('clickAnnotation', function (anno) {
      const els = findInPageElementsMatchingBodySelector(anno.body);
      els.map(flashElement);
    });

    return anno;
  }

  /**
   * Expands a local in-page annotation into full web annotation form,
   * creating bodies from DOM elements assigned specified ID.
   *
   * ``frag`` is used as fragment selector value.
   *
   * Bodies will reference in-page DOM elements, which are expected to have
   * ``data-annotation-id=<given annotation ID>`` attribute.
   * Those elements’ contents will be used as bodies by
   * corresponding custom Annotorious widget ``makeInPageAnnotationBody()``.
   */
  function readInPageAnnotation(inPageAnn) {
    return {
      '@context': 'http://www.w3.org/ns/anno.jsonld',
      type: 'Annotation',
      id: `#${inPageAnn.id}`,
      body: [{
        type: 'SpecificResource',
        purpose: 'annotating',
        source: '#', // this page
        selector: [{
          type: 'CssSelector',
          value: inPageAnn.cssSelector,
        }],
      }],
      target: {
        selector: {
          type: 'FragmentSelector',
          conformsTo: 'http://www.w3.org/TR/media-frags/',
          value: inPageAnn.frag,
        },
      },
    };
  }

  function initializeAllAnnotatedImages() {
    const els = document.querySelectorAll('[data-in-page-annotations]');
    for (const el of els) {
      let inPageAnnos;
      try {
        inPageAnnos = JSON.parse(el.dataset.inPageAnnotations);
      } catch (e) {
        console.error("Unable to parse annotations", e);
        inPageAnnos = null;
      }
      if (inPageAnnos) {
        const annotations = inPageAnnos.map(readInPageAnnotation);
        initializeAnnotator(el, annotations);
      }
    }
  }

  initializeAllAnnotatedImages();

})();
