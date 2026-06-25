(function () {
  var header = document.querySelector(".site-header");
  var cards = Array.prototype.slice.call(
    document.querySelectorAll("[data-article-card]")
  );
  var filterButtons = Array.prototype.slice.call(
    document.querySelectorAll("[data-filter]")
  );
  var searchInput = document.querySelector("[data-article-search]");

  function updateHeader() {
    if (!header) return;
    header.classList.toggle("is-scrolled", window.scrollY > 12);
  }

  function normalize(value) {
    return (value || "").toString().toLowerCase();
  }

  function updateArticles() {
    if (!cards.length) return;
    var activeButton =
      filterButtons.find(function (button) {
        return button.classList.contains("is-active");
      }) || filterButtons[0];
    var activeFilter = activeButton ? activeButton.dataset.filter : "all";
    var query = normalize(searchInput ? searchInput.value : "");

    cards.forEach(function (card) {
      var niche = card.dataset.niche || "";
      var text = normalize(card.dataset.title);
      var matchesFilter = activeFilter === "all" || niche === activeFilter;
      var matchesSearch = !query || text.indexOf(query) !== -1;
      card.hidden = !(matchesFilter && matchesSearch);
    });
  }

  filterButtons.forEach(function (button) {
    button.addEventListener("click", function () {
      filterButtons.forEach(function (item) {
        item.classList.remove("is-active");
      });
      button.classList.add("is-active");
      updateArticles();
    });
  });

  if (searchInput) {
    searchInput.addEventListener("input", updateArticles);
  }

  if ("IntersectionObserver" in window) {
    var observer = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-visible");
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.12 }
    );
    document.querySelectorAll(".reveal-on-scroll").forEach(function (item) {
      observer.observe(item);
    });
  } else {
    document.querySelectorAll(".reveal-on-scroll").forEach(function (item) {
      item.classList.add("is-visible");
    });
  }

  window.addEventListener("scroll", updateHeader, { passive: true });
  updateHeader();
  updateArticles();
})();
