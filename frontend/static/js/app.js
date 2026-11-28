(() => {
  const placeholder = "/static/images/movie-placeholder.svg";

  // Watchlist storage helper
  function loadWatchlist() {
    try {
      const saved = localStorage.getItem("cinesuggest_watchlist");
      return new Set(saved ? JSON.parse(saved) : []);
    } catch {
      return new Set();
    }
  }

  function saveWatchlist(watchlist) {
    try {
      localStorage.setItem("cinesuggest_watchlist", JSON.stringify([...watchlist]));
    } catch (e) {
      console.warn("Could not save watchlist to localStorage", e);
    }
  }

  // Liked movies storage helper (used for AI taste matching)
  function loadLikedMovies() {
    try {
      const saved = localStorage.getItem("cinesuggest_liked_movies");
      return new Set(saved ? JSON.parse(saved) : []);
    } catch {
      return new Set();
    }
  }

  function saveLikedMovies(liked) {
    try {
      localStorage.setItem("cinesuggest_liked_movies", JSON.stringify([...liked]));
    } catch (e) {
      console.warn("Could not save liked movies to localStorage", e);
    }
  }

  const state = {
    movies: new Map(),
    watchlist: loadWatchlist(),
    likedMovies: loadLikedMovies(),
    activeFilterTab: "all", // "all" | "watchlist"
    activeMovieId: null,
    spotlightMovieId: null,
  };

  const byId = (id) => document.getElementById(id);
  const escapeHtml = (value) =>
    String(value ?? "Not available").replace(
      /[&<>'"]/g,
      (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", "\"": "&quot;" }[char])
    );
  const text = (value, fallback = "Not available") => String(value ?? "").trim() || fallback;
  const genresFor = (movie) =>
    Array.isArray(movie.genres) && movie.genres.length ? movie.genres : ["Not available"];
  const languagesFor = (movie) =>
    text(movie.language, "")
      .split(/[,;/|]+/)
      .map((val) => val.trim())
      .filter(Boolean);

  const numericRating = (value) => {
    if (value === null || value === undefined || value === "" || value === "Not available") return null;
    const rating = Number(value);
    return Number.isFinite(rating) && rating > 0 ? rating : null;
  };

  const safeUrl = (value) => (/^https?:\/\//i.test(String(value || "")) ? value : "");

  // Toast Notification System
  function showToast(message, type = "info") {
    const container = byId("toast-container");
    if (!container) return;
    const toast = document.createElement("div");
    toast.className = `toast ${type === "success" ? "toast-success" : ""}`;
    toast.innerHTML = `<span>${type === "success" ? "✓" : "ℹ"}</span><span>${escapeHtml(message)}</span>`;
    container.append(toast);
    setTimeout(() => {
      toast.style.opacity = "0";
      toast.style.transform = "translateY(10px)";
      toast.style.transition = "all 0.25s ease";
      setTimeout(() => toast.remove(), 260);
    }, 3200);
  }

  async function fetchJson(url, options = {}) {
    const response = await fetch(url, options);
    const data = await response.json().catch(() => ({}));
    if (!response.ok || !data.success) {
      throw new Error(data.message || "Something went wrong. Please try again.");
    }
    return data;
  }

  function setStatus(id, message = "", type = "info") {
    const target = byId(id);
    if (!target) return;
    target.textContent = message;
    target.className = "status-msg";
    if (type === "error") target.classList.add("error");
    if (type === "success") target.classList.add("success");
  }

  function setButtonBusy(button, busy, busyLabel) {
    if (!button) return;
    button.disabled = busy;
    if (busy) {
      button.dataset.originalHtml = button.innerHTML;
      button.innerHTML = `<span>${busyLabel}</span> <span class="spinner" aria-hidden="true">⏳</span>`;
    } else if (button.dataset.originalHtml) {
      button.innerHTML = button.dataset.originalHtml;
    }
  }

  function updateWatchlistBadges() {
    const count = state.watchlist.size;
    const navCount = byId("nav-watchlist-count");
    const tabCount = byId("tab-watchlist-badge");
    if (navCount) navCount.textContent = count;
    if (tabCount) tabCount.textContent = count;
  }

  function toggleWatchlist(movieId) {
    const movie = state.movies.get(movieId);
    if (!movie) return;

    if (state.watchlist.has(movieId)) {
      state.watchlist.delete(movieId);
      showToast(`Removed "${movie.title}" from watchlist.`);
    } else {
      state.watchlist.add(movieId);
      showToast(`Added "${movie.title}" to your watchlist!`, "success");
    }
    saveWatchlist(state.watchlist);
    updateWatchlistBadges();

    // Re-render cards and modal watchlist buttons
    document.querySelectorAll(`.card-watchlist-btn[data-movie-id="${movieId}"]`).forEach((btn) => {
      btn.classList.toggle("active", state.watchlist.has(movieId));
      btn.setAttribute("aria-label", state.watchlist.has(movieId) ? "Remove from watchlist" : "Add to watchlist");
    });

    const modalWatchlistBtn = document.querySelector(`.btn-modal-watchlist[data-movie-id="${movieId}"]`);
    if (modalWatchlistBtn) {
      const inList = state.watchlist.has(movieId);
      modalWatchlistBtn.classList.toggle("active", inList);
      modalWatchlistBtn.innerHTML = inList
        ? `<span>❤️ In Watchlist</span>`
        : `<span>🤍 Add to Watchlist</span>`;
    }

    if (state.activeFilterTab === "watchlist") {
      renderMovies();
    }
  }

  // Toggle movie in liked/selected taste list
  function toggleLikedMovie(movieTitle) {
    const title = text(movieTitle);
    if (!title) return;

    if (state.likedMovies.has(title)) {
      state.likedMovies.delete(title);
      showToast(`Removed "${title}" from your liked movies.`);
    } else {
      state.likedMovies.add(title);
      showToast(`Added "${title}" to your liked movies for AI taste matching!`, "success");
    }
    saveLikedMovies(state.likedMovies);
    updateTasteSelectionUI();
  }

  function updateTasteSelectionUI() {
    const count = state.likedMovies.size;
    const badge = byId("selected-movies-badge");
    const clearBtn = byId("clear-selected-movies-btn");
    const btnLabel = byId("recommend-btn-label");

    if (badge) {
      badge.textContent = `${count} movie${count === 1 ? "" : "s"} selected`;
    }
    if (clearBtn) {
      clearBtn.hidden = count === 0;
    }
    if (btnLabel) {
      btnLabel.textContent = count > 0
        ? `✦ Analyze Taste & Recommend (${count} selected)`
        : `✦ Analyze Taste & Recommend`;
    }

    // Update movie card like buttons
    document.querySelectorAll(".card-like-btn").forEach((btn) => {
      const t = btn.dataset.movieTitle;
      const isLiked = state.likedMovies.has(t);
      btn.classList.toggle("active", isLiked);
      btn.title = isLiked ? "Liked (Click to remove from AI taste)" : "Like this movie (Adds to AI taste)";
    });

    renderSelectedMoviesTray();
    renderMovieSelectorPills();
  }

  function renderSelectedMoviesTray() {
    const tray = byId("selected-movies-tray");
    if (!tray) return;

    if (state.likedMovies.size === 0) {
      tray.hidden = true;
      tray.replaceChildren();
      return;
    }

    tray.hidden = false;
    tray.replaceChildren();

    state.likedMovies.forEach((title) => {
      const tag = document.createElement("span");
      tag.className = "selected-movie-tag";
      tag.innerHTML = `
        <span>${escapeHtml(title)}</span>
        <button type="button" class="selected-movie-tag-close" data-title="${escapeHtml(title)}" title="Remove ${escapeHtml(title)}">×</button>
      `;
      tag.querySelector(".selected-movie-tag-close").addEventListener("click", () => {
        toggleLikedMovie(title);
      });
      tray.append(tag);
    });
  }

  function renderMovieSelectorPills() {
    const container = byId("movie-selector-pills");
    if (!container) return;

    const filterVal = (byId("taste-movie-search")?.value || "").trim().toLowerCase();
    const allMovies = [...state.movies.values()];

    container.replaceChildren();

    const matching = allMovies.filter((m) => {
      if (!filterVal) return true;
      return (
        m.title.toLowerCase().includes(filterVal) ||
        (m.director && m.director.toLowerCase().includes(filterVal)) ||
        genresFor(m).some((g) => g.toLowerCase().includes(filterVal))
      );
    });

    if (matching.length === 0) {
      const empty = document.createElement("span");
      empty.className = "text-muted";
      empty.style.padding = "8px";
      empty.textContent = "No movies match your search in the library.";
      container.append(empty);
      return;
    }

    matching.forEach((movie) => {
      const isSelected = state.likedMovies.has(movie.title);
      const pill = document.createElement("button");
      pill.type = "button";
      pill.className = `taste-movie-pill ${isSelected ? "selected" : ""}`;
      pill.innerHTML = `
        <span class="pill-check">${isSelected ? "✓" : "+"}</span>
        <span>${escapeHtml(movie.title)}</span>
        <small style="opacity: 0.65;">(${escapeHtml(text(movie.year))})</small>
      `;
      pill.addEventListener("click", () => {
        toggleLikedMovie(movie.title);
      });
      container.append(pill);
    });
  }

  function recommendSimilarTo(movieTitle) {
    if (!state.likedMovies.has(movieTitle)) {
      state.likedMovies.add(movieTitle);
      saveLikedMovies(state.likedMovies);
      updateTasteSelectionUI();
    }
    showToast(`Finding movies similar to "${movieTitle}"...`, "success");
    const curatorSection = byId("curator-section");
    if (curatorSection) {
      curatorSection.scrollIntoView({ behavior: "smooth" });
    }
    setTimeout(() => {
      byId("recommend-form").dispatchEvent(new Event("submit"));
    }, 400);
  }

  function posterArtwork(movie) {
    const remotePoster = safeUrl(movie.poster_url);
    if (remotePoster) {
      const img = document.createElement("img");
      img.src = remotePoster;
      img.alt = `${movie.title} poster`;
      img.loading = "lazy";
      img.addEventListener("error", () => {
        img.src = placeholder;
      });
      return img;
    }

    const artwork = document.createElement("div");
    const title = text(movie.title);
    const tone = [...title].reduce((total, character) => total + character.charCodeAt(0), 0) % 6;
    artwork.className = `poster-fallback poster-tone-${tone}`;
    artwork.setAttribute("role", "img");
    artwork.setAttribute("aria-label", `${title} poster artwork`);
    artwork.innerHTML = `
      <span class="poster-monogram">${escapeHtml(title.charAt(0))}</span>
      <strong>${escapeHtml(title)}</strong>
      <small>${escapeHtml(genresFor(movie)[0])} • ${escapeHtml(text(movie.year))}</small>
    `;
    return artwork;
  }

  function movieCard(movie) {
    const card = document.createElement("article");
    card.className = "movie-card";
    card.dataset.id = movie.id;

    const posterWrap = document.createElement("div");
    posterWrap.className = "card-poster-wrap";
    posterWrap.append(posterArtwork(movie));

    // Rating badge
    const rating = numericRating(movie.rating);
    if (rating) {
      const ratingBadge = document.createElement("div");
      ratingBadge.className = "card-badge-rating";
      ratingBadge.innerHTML = `★ ${rating.toFixed(1)}`;
      posterWrap.append(ratingBadge);
    }

    // Like button (Thumbs-up / Heart for taste profile)
    const isLiked = state.likedMovies.has(movie.title);
    const likeBtn = document.createElement("button");
    likeBtn.type = "button";
    likeBtn.className = `card-like-btn ${isLiked ? "active" : ""}`;
    likeBtn.dataset.movieTitle = movie.title;
    likeBtn.title = isLiked ? "Liked (Click to remove from AI taste)" : "Like this movie (Adds to AI taste)";
    likeBtn.innerHTML = `👍`;
    likeBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      toggleLikedMovie(movie.title);
    });
    posterWrap.append(likeBtn);

    // Watchlist Heart Button
    const isSaved = state.watchlist.has(movie.id);
    const watchlistBtn = document.createElement("button");
    watchlistBtn.type = "button";
    watchlistBtn.className = `card-watchlist-btn ${isSaved ? "active" : ""}`;
    watchlistBtn.dataset.movieId = movie.id;
    watchlistBtn.setAttribute("aria-label", isSaved ? "Remove from watchlist" : "Add to watchlist");
    watchlistBtn.title = isSaved ? "Remove from watchlist" : "Save to watchlist";
    watchlistBtn.innerHTML = `
      <svg width="15" height="15" viewBox="0 0 24 24" fill="currentColor">
        <path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z"/>
      </svg>
    `;
    watchlistBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      toggleWatchlist(movie.id);
    });
    posterWrap.append(watchlistBtn);

    const body = document.createElement("div");
    body.className = "card-body";
    body.innerHTML = `
      <h3 class="card-title" title="${escapeHtml(movie.title)}">${escapeHtml(movie.title)}</h3>
      <div class="card-meta">
        <span>${escapeHtml(text(movie.year))}</span>
        <span>${escapeHtml(genresFor(movie)[0])}</span>
        <span>${escapeHtml(text(movie.language))}</span>
      </div>
      <div class="card-actions">
        <button class="btn-card-details" type="button">Details</button>
        <button class="btn-card-summary" type="button">✦ Summary</button>
        <button class="btn-card-similar" type="button" title="Find movies like ${escapeHtml(movie.title)}">✦ Similar</button>
      </div>
    `;

    body.querySelector(".btn-card-details").addEventListener("click", () => openModal(movie.id));
    body.querySelector(".btn-card-summary").addEventListener("click", (e) => {
      requestSummary(movie.id, false, e.currentTarget);
    });
    body.querySelector(".btn-card-similar").addEventListener("click", () => {
      recommendSimilarTo(movie.title);
    });

    card.append(posterWrap, body);
    return card;
  }

  function renderSpotlight() {
    const spotlightSec = byId("spotlight-section");
    const container = byId("spotlight-card");
    if (!spotlightSec || !container) return;

    const sorted = [...state.movies.values()].sort((a, b) => (numericRating(b.rating) ?? 0) - (numericRating(a.rating) ?? 0));
    const featured = sorted[0];
    if (!featured) {
      spotlightSec.hidden = true;
      return;
    }

    state.spotlightMovieId = featured.id;
    spotlightSec.hidden = false;
    container.innerHTML = "";

    const posterWrap = document.createElement("div");
    posterWrap.className = "spotlight-poster";
    posterWrap.append(posterArtwork(featured));

    const body = document.createElement("div");
    body.className = "spotlight-body";
    const rating = numericRating(featured.rating);
    const trailerUrl = `https://www.youtube.com/results?search_query=${encodeURIComponent(featured.title + " " + (featured.year || "") + " trailer")}`;

    body.innerHTML = `
      <div class="spotlight-tag">★ SPOTLIGHT FILM OF THE DAY</div>
      <h2 class="spotlight-title">${escapeHtml(featured.title)}</h2>
      <div class="spotlight-meta">
        ${rating ? `<span class="rating-badge">★ ${rating.toFixed(1)} IMDb</span>` : ""}
        <span>${escapeHtml(text(featured.year))}</span>
        <span>${escapeHtml(genresFor(featured).join(", "))}</span>
        <span>${escapeHtml(text(featured.duration))}</span>
        <span>${escapeHtml(text(featured.language))}</span>
      </div>
      <p class="spotlight-desc">${escapeHtml(text(featured.description))}</p>
      <div class="spotlight-actions">
        <button type="button" class="btn-primary" id="spotlight-details-btn">
          <span>Explore Details</span>
          <span aria-hidden="true">→</span>
        </button>
        <a href="${escapeHtml(trailerUrl)}" target="_blank" rel="noopener noreferrer" class="btn-ghost" title="Watch official trailer on YouTube">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
            <path d="M19.615 3.184c-3.604-.246-11.631-.245-15.23 0-3.897.266-4.356 2.62-4.385 8.816.029 6.185.484 8.549 4.385 8.816 3.6.245 11.626.246 15.23 0 3.897-.266 4.356-2.62 4.385-8.816-.029-6.185-.484-8.549-4.385-8.816zm-10.615 12.816v-8l8 3.993-8 4.007z"/>
          </svg>
          <span>Watch Trailer ↗</span>
        </a>
        <button type="button" class="btn-ghost" id="spotlight-similar-btn">
          <span>✦ AI Taste Match</span>
        </button>
      </div>
    `;

    body.querySelector("#spotlight-details-btn").addEventListener("click", () => openModal(featured.id));
    body.querySelector("#spotlight-similar-btn").addEventListener("click", () => {
      recommendSimilarTo(featured.title);
    });

    container.append(posterWrap, body);
  }

  function populateFilters() {
    const movies = [...state.movies.values()];
    const genreSelect = byId("genre-filter");
    const langSelect = byId("language-filter");

    const currentGenre = genreSelect.value;
    const currentLang = langSelect.value;

    const allGenres = new Set(movies.flatMap(genresFor).filter((val) => val && val !== "Not available"));
    const allLangs = new Set(movies.flatMap(languagesFor));

    genreSelect.innerHTML = '<option value="">All Genres</option>';
    [...allGenres].sort().forEach((genre) => {
      const opt = document.createElement("option");
      opt.value = genre;
      opt.textContent = genre;
      genreSelect.append(opt);
    });
    if ([...genreSelect.options].some((o) => o.value === currentGenre)) {
      genreSelect.value = currentGenre;
    }

    langSelect.innerHTML = '<option value="">All Languages</option>';
    [...allLangs].sort().forEach((lang) => {
      const opt = document.createElement("option");
      opt.value = lang;
      opt.textContent = lang;
      langSelect.append(opt);
    });
    if ([...langSelect.options].some((o) => o.value === currentLang)) {
      langSelect.value = currentLang;
    }
  }

  function renderMovies() {
    const grid = byId("movie-grid");
    if (!grid) return;

    const genre = byId("genre-filter").value.toLowerCase();
    const language = byId("language-filter").value.toLowerCase();
    const minRating = Number(byId("rating-filter").value) || 0;
    const filterQuery = (byId("library-filter-input")?.value || "").trim().toLowerCase();
    const sortBy = byId("sort-filter")?.value || "newest";

    let list = [...state.movies.values()];

    if (state.activeFilterTab === "watchlist") {
      list = list.filter((m) => state.watchlist.has(m.id));
    }

    list = list.filter((movie) => {
      const matchGenre = !genre || genresFor(movie).some((g) => g.toLowerCase() === genre);
      const matchLang = !language || languagesFor(movie).some((l) => l.toLowerCase() === language);
      const matchRating = (numericRating(movie.rating) ?? 0) >= minRating;

      let matchText = true;
      if (filterQuery) {
        const titleMatch = (movie.title || "").toLowerCase().includes(filterQuery);
        const directorMatch = (movie.director || "").toLowerCase().includes(filterQuery);
        const castMatch = (Array.isArray(movie.cast) ? movie.cast.join(" ") : "").toLowerCase().includes(filterQuery);
        matchText = titleMatch || directorMatch || castMatch;
      }

      return matchGenre && matchLang && matchRating && matchText;
    });

    if (sortBy === "rating_desc") {
      list.sort((a, b) => (numericRating(b.rating) ?? 0) - (numericRating(a.rating) ?? 0));
    } else if (sortBy === "year_desc") {
      list.sort((a, b) => (Number(b.year) || 0) - (Number(a.year) || 0));
    } else if (sortBy === "title_asc") {
      list.sort((a, b) => (a.title || "").localeCompare(b.title || ""));
    }

    grid.replaceChildren();

    if (!list.length) {
      const isWatchlist = state.activeFilterTab === "watchlist";
      grid.innerHTML = `
        <div class="empty-state">
          <div class="empty-state-icon">${isWatchlist ? "🤍" : "🎬"}</div>
          <p>${isWatchlist
            ? "Your watchlist is empty! Click the heart icon on any movie to save it here."
            : "No movies matched your current filters. Try resetting filters or searching above."}</p>
        </div>
      `;
    } else {
      list.forEach((movie) => grid.append(movieCard(movie)));
    }

    const totalCount = state.activeFilterTab === "watchlist" ? state.watchlist.size : state.movies.size;
    byId("movie-count").textContent = `Showing ${list.length} of ${totalCount} movies`;

    const hasActiveFilters = genre || language || minRating > 0 || filterQuery;
    const filterIndicator = byId("active-filter-indicator");
    if (filterIndicator) {
      filterIndicator.hidden = !hasActiveFilters;
    }
  }

  function addMovie(movie) {
    if (!movie || !movie.id) return;
    state.movies.set(movie.id, movie);
    populateFilters();
    renderMovies();
    renderMovieSelectorPills();
  }

  async function loadMovies() {
    setStatus("movies-status", "Connecting to database and loading movie library...");
    try {
      const data = await fetchJson("/api/movies?limit=100");
      state.movies.clear();
      data.movies.forEach((movie) => state.movies.set(movie.id, movie));
      populateFilters();
      renderMovies();
      renderSpotlight();
      renderMovieSelectorPills();
      updateTasteSelectionUI();
      setStatus("movies-status", "");
    } catch (error) {
      console.warn("loadMovies error:", error);
      setStatus("movies-status", error.message, "error");
    }
  }

  async function checkStats() {
    try {
      const data = await fetchJson("/api/stats");
      if (data.ai_enabled) {
        byId("ai-status-text").textContent = "AI Ready";
      }
    } catch {
      byId("ai-status-text").textContent = "Local Mode";
    }
  }

  function summaryMarkup(movie) {
    if (!movie.ai_summary) {
      return `
        <div class="ai-summary-card">
          <div class="ai-summary-header">
            <span class="ai-summary-title">✦ AI Spoiler-Free Summary</span>
          </div>
          <p class="ai-summary-text" style="color: var(--text-muted);">
            Generate a personalized, spoiler-free breakdown of key themes, mood, and audience recommendation powered by OpenRouter AI.
          </p>
          <button class="btn-primary btn-regenerate" type="button" data-trigger-summary="${escapeHtml(movie.id)}">
            <span>Generate Summary Now</span>
            <span aria-hidden="true">✦</span>
          </button>
        </div>
      `;
    }

    return `
      <div class="ai-summary-card">
        <div class="ai-summary-header">
          <span class="ai-summary-title">✦ AI Spoiler-Free Summary</span>
          <span class="ai-provider-pill">${escapeHtml(movie.summary_provider || "AI")}</span>
        </div>
        <p class="ai-summary-text">${escapeHtml(movie.ai_summary)}</p>
        <div class="ai-summary-tags">
          <div><b>Key Genre:</b> ${escapeHtml(text(movie.summary_genre))}</div>
          <div><b>Mood:</b> ${escapeHtml(text(movie.summary_mood))}</div>
          <div style="grid-column: 1 / -1;"><b>Best Suited For:</b> ${escapeHtml(text(movie.summary_suitable_for))}</div>
        </div>
        <button class="btn-regenerate" type="button" data-regenerate="${escapeHtml(movie.id)}">
          <span>⚡ Regenerate Summary</span>
        </button>
      </div>
    `;
  }

  function openModal(movieId) {
    const movie = state.movies.get(movieId);
    if (!movie) return;
    state.activeMovieId = movieId;

    const rating = numericRating(movie.rating);
    const source = safeUrl(movie.source_url);
    const isSaved = state.watchlist.has(movieId);
    const trailerUrl = `https://www.youtube.com/results?search_query=${encodeURIComponent(movie.title + " " + (movie.year || "") + " trailer")}`;

    const modalContent = byId("modal-content");
    modalContent.innerHTML = `
      <div class="modal-inner">
        <div class="modal-poster-wrap"></div>
        <div class="modal-content-body">
          <div class="modal-badge-row">
            <span class="modal-source-pill">${escapeHtml(text(movie.data_source, "CURATED"))}</span>
            ${rating ? `<span class="rating-badge">★ ${rating.toFixed(1)} IMDb</span>` : ""}
          </div>
          <h2 id="modal-title" class="modal-title">${escapeHtml(movie.title)}</h2>
          <div class="modal-genres">
            ${genresFor(movie).map((g) => `<span class="genre-chip">${escapeHtml(g)}</span>`).join("")}
          </div>

          <div class="modal-meta-grid">
            <div class="meta-item"><b>Released</b><span>${escapeHtml(text(movie.year))}</span></div>
            <div class="meta-item"><b>Runtime</b><span>${escapeHtml(text(movie.duration))}</span></div>
            <div class="meta-item"><b>Language</b><span>${escapeHtml(text(movie.language))}</span></div>
            <div class="meta-item"><b>Director</b><span>${escapeHtml(text(movie.director))}</span></div>
            <div class="meta-item" style="grid-column: 1 / -1;">
              <b>Cast</b>
              <span>${escapeHtml((Array.isArray(movie.cast) ? movie.cast : ["Not available"]).join(", "))}</span>
            </div>
          </div>

          <p class="modal-synopsis">${escapeHtml(text(movie.description))}</p>

          <div class="modal-action-bar">
            <a href="${escapeHtml(trailerUrl)}" target="_blank" rel="noopener noreferrer" class="btn-trailer" title="Watch trailer on YouTube">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                <path d="M19.615 3.184c-3.604-.246-11.631-.245-15.23 0-3.897.266-4.356 2.62-4.385 8.816.029 6.185.484 8.549 4.385 8.816 3.6.245 11.626.246 15.23 0 3.897-.266 4.356-2.62 4.385-8.816-.029-6.185-.484-8.549-4.385-8.816zm-10.615 12.816v-8l8 3.993-8 4.007z"/>
              </svg>
              <span>Watch Trailer ↗</span>
            </a>

            <button type="button" class="btn-modal-watchlist ${isSaved ? "active" : ""}" data-movie-id="${escapeHtml(movieId)}">
              <span>${isSaved ? "❤️ In Watchlist" : "🤍 Add to Watchlist"}</span>
            </button>

            <button type="button" class="btn-ghost" id="modal-similar-btn" title="Find movies similar to ${escapeHtml(movie.title)}">
              <span>✦ Find Similar</span>
            </button>

            ${source ? `<a class="source-anchor" href="${escapeHtml(source)}" target="_blank" rel="noopener noreferrer">Wikipedia Source ↗</a>` : ""}
          </div>

          ${summaryMarkup(movie)}
        </div>
      </div>
    `;

    modalContent.querySelector(".modal-poster-wrap").append(posterArtwork(movie));

    modalContent.querySelector(".btn-modal-watchlist").addEventListener("click", () => {
      toggleWatchlist(movieId);
    });

    modalContent.querySelector("#modal-similar-btn").addEventListener("click", () => {
      closeModal();
      recommendSimilarTo(movie.title);
    });

    const triggerSummary = modalContent.querySelector("[data-trigger-summary]");
    if (triggerSummary) {
      triggerSummary.addEventListener("click", (e) => requestSummary(movieId, false, e.currentTarget));
    }
    const regenerate = modalContent.querySelector("[data-regenerate]");
    if (regenerate) {
      regenerate.addEventListener("click", (e) => requestSummary(movieId, true, e.currentTarget));
    }

    byId("movie-modal").hidden = false;
    document.body.style.overflow = "hidden";
  }

  function closeModal() {
    byId("movie-modal").hidden = true;
    document.body.style.overflow = "";
    state.activeMovieId = null;
  }

  async function requestSummary(movieId, regenerate, button) {
    if (button) {
      setButtonBusy(button, true, "Generating summary...");
    }
    if (state.activeMovieId !== movieId || byId("movie-modal").hidden) {
      openModal(movieId);
    }

    const summaryCard = byId("modal-content").querySelector(".ai-summary-card");
    if (summaryCard) {
      summaryCard.innerHTML = `
        <div class="ai-summary-header">
          <span class="ai-summary-title">✦ Generating Spoiler-Free Summary...</span>
        </div>
        <p class="ai-summary-text" style="color: var(--accent-gold);">
          Consulting AI provider for spoiler-free synopsis, mood analysis, and audience recommendations...
        </p>
      `;
    }

    try {
      const data = await fetchJson("/api/summary", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ movie_id: movieId, regenerate }),
      });

      const movie = state.movies.get(movieId);
      if (movie) {
        Object.assign(movie, {
          ai_summary: data.result.summary,
          summary_genre: data.result.genre,
          summary_mood: data.result.mood,
          summary_suitable_for: data.result.suitable_for,
          summary_provider: data.provider,
        });
      }

      showToast(`Summary generated for "${data.result.title}"!`, "success");
      if (state.activeMovieId === movieId) {
        openModal(movieId);
      }
    } catch (error) {
      if (state.activeMovieId === movieId) {
        const target = byId("modal-content").querySelector(".ai-summary-card");
        if (target) {
          target.innerHTML = `
            <div class="ai-summary-header">
              <span class="ai-summary-title" style="color: #f87171;">Summary Unavailable</span>
            </div>
            <p class="ai-summary-text" style="color: #f87171;">${escapeHtml(error.message)}</p>
            <button class="btn-regenerate" type="button" data-regenerate="${escapeHtml(movieId)}">
              <span>Try Again</span>
            </button>
          `;
          target.querySelector("[data-regenerate]").addEventListener("click", (e) => {
            requestSummary(movieId, true, e.currentTarget);
          });
        }
      }
      showToast(error.message, "error");
    } finally {
      if (button) setButtonBusy(button, false);
    }
  }

  // Search Form Submit (Wikipedia live scraping + Database caching)
  byId("search-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const input = byId("movie-search");
    const button = byId("search-submit-btn");
    const query = input.value.trim();

    if (!query) {
      return setStatus("search-status", "Please enter a movie title to search.", "error");
    }

    setButtonBusy(button, true, "Searching...");
    setStatus("search-status", `Searching "${query}" in database and Wikipedia...`);

    try {
      const data = await fetchJson("/api/search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query }),
      });

      addMovie(data.movie);
      setStatus(
        "search-status",
        `✓ Found "${data.movie.title}" (${data.movie.year || "Unknown"}) from ${data.source === "scraped" ? "Wikipedia (live scraped & cached)" : "database"}!`,
        "success"
      );
      showToast(`Found "${data.movie.title}"!`, "success");
      input.value = "";
      byId("search-clear-btn").hidden = true;

      byId("library-section").scrollIntoView({ behavior: "smooth" });
      setTimeout(() => openModal(data.movie.id), 600);
    } catch (error) {
      setStatus("search-status", error.message, "error");
      showToast(error.message, "error");
    } finally {
      setButtonBusy(button, false);
    }
  });

  // Search input clear button
  const searchInput = byId("movie-search");
  const searchClearBtn = byId("search-clear-btn");
  searchInput.addEventListener("input", () => {
    searchClearBtn.hidden = !searchInput.value.trim();
  });
  searchClearBtn.addEventListener("click", () => {
    searchInput.value = "";
    searchClearBtn.hidden = true;
    searchInput.focus();
  });

  // Quick Trending Pills
  document.querySelectorAll(".quick-pill").forEach((pill) => {
    pill.addEventListener("click", () => {
      const movieQuery = pill.dataset.search;
      searchInput.value = movieQuery;
      searchClearBtn.hidden = false;
      byId("search-form").dispatchEvent(new Event("submit"));
    });
  });

  // Taste search in movie selector
  const tasteSearch = byId("taste-movie-search");
  if (tasteSearch) {
    tasteSearch.addEventListener("input", () => {
      renderMovieSelectorPills();
    });
  }

  // Clear selected movies button
  const clearSelectedBtn = byId("clear-selected-movies-btn");
  if (clearSelectedBtn) {
    clearSelectedBtn.addEventListener("click", () => {
      state.likedMovies.clear();
      saveLikedMovies(state.likedMovies);
      updateTasteSelectionUI();
      showToast("Cleared selected taste movies.");
    });
  }

  // AI Recommendation Curator Form
  byId("recommend-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const button = byId("recommend-button");
    const moodVal = byId("mood").value;
    const genreVal = byId("preferred-genre").value;
    const langVal = byId("preferred-language").value;
    const reqVal = byId("recommendation-request").value;

    const selectedList = [...state.likedMovies];

    if (!selectedList.length && !moodVal && !genreVal && !langVal && !reqVal) {
      return setStatus(
        "recommend-status",
        "Please select at least one movie you like, choose a mood, or describe what you want.",
        "error"
      );
    }

    setButtonBusy(button, true, "Analyzing taste...");
    setStatus(
      "recommend-status",
      selectedList.length
        ? `Analyzing your love for ${selectedList.slice(0, 3).join(", ")} and curating matches...`
        : "Consulting AI taste curator for tailored movies..."
    );

    const tasteSummaryBox = byId("taste-summary-container");
    if (tasteSummaryBox) {
      tasteSummaryBox.hidden = true;
      tasteSummaryBox.replaceChildren();
    }
    byId("recommendation-results").replaceChildren();

    const payload = {
      selected_movies: selectedList,
      mood: moodVal,
      genre: genreVal,
      language: langVal,
      request: reqVal,
    };

    try {
      const data = await fetchJson("/api/recommend", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      // Display Taste Summary Card if returned
      if (data.taste_summary && tasteSummaryBox) {
        tasteSummaryBox.hidden = false;
        tasteSummaryBox.innerHTML = `
          <div class="taste-profile-card">
            <span class="taste-profile-badge">✦ YOUR CINEMA TASTE PROFILE</span>
            <p class="taste-profile-text">${escapeHtml(data.taste_summary)}</p>
          </div>
        `;
      }

      // Render recommendations
      data.recommendations.forEach((item) => {
        const card = document.createElement("article");
        card.className = "rec-card";
        const trailerUrl = `https://www.youtube.com/results?search_query=${encodeURIComponent(item.title + " " + (item.year || "") + " trailer")}`;

        card.innerHTML = `
          <div class="rec-score-badge">★ ${escapeHtml(item.match_score || "98% Match")}</div>
          <h3 class="rec-title">${escapeHtml(item.title)}</h3>
          <div class="rec-meta">${escapeHtml(item.year)} • ${escapeHtml(item.genre)} • ${escapeHtml(item.language)}</div>
          <p class="rec-reason">${escapeHtml(item.reason)}</p>
          <div class="rec-actions">
            <a href="${escapeHtml(trailerUrl)}" target="_blank" rel="noopener noreferrer" class="btn-trailer" style="padding: 6px 12px; font-size: 0.8rem;">
              <span>Watch Trailer ↗</span>
            </a>
            <button type="button" class="btn-rec-search">Search in Library ↗</button>
          </div>
        `;

        card.querySelector(".btn-rec-search").addEventListener("click", () => {
          searchInput.value = item.title;
          searchClearBtn.hidden = false;
          window.scrollTo({ top: 0, behavior: "smooth" });
          setTimeout(() => {
            byId("search-form").dispatchEvent(new Event("submit"));
          }, 300);
        });

        byId("recommendation-results").append(card);
      });

      setStatus("recommend-status", "✓ AI curated 3 personalized movie recommendations tailored to your taste!", "success");
      showToast("Recommendations ready!", "success");
    } catch (error) {
      setStatus("recommend-status", error.message, "error");
      showToast(error.message, "error");
    } finally {
      setButtonBusy(button, false);
    }
  });

  // Preset chips in AI Curator
  document.querySelectorAll(".preset-chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      byId("mood").value = chip.dataset.mood || "";
      byId("preferred-genre").value = chip.dataset.genre || "";
      byId("preferred-language").value = chip.dataset.lang || "";
      byId("recommendation-request").value = chip.dataset.req || "";
      byId("recommend-form").dispatchEvent(new Event("submit"));
    });
  });

  // Tab switching (All Movies vs Watchlist)
  const tabAll = byId("tab-all");
  const tabWatchlist = byId("tab-watchlist");

  tabAll.addEventListener("click", () => {
    state.activeFilterTab = "all";
    tabAll.classList.add("active");
    tabWatchlist.classList.remove("active");
    renderMovies();
  });

  tabWatchlist.addEventListener("click", () => {
    state.activeFilterTab = "watchlist";
    tabWatchlist.classList.add("active");
    tabAll.classList.remove("active");
    renderMovies();
  });

  byId("nav-watchlist-btn").addEventListener("click", () => {
    tabWatchlist.click();
    byId("library-section").scrollIntoView({ behavior: "smooth" });
  });

  // Filter listeners
  ["genre-filter", "language-filter", "rating-filter", "sort-filter"].forEach((id) => {
    const el = byId(id);
    if (el) el.addEventListener("change", renderMovies);
  });

  const libraryFilterInput = byId("library-filter-input");
  if (libraryFilterInput) {
    libraryFilterInput.addEventListener("input", renderMovies);
  }

  // Reset filters button
  byId("reset-filters-btn").addEventListener("click", () => {
    byId("genre-filter").value = "";
    byId("language-filter").value = "";
    byId("rating-filter").value = "0";
    byId("sort-filter").value = "newest";
    if (libraryFilterInput) libraryFilterInput.value = "";
    renderMovies();
    showToast("Filters reset.");
  });

  // Modal event listeners
  document.querySelectorAll("[data-close-modal]").forEach((btn) => {
    btn.addEventListener("click", closeModal);
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !byId("movie-modal").hidden) {
      closeModal();
    }
  });

  // Initialize
  updateWatchlistBadges();
  loadMovies();
  checkStats();
})();
