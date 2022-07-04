(function () {
  const copyButtonSVG = `
    <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
      <path d="M8 3a1 1 0 011-1h2a1 1 0 110 2H9a1 1 0 01-1-1z" />
      <path d="M6 3a2 2 0 00-2 2v11a2 2 0 002 2h8a2 2 0 002-2V5a2 2 0 00-2-2 3 3 0 01-3 3H9a3 3 0 01-3-3z" />
    </svg>
  `;
  const selectButtonSVG = `
    <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
      <path fill-rule="evenodd" d="M6.672 1.911a1 1 0 10-1.932.518l.259.966a1 1 0 001.932-.518l-.26-.966zM2.429 4.74a1 1 0 10-.517 1.932l.966.259a1 1 0 00.517-1.932l-.966-.26zm8.814-.569a1 1 0 00-1.415-1.414l-.707.707a1 1 0 101.415 1.415l.707-.708zm-7.071 7.072l.707-.707A1 1 0 003.465 9.12l-.708.707a1 1 0 001.415 1.415zm3.2-5.171a1 1 0 00-1.3 1.3l4 10a1 1 0 001.823.075l1.38-2.759 3.018 3.02a1 1 0 001.414-1.415l-3.019-3.02 2.76-1.379a1 1 0 00-.076-1.822l-10-4z" clip-rule="evenodd" />
    </svg>
  `;

  function appendButton(el, title, iconHTML, clickHandler) {
    const btnEl = document.createElement('span');
    btnEl.setAttribute('class', el.dataset.copyButtonClass ?? '');
    btnEl.setAttribute('title', title);
    btnEl.innerHTML = iconHTML;
    btnEl.addEventListener('click', clickHandler);
    el.appendChild(btnEl);
    btnEl.classList.add('cursor-pointer');
  }

  function autoExpand(el) {
    const input = el.querySelector('input');
    const short = document.createElement('span');
    short.setAttribute('class', input.getAttribute('class'));
    short.innerText = el.dataset.xml2rfcSubpath;
    el.prepend(short);
    input.classList.add('hidden');
    el.addEventListener('mouseenter', () => {
      short.classList.add('hidden');
      input.classList.remove('hidden');
    });
    el.addEventListener('mouseleave', () => {
      input.classList.add('hidden');
      short.classList.remove('hidden');
    });
  }

  function initCopyWidget(el) {
    const subpath = el.dataset.xml2rfcSubpath;
    const fullURL = el.dataset.fullUrl;
    const input = el.querySelector('input');

    function handleXml2rfcUrlCopy() {
      input.select();
      navigator.clipboard.writeText(fullURL).then(function() {
        console.info("Copied xml2rfc path to clipboard");
      }, function(err) {
        console.error("Couldn’t copy xml2rfc path to clipboard", fullURL, err);
      });
    }

    if (subpath && fullURL) {
      appendButton(
        el,
        "Copy this xml2rfc URL to clipboard",
        copyButtonSVG,
        handleXml2rfcUrlCopy,
      );
    } else {
      console.warning("Cannot initialize copy xml2rfc path widget: missing data attributes", el);
    }
  }

  function initSelectWidget(el) {
    const input = el.querySelector('input');
    appendButton(
      el,
      "Select this xml2rfc URL",
      selectButtonSVG,
      function () { input.select() },
    );
  }

  const els = document.querySelectorAll('[data-xml2rfc-subpath]')

  els.forEach(autoExpand);
  if (navigator.permissions) {
    navigator.permissions.query({name: "clipboard-write"}).then(result => {
      if (result.state == "granted" || result.state == "prompt") {
        els.forEach(initCopyWidget);
      } else {
        els.forEach(initSelectWidget);
      }
    });
  } else {
    els.forEach(initCopyWidget);
  }
})();
