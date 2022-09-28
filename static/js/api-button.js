(function () {

  const apiSecret = document.documentElement.dataset['api-secret'];

  function callIndexerAPI (url, method, urlParams) {
    if (urlParams) {
      url = `${url}?${urlParams}`
    }
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

    let getQuery;
    const getQueryJSON = el.dataset['api-get-query'];
    if (getQueryJSON) {
      try {
        getQuery = new URLSearchParams(JSON.parse(getQueryJSON));
      } catch (e) {
        console.error("Failed to parse GET parameters", e, getQueryJSON);
        throw e;
      }
    } else {
      getQuery = undefined;
    }

    if (url && meth) {
      el.classList.add('button');
      el.style.cursor = 'pointer';
      el.innerHTML = label;
      el.setAttribute('role', 'button');
      el.addEventListener('click', function () {
        callIndexerAPI(url, meth, getQuery);
      });
    } else {
      console.warn("Invalid data API endpoint", el);
    }
  }

  if (apiSecret) {
    document.querySelectorAll('[data-api-endpoint]').forEach(makeClickableButton);
  }

})();
