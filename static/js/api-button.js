(function () {

  var apiSecret = document.documentElement.dataset['api-secret'];

  function callIndexerAPI (url, method) {
    fetch(url, {
      method: method,
      headers: {
        'X-IETF-Token': apiSecret,
      },
    }).then(function () { document.location.reload() });
  }

  if (apiSecret) {
    document.querySelectorAll('[data-api-endpoint]').forEach(function (el) {
      var label = el.dataset['api-action-label'];
      var url = el.dataset['api-endpoint'];
      var meth = el.dataset['api-method'];
      if (url && meth) {
        el.classList.add('link');
        el.classList.add('dim');
        el.style.cursor = 'pointer';
        el.innerHTML = label;
        el.setAttribute('role', 'button');
        el.addEventListener('click', function () {
          callIndexerAPI(url, meth);
        });
      }
    });
  }

})();
