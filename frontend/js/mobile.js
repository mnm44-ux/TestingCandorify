/* Optional mobile bridge. This file is harmless on the web (Capacitor globals
 * simply won't exist) and adds native behaviors when running inside the app:
 *   - Android hardware back button navigates views instead of closing the app
 *   - Deep-link return from Stripe hosted checkout (candorify://payment-return)
 * The Capacitor plugins are loaded by the native shell; we access them via the
 * global `Capacitor` object if present.
 */
(function () {
  var Cap = window.Capacitor;
  if (!Cap || !Cap.isNativePlatform || !Cap.isNativePlatform()) return; // web: no-op

  document.addEventListener("DOMContentLoaded", function () {
    var App = Cap.Plugins && Cap.Plugins.App;
    if (!App) return;

    // Hardware back button: go home, or exit if already home.
    App.addListener("backButton", function () {
      var home = document.getElementById("view-home");
      if (home && home.classList.contains("active")) {
        App.exitApp();
      } else {
        var homeBtn = document.querySelector('nav.top button[data-view="home"]');
        if (homeBtn) homeBtn.click();
      }
    });

    // Deep link back from Stripe hosted checkout in the in-app browser.
    App.addListener("appUrlOpen", function (data) {
      try {
        var url = new URL(data.url);
        var sid = url.searchParams.get("session_id");
        if (sid && window.CandorifyAPI) {
          window.CandorifyAPI.confirmCheckout(sid).then(function () {
            window.location.reload();
          });
        }
      } catch (e) { /* ignore */ }
    });
  });
})();
