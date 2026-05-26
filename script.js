const spainBounds = [[35.9, -10.7], [44.6, 4.7]];
const map = L.map('map', {
  maxBounds: spainBounds,
  maxBoundsViscosity: 0.9,
  minZoom: 5,
  maxZoom: 13,
  zoomControl: true
}).setView([40.4168, -3.7038], 6);

const jobsUrl = window.JOBS_JSON_URL || 'jobs.json';

L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  attribution: '&copy; OpenStreetMap contributors'
}).addTo(map);

const markerLayer = L.layerGroup().addTo(map);

const jobsBaseUrl = getBaseUrl(jobsUrl);

function resolveUrl(path) {
  if (!path) return path;
  if (/^(?:https?:)?\/\//.test(path)) return path;
  if (path.startsWith('/')) return path;
  return jobsBaseUrl + path;
}

const jobMarkerIcon = L.divIcon({
  className: 'job-marker',
  iconSize: [14, 14],
  popupAnchor: [0, -8]
});

const COMMUNITY_ALIAS = {
  'Comunidad Valenciana': 'C. Valenciana'
};

let jobs = [];
let communities = [];
let selectedCommunitySlug = 'all';
let selectedCommunityName = 'Todas';
let selectedType = 'all';
let selectedCategory = 'all';
let selectedSearch = '';
let liveSearchMatches = [];

const summary = document.getElementById('summary');
const openFiltersButton = document.getElementById('open-filters');
const closeFiltersButton = document.getElementById('close-filters');
const filterModal = document.getElementById('filter-modal');
const modalCommunity = document.getElementById('modal-community');
const modalType = document.getElementById('modal-type');
const modalCategory = document.getElementById('modal-category');
const modalSearch = document.getElementById('modal-search');
const searchResults = document.getElementById('search-results');
const applyFiltersButton = document.getElementById('apply-filters');
const resetFiltersButton = document.getElementById('reset-filters');

const communitiesUrl = getBaseUrl(jobsUrl) + 'communities.json';

fetch(communitiesUrl)
  .then(res => res.json())
  .then(data => {
    communities = Array.isArray(data) ? data : [];
    if (!communities.length) throw new Error('Communities list vacía');
    populateModalCommunity();
    populateModalType();
    openModal();
  })
  .catch(() => {
    console.error('No se pudo cargar communities.json, cargando jobs.json como fallback.');
    fetch(jobsUrl)
      .then(res => res.json())
      .then(data => {
        jobs = data;
        communities = createCommunityListFromJobs(data);
        selectedCommunitySlug = communities.length ? communities[0].slug : 'all';
        selectedCommunityName = communities.length ? communities[0].name : 'Todas';
        populateModalCommunity();
        populateModalType();
        openModal();
      });
  });

openFiltersButton.addEventListener('click', openModal);
closeFiltersButton.addEventListener('click', closeModal);
modalSearch.addEventListener('input', () => {
  selectedSearch = modalSearch.value.trim().toLowerCase();
  updateSearchResults();
});
applyFiltersButton.addEventListener('click', () => {
  if (!selectedCommunitySlug && communities.length > 0) {
    selectedCommunitySlug = communities[0].slug;
    selectedCommunityName = communities[0].name;
  }
  selectedSearch = modalSearch.value.trim().toLowerCase();
  const communityEntry = communities.find(item => item.slug === selectedCommunitySlug);
  const path = communityEntry ? communityEntry.path : jobsUrl;
  loadJobsForCommunity(path).then(() => {
    closeModal();
    updateSearchResults();
    renderJobs();
  });
});
resetFiltersButton.addEventListener('click', () => {
  selectedCommunitySlug = 'all';
  selectedCommunityName = 'Todas';
  selectedType = 'all';
  selectedCategory = 'all';
  selectedSearch = '';
  modalSearch.value = '';
  populateModalCommunity();
  populateModalType();
  populateModalCategory([]);
  loadJobsForCommunity(jobsUrl).then(() => {
    updateSearchResults();
    renderJobs();
  });
});

filterModal.addEventListener('click', event => {
  if (event.target.dataset.close === 'true') {
    closeModal();
  }
});

function getBaseUrl(url) {
  return url.includes('/') ? url.replace(/\/[^\/]*$/, '/') : '';
}

function openModal() {
  updateSearchResults();
  filterModal.setAttribute('aria-hidden', 'false');
  filterModal.classList.add('visible');
}

function closeModal() {
  filterModal.setAttribute('aria-hidden', 'true');
  filterModal.classList.remove('visible');
}

function populateModalCommunity() {
  modalCommunity.innerHTML = '';
  if (communities.length && selectedCommunitySlug === null) {
    selectedCommunitySlug = 'all';
  }

  const communityOptions = [{ name: 'Todas', slug: 'all', path: jobsUrl }, ...communities];

  communityOptions.forEach(item => {
    const button = document.createElement('button');
    button.type = 'button';
    button.textContent = item.name;
    button.className = item.slug === selectedCommunitySlug ? 'active' : '';
    button.addEventListener('click', () => {
      selectedCommunitySlug = item.slug;
      selectedCommunityName = item.name;
      selectedCategory = 'all';
      selectedSearch = '';
      modalSearch.value = '';
      updateActiveButtons(modalCommunity, button);
      loadJobsForCommunity(item.path).then(() => {
        loadCommunityCategories(item.path);
        updateSearchResults();
      });
    });
    modalCommunity.appendChild(button);
  });

  const current = communityOptions.find(item => item.slug === selectedCommunitySlug);
  if (current) {
    loadCommunityCategories(current.path);
  }
}

function populateModalType() {
  buildFilterButtons(modalType, ['all', 'onsite', 'remote', 'hybrid'], labelForType, value => {
    selectedType = value;
  }, selectedType);
}

function populateModalCategory(categories = []) {
  modalCategory.innerHTML = '';
  const categoryValues = ['all', ...categories.sort()];
  buildFilterButtons(modalCategory, categoryValues, value => value === 'all' ? 'Todas' : value, value => {
    selectedCategory = value;
  }, selectedCategory);
  updateCategoryState();
}

function buildFilterButtons(container, values, labelFn, onSelect, selectedValue = 'all') {
  container.innerHTML = '';
  values.forEach(value => {
    const button = document.createElement('button');
    button.type = 'button';
    button.textContent = labelFn(value);
    button.className = value === selectedValue ? 'active' : '';
    button.addEventListener('click', () => {
      onSelect(value);
      updateActiveButtons(container, button);
    });
    container.appendChild(button);
  });
}

function updateActiveButtons(container, activeButton) {
  Array.from(container.children).forEach(btn => btn.classList.toggle('active', btn === activeButton));
}

function updateCategoryState() {
  const disabled = Boolean(selectedSearch);
  Array.from(modalCategory.querySelectorAll('button')).forEach(button => {
    button.disabled = disabled;
    button.classList.toggle('disabled', disabled);
  });
}

function loadCommunityCategories(path) {
  fetch(resolveUrl(path))
    .then(res => res.json())
    .then(data => {
      const categories = new Set(data.map(job => job.category).filter(Boolean));
      populateModalCategory(Array.from(categories));
    });
}

function loadJobsForCommunity(path) {
  return fetch(resolveUrl(path))
    .then(res => res.json())
    .then(data => {
      jobs = data;
      if (!communities.length || communities.every(item => item.path !== path)) {
        communities = createCommunityListFromJobs(data);
      }
      return jobs;
    });
}

function createCommunityListFromJobs(jobList) {
  const map = new Map();
  jobList.forEach(job => {
    const community = job.community || job.province || 'Sin región';
    const slug = slugify(community);
    if (!map.has(slug)) {
      map.set(slug, {
        name: COMMUNITY_ALIAS[community] || community,
        slug,
        path: jobsUrl
      });
    }
  });
  return Array.from(map.values()).sort((a, b) => a.name.localeCompare(b.name, 'es'));
}

function slugify(value) {
  return value.toString().normalize('NFKD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/(^-|-$)/g, '');
}

function labelForType(value) {
  return value === 'all' ? 'Todas' : value === 'onsite' ? 'Presencial' : value === 'remote' ? 'Remoto' : 'Híbrido';
}

function renderJobs() {
  const filtered = jobs.filter(job => {
    const matchType = selectedType === 'all' || job.type === selectedType;
    const matchCategory = selectedCategory === 'all' || job.category === selectedCategory;
    const matchCommunity = selectedCommunitySlug === 'all' || !selectedCommunitySlug || isCommunityMatch(job, selectedCommunitySlug);
    return matchType && matchCategory && matchCommunity;
  });

  const total = filtered.length;
  let counts = {};
  const hasCoords = filtered.some(job => Number.isFinite(parseFloat(job.lat)) && Number.isFinite(parseFloat(job.lng)));
  if (hasCoords) {
    filtered.forEach(job => {
      const community = job.community || job.province || 'Sin región';
      counts[community] = (counts[community] || 0) + 1;
    });
  } else {
    // Fallback: group by city/location when no coordinates are available
    filtered.forEach(job => {
      const city = job.city || job.location || 'Sin localidad';
      counts[city] = (counts[city] || 0) + 1;
    });
  }

  summary.innerHTML = total === 0
    ? '<div class="mini-summary__total">0 ofertas totales</div><div class="mini-summary__list"><div class="mini-summary__item"><span>No hay resultados</span></div></div>'
    : buildSummaryHtml(total, counts);

  markerLayer.clearLayers();

  if (filtered.length && hasCoords) {
    const bounds = [];
    filtered.forEach(job => {
      const lat = parseFloat(job.lat);
      const lng = parseFloat(job.lng);
      if (!Number.isFinite(lat) || !Number.isFinite(lng)) return;
      const marker = L.marker([lat, lng], { icon: jobMarkerIcon });
      const linkHtml = job.url
        ? `<br><a href="${job.url}" target="_blank" rel="noopener" style="color:#60a5fa; text-decoration:none; font-weight:700;">Ver oferta</a>`
        : '';
      marker.bindPopup(`
        <strong>${job.title}</strong><br>
        ${job.company}<br>
        ${job.location}<br>
        ${job.category} · ${capitalize(job.type)}${linkHtml}
      `);
      marker.on('click', () => {
        map.flyTo([lat, lng], 11, { animate: true });
        marker.openPopup();
      });
      markerLayer.addLayer(marker);
      bounds.push([lat, lng]);
    });

    if (bounds.length) {
      map.fitBounds(bounds, { padding: [40, 40], maxZoom: 11 });
    }
  }
}


function updateSearchResults() {
  const query = modalSearch.value.trim().toLowerCase();
  const currentCommunity = selectedCommunitySlug === 'all' ? null : selectedCommunitySlug;
  updateCategoryState();
  const matches = query ? jobs.filter(job => {
    const matchType = selectedType === 'all' || job.type === selectedType;
    const matchCommunity = currentCommunity ? isCommunityMatch(job, currentCommunity) : true;
    const terms = `${job.title} ${job.company} ${job.location} ${job.category} ${job.province} ${job.community}`.toLowerCase();
    return matchType && matchCommunity && terms.includes(query);
  }).slice(0, 10) : [];

  liveSearchMatches = matches;

  if (!query) {
    searchResults.innerHTML = '<div class="search-results__header">Empieza a escribir para ver coincidencias de puesto</div>';
    return;
  }

  searchResults.innerHTML = `
    <div class="search-results__header">Coincidencias de "${modalSearch.value.trim()}" (${matches.length})</div>
    ${matches.length ? matches.map((job, index) => {
      const community = job.community || job.province || 'Sin región';
      const label = currentCommunity ? job.title : `${job.title} · ${community}`;
      return `<button type="button" class="search-result" data-result-index="${index}">${label}</button>`;
    }).join('') : '<div class="search-result search-result--empty">No hay coincidencias</div>'}
  `;

  Array.from(searchResults.querySelectorAll('[data-result-index]')).forEach(button => {
    button.addEventListener('click', () => {
      const index = Number(button.dataset.resultIndex);
      const job = liveSearchMatches[index];
      if (job) {
        focusJobOnMap(job);
      }
    });
  });
}

function focusJobOnMap(job) {
  const lat = parseFloat(job.lat);
  const lng = parseFloat(job.lng);
  closeModal();
  if (!Number.isFinite(lat) || !Number.isFinite(lng)) {
    // No coordinates: show info at current map center
    const center = map.getCenter();
    L.popup({ autoClose: false, closeOnClick: false })
      .setLatLng(center)
      .setContent(`
        <strong>${job.title}</strong><br>
        ${job.company}<br>
        ${job.location || job.city || 'Sin localidad'}<br>
        ${job.category} · ${capitalize(job.type)}
      `)
      .openOn(map);
    return;
  }
  map.flyTo([lat, lng], 11, { animate: true });
  L.popup({ autoClose: false, closeOnClick: false })
    .setLatLng([lat, lng])
    .setContent(`
      <strong>${job.title}</strong><br>
      ${job.company}<br>
      ${job.location}<br>
      ${job.category} · ${capitalize(job.type)}
    `)
    .openOn(map);
}

function isCommunityMatch(job, slug) {
  if (slug === 'all') return true;
  const community = job.community || job.province || 'Sin región';
  return slugify(community) === slug;
}

function buildSummaryHtml(total, counts) {
  const filtered = Object.entries(counts)
    .sort((a, b) => b[1] - a[1]);
  const listItems = filtered.map(([community, count]) => {
    const displayName = COMMUNITY_ALIAS[community] || community;
    return `
      <div class="mini-summary__item"><span>${count} ofertas en ${displayName}</span></div>
    `;
  }).join('');

  return `
    <div class="mini-summary__total">${total} ofertas totales</div>
    <div class="mini-summary__list">${listItems}</div>
  `;
}

function capitalize(value) {
  return value.charAt(0).toUpperCase() + value.slice(1);
}

