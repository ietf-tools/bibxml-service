(function () {

  const apiSecret = document.documentElement.dataset['api-secret'];

  function callIndexerAPI (url, method) {
    fetch(url, {
      method: method,
      headers: {
        'X-IETF-Token': apiSecret,
      },
    }).then(function () { document.location.reload() });
  }

  function makeClickableButton (el) {
    const label = el.dataset['api-action-label'];
    const url = el.dataset['api-endpoint'];
    const meth = el.dataset['api-method'];
    if (url && meth) {
      el.classList.add('link');
      el.classList.add('dim');
      el.style.cursor = 'pointer';
      el.innerHTML = label;
      el.setAttribute('role', 'button');
      el.addEventListener('click', function () {
        callIndexerAPI(url, meth);
      });
    } else {
      console.warn("Invalid data API endpoint", el);
    }
  }

  if (apiSecret) {
    document.querySelectorAll('[data-api-endpoint]').forEach(makeClickableButton);
  }

})();
