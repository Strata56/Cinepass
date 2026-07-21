(() => {
  const placeholder = "/static/images/movie-placeholder.svg";
  const state = { movies: new Map(), activeMovieId: null };
  const byId = (id) => document.getElementById(id);
  const escapeHtml = (value) => String(value ?? "Not available").replace(/[&<>'"]/g, (char) => ({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;","\"":"&quot;"}[char]));
  const text = (value, fallback = "Not available") => String(value ?? "").trim() || fallback;
  const genresFor = (movie) => Array.isArray(movie.genres) && movie.genres.length ? movie.genres : ["Not available"];
  const languagesFor = (movie) => text(movie.language, "").split(/[,;/|]+/).map((value) => value.trim()).filter(Boolean);
  const numericRating = (value) => {
    if (value === null || value === undefined || value === "" || value === "Not available") return null;
    const rating = Number(value);
    return Number.isFinite(rating) && rating > 0 ? rating : null;
  };
  const safeUrl = (value) => /^https?:\/\//i.test(String(value || "")) ? value : "";

  async function fetchJson(url, options = {}) {
    const response = await fetch(url, options);
    const data = await response.json().catch(() => ({}));
    if (!response.ok || !data.success) throw new Error(data.message || "Something went wrong. Please try again.");
    return data;
  }

  function setStatus(id, message = "", isError = false) {
    const target = byId(id);
    target.textContent = message;
    target.classList.toggle("error", isError);
  }

  function setButtonBusy(button, busy, label) {
    button.disabled = busy;
    if (busy && label) button.textContent = label;
    if (!busy && button.dataset.originalLabel) button.textContent = button.dataset.originalLabel;
  }

  function posterImage(url, alt) {
    const image = document.createElement("img");
    image.src = safeUrl(url) || placeholder;
    image.alt = `${alt} poster`;
    image.loading = "lazy";
    image.addEventListener("error", () => { image.src = placeholder; });
    return image;
  }

  function posterArtwork(movie) {
    const remotePoster = safeUrl(movie.poster_url);
    if (remotePoster) return posterImage(remotePoster, text(movie.title));
    const artwork = document.createElement("div");
    const title = text(movie.title);
    const tone = [...title].reduce((total, character) => total + character.charCodeAt(0), 0) % 6;
    artwork.className = `poster-fallback poster-tone-${tone}`;
    artwork.setAttribute("role", "img");
    artwork.setAttribute("aria-label", `${title} poster artwork`);
    artwork.innerHTML = `<span class="poster-brand">CINESUGGEST</span><span class="poster-monogram">${escapeHtml(title.charAt(0))}</span><strong>${escapeHtml(title)}</strong><small>${escapeHtml(genresFor(movie)[0])} • ${escapeHtml(text(movie.year))}</small>`;
    return artwork;
  }

  function movieCard(movie) {
    const card = document.createElement("article");
    card.className = "movie-card";
    card.dataset.id = movie.id;
    card.dataset.genres = genresFor(movie).map((genre) => genre.toLowerCase()).join("|");
    card.dataset.language = text(movie.language, "").toLowerCase();
    card.dataset.rating = numericRating(movie.rating) ?? 0;
    const poster = document.createElement("div");
    poster.className = "poster-wrap";
    poster.append(posterArtwork(movie));
    const body = document.createElement("div");
    body.className = "movie-card-body";
    const rating = numericRating(movie.rating);
    body.innerHTML = `<h3>${escapeHtml(text(movie.title))}</h3><div class="metadata"><span>${escapeHtml(text(movie.year))}</span><span>${escapeHtml(genresFor(movie)[0])}</span></div><div class="metadata">${escapeHtml(text(movie.language))}</div><p class="movie-rating">★ ${Number.isFinite(rating) ? rating.toFixed(1) : "Not available"}</p>`;
    const actions = document.createElement("div");
    actions.className = "card-actions";
    const details = document.createElement("button");
    details.type = "button";
    details.textContent = "View details";
    details.addEventListener("click", () => openModal(movie.id));
    const summary = document.createElement("button");
    summary.type = "button";
    summary.textContent = "AI summary";
    summary.addEventListener("click", () => requestSummary(movie.id, false, summary));
    actions.append(details, summary);
    body.append(actions);
    card.append(poster, body);
    return card;
  }

  function populateFilters() {
    const movies = [...state.movies.values()];
    const setOptions = (select, values, label) => {
      const selected = select.value;
      select.innerHTML = `<option value="">All ${label}</option>`;
      [...values].sort().forEach((value) => { const option = document.createElement("option"); option.value = value; option.textContent = value; select.append(option); });
      if ([...select.options].some((option) => option.value === selected)) select.value = selected;
    };
    setOptions(byId("genre-filter"), new Set(movies.flatMap(genresFor).filter((value) => value !== "Not available")), "genres");
    setOptions(byId("language-filter"), new Set(movies.flatMap(languagesFor)), "languages");
  }

  function renderMovies() {
    const grid = byId("movie-grid");
    const genre = byId("genre-filter").value.toLowerCase();
    const language = byId("language-filter").value.toLowerCase();
    const minimumRating = Number(byId("rating-filter").value);
    const movies = [...state.movies.values()].filter((movie) => {
      const hasGenre = !genre || genresFor(movie).some((item) => item.toLowerCase() === genre);
      const hasLanguage = !language || languagesFor(movie).some((item) => item.toLowerCase() === language);
      return hasGenre && hasLanguage && (numericRating(movie.rating) ?? 0) >= minimumRating;
    });
    grid.replaceChildren();
    if (!movies.length) {
      grid.innerHTML = '<p class="empty-state">No movies match these filters.</p>';
    } else {
      movies.forEach((movie) => grid.append(movieCard(movie)));
    }
    byId("movie-count").textContent = `${movies.length} of ${state.movies.size} movies`;
  }

  function addMovie(movie) {
    if (!movie || !movie.id) return;
    state.movies.set(movie.id, movie);
    populateFilters();
    renderMovies();
  }

  async function loadMovies() {
    try {
      const data = await fetchJson("/api/movies");
      data.movies.forEach((movie) => state.movies.set(movie.id, movie));
      populateFilters();
      renderMovies();
      setStatus("movies-status");
    } catch (error) {
      setStatus("movies-status", error.message, true);
    }
  }

  function summaryMarkup(movie) {
    if (!movie.ai_summary) return '<div class="summary-box"><h3>AI spoiler-free summary</h3><p>Generate a short, spoiler-free overview from the movie details.</p></div>';
    return `<div class="summary-box"><h3>AI spoiler-free summary</h3><p>${escapeHtml(movie.ai_summary)}</p><p><b>Genre:</b> ${escapeHtml(text(movie.summary_genre))} &nbsp; <b>Mood:</b> ${escapeHtml(text(movie.summary_mood))}</p><p><b>Suitable for:</b> ${escapeHtml(text(movie.summary_suitable_for))}</p><button class="regenerate" type="button" data-regenerate="${escapeHtml(movie.id)}">Regenerate summary</button></div>`;
  }

  function openModal(movieId) {
    const movie = state.movies.get(movieId);
    if (!movie) return;
    state.activeMovieId = movieId;
    const rating = numericRating(movie.rating);
    const source = safeUrl(movie.source_url);
    byId("modal-content").innerHTML = `<div class="modal-details"><div></div><div><p class="eyebrow">${escapeHtml(text(movie.data_source, "movie"))} MOVIE</p><h2 id="modal-title">${escapeHtml(text(movie.title))}</h2><p class="detail-tags">${escapeHtml(genresFor(movie).join(" • "))}</p><div class="detail-list"><div><b>Released:</b> ${escapeHtml(text(movie.year))}</div><div><b>Language:</b> ${escapeHtml(text(movie.language))}</div><div><b>Duration:</b> ${escapeHtml(text(movie.duration))}</div><div><b>Director:</b> ${escapeHtml(text(movie.director))}</div><div><b>Cast:</b> ${escapeHtml((Array.isArray(movie.cast) ? movie.cast : ["Not available"]).join(", "))}</div><div><b>Rating:</b> ${Number.isFinite(rating) ? rating.toFixed(1) : "Not available"}</div></div><p>${escapeHtml(text(movie.description))}</p>${source ? `<a class="source-link" href="${escapeHtml(source)}" target="_blank" rel="noopener noreferrer">View Wikipedia source ↗</a>` : ""}${summaryMarkup(movie)}</div></div>`;
    byId("modal-content").querySelector(".modal-details > div").append(posterArtwork(movie));
    const regenerate = byId("modal-content").querySelector("[data-regenerate]");
    if (regenerate) regenerate.addEventListener("click", () => requestSummary(movieId, true, regenerate));
    byId("movie-modal").hidden = false;
    document.body.style.overflow = "hidden";
  }

  function closeModal() { byId("movie-modal").hidden = true; document.body.style.overflow = ""; }

  async function requestSummary(movieId, regenerate, button) {
    if (button) { button.dataset.originalLabel = button.textContent; setButtonBusy(button, true, "Generating..."); }
    if (state.activeMovieId !== movieId || byId("movie-modal").hidden) openModal(movieId);
    const summaryBox = byId("modal-content").querySelector(".summary-box");
    if (summaryBox) summaryBox.innerHTML = "<h3>AI spoiler-free summary</h3><p>Generating spoiler-free summary...</p>";
    try {
      const data = await fetchJson("/api/summary", { method: "POST", headers: {"Content-Type":"application/json"}, body: JSON.stringify({movie_id: movieId, regenerate}) });
      const movie = state.movies.get(movieId);
      Object.assign(movie, { ai_summary: data.result.summary, summary_genre: data.result.genre, summary_mood: data.result.mood, summary_suitable_for: data.result.suitable_for, summary_provider: data.provider });
      if (state.activeMovieId === movieId) openModal(movieId);
    } catch (error) {
      if (state.activeMovieId === movieId) byId("modal-content").querySelector(".summary-box").innerHTML = `<h3>AI spoiler-free summary</h3><p>${escapeHtml(error.message)}</p>`;
    } finally { if (button) setButtonBusy(button, false); }
  }

  byId("search-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const input = byId("movie-search"), button = event.currentTarget.querySelector("button"), query = input.value.trim();
    if (!query) return setStatus("search-status", "Enter a movie name to search.", true);
    button.dataset.originalLabel = button.textContent; setButtonBusy(button, true, "Searching..."); setStatus("search-status", "Searching for movie information...");
    try { const data = await fetchJson("/api/search", {method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({query})}); addMovie(data.movie); setStatus("search-status", `Found ${data.movie.title} from ${data.source}.`); input.value = ""; }
    catch (error) { setStatus("search-status", error.message, true); }
    finally { setButtonBusy(button, false); }
  });

  byId("recommend-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const button = byId("recommend-button"); button.dataset.originalLabel = button.textContent; setButtonBusy(button, true, "Finding movies..."); setStatus("recommend-status", "Finding movie recommendations..."); byId("recommendation-results").replaceChildren();
    const payload = {mood:byId("mood").value,genre:byId("preferred-genre").value,language:byId("preferred-language").value,request:byId("recommendation-request").value};
    try { const data = await fetchJson("/api/recommend", {method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(payload)}); data.recommendations.forEach((movie) => { const card = document.createElement("article"); card.className = "recommendation-card"; card.innerHTML = `<h3>${escapeHtml(movie.title)}</h3><div class="metadata">${escapeHtml(movie.year)} • ${escapeHtml(movie.genre)} • ${escapeHtml(movie.language)}</div><p>${escapeHtml(movie.reason)}</p>`; byId("recommendation-results").append(card); }); setStatus("recommend-status", ""); }
    catch (error) { setStatus("recommend-status", error.message, true); }
    finally { setButtonBusy(button, false); }
  });

  ["genre-filter", "language-filter", "rating-filter"].forEach((id) => byId(id).addEventListener("change", renderMovies));
  document.querySelectorAll("[data-close-modal]").forEach((button) => button.addEventListener("click", closeModal));
  document.addEventListener("keydown", (event) => { if (event.key === "Escape") closeModal(); });
  loadMovies();
})();
