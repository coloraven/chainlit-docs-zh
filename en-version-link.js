/**
 * Injects a per-page "英文原文" link in the top navbar, immediately left of Github.
 * Mintlify auto-includes .js files from the content directory site-wide.
 */
(function () {
  var OFFICIAL_BASE = "https://docs.chainlit.io";
  var LINK_ID = "chainlit-en-version-link";
  var GITHUB_HREF = "github.com/Chainlit/chainlit";
  var lastInjectedPath = "";

  function toEnglishSlug(pathname) {
    var path = pathname.replace(/^\/+|\/+$/g, "");
    if (path.indexOf("zh/") === 0) {
      path = path.slice(3);
    }
    return path;
  }

  function buildEnglishUrl(slug) {
    return slug ? OFFICIAL_BASE + "/" + slug : OFFICIAL_BASE;
  }

  function findGithubListItem() {
    var anchors = document.querySelectorAll("li.navbar-link a");
    for (var i = 0; i < anchors.length; i++) {
      var href = anchors[i].getAttribute("href") || "";
      var text = (anchors[i].textContent || "").trim();
      if (href.indexOf(GITHUB_HREF) !== -1 || /^github$/i.test(text)) {
        return anchors[i].closest("li.navbar-link");
      }
    }
    return null;
  }

  function getGithubAnchorClass() {
    var githubAnchor = document.querySelector(
      'li.navbar-link a[href*="' + GITHUB_HREF + '"]'
    );
    return githubAnchor
      ? githubAnchor.className
      : "flex items-center gap-1.5 whitespace-nowrap font-medium text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-300";
  }

  function removeMisplacedLink() {
    var el = document.getElementById(LINK_ID);
    if (!el) {
      return;
    }

    var githubLi = findGithubListItem();
    if (githubLi && el.nextElementSibling === githubLi) {
      return;
    }

    el.remove();
  }

  function inject() {
    var pathname = window.location.pathname;
    var url = buildEnglishUrl(toEnglishSlug(pathname));
    var githubLi = findGithubListItem();

    if (!githubLi || !githubLi.parentNode) {
      return false;
    }

    removeMisplacedLink();

    var el = document.getElementById(LINK_ID);
    if (!el) {
      el = document.createElement("li");
      el.id = LINK_ID;
      el.className = "navbar-link";

      var anchor = document.createElement("a");
      anchor.className = getGithubAnchorClass();
      anchor.target = "_blank";
      anchor.rel = "noopener noreferrer";
      anchor.textContent = "英文原文";
      el.appendChild(anchor);
    }

    var link = el.querySelector("a");
    if (link) {
      link.href = url;
      link.className = getGithubAnchorClass();
    }

    if (el.nextElementSibling !== githubLi) {
      githubLi.parentNode.insertBefore(el, githubLi);
    }

    lastInjectedPath = pathname;
    return true;
  }

  function scheduleInject() {
    requestAnimationFrame(function () {
      inject();
    });
  }

  function patchHistory(method) {
    var original = history[method];
    history[method] = function () {
      var result = original.apply(this, arguments);
      scheduleInject();
      return result;
    };
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", scheduleInject);
  } else {
    scheduleInject();
  }

  window.addEventListener("popstate", scheduleInject);
  patchHistory("pushState");
  patchHistory("replaceState");

  var observer = new MutationObserver(function () {
    if (
      window.location.pathname !== lastInjectedPath ||
      !document.getElementById(LINK_ID)
    ) {
      scheduleInject();
    }
  });

  observer.observe(document.documentElement, {
    childList: true,
    subtree: true,
  });
})();
