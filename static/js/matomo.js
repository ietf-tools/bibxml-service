var MATOMO_URL = document.documentElement.getAttribute('data-matomo-url');
var MATOMO_SITE_ID = document.documentElement.getAttribute('data-matomo-site-id');
var MTM_CONTAINER = document.documentElement.getAttribute('data-matomo-tag-manager-container');

if (MATOMO_URL && MTM_CONTAINER) {
  var _mtm = window._mtm = window._mtm || [];
  _mtm.push({'mtm.startTime': (new Date().getTime()), 'event': 'mtm.Start'});
  var d=document, g=d.createElement('script'), s=d.getElementsByTagName('script')[0];
  g.type='text/javascript'; g.async=true; g.src=`https://${MATOMO_URL}/js/container_${MTM_CONTAINER}.js`; s.parentNode.insertBefore(g,s);
} else if (MATOMO_URL && MATOMO_SITE_ID) {
  var _paq = window._paq = window._paq || [];
  _paq.push(['trackPageView']);
  _paq.push(['enableLinkTracking']);
  (function() {
    var u=`//${MATOMO_URL}/`;
    _paq.push(['setTrackerUrl', u+'matomo.php']);
    _paq.push(['setSiteId', MATOMO_SITE_ID]);
    var d=document, g=d.createElement('script'), s=d.getElementsByTagName('script')[0];
    g.type='text/javascript'; g.async=true; g.src=u+'matomo.js'; s.parentNode.insertBefore(g,s);
  })();
}
