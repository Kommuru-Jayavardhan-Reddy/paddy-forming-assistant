// ============================================================================
// STEP 4: MY FIELD SCREEN
// Handles rendering the Field Selector on the Home Page and the logic for
// Add/Edit Field form.
// ============================================================================

document.addEventListener('DOMContentLoaded', async () => {
  // Elements - Home Page
  const fieldListContainer = document.getElementById('field-selector-list');
  const fieldLoading = document.getElementById('field-selector-loading');
  const fieldEmpty = document.getElementById('field-selector-empty');
  const btnAddNewField = document.getElementById('btn-add-new-field');

  // Elements - Form Page
  const formTitle = document.getElementById('field-form-title');
  const formContainer = document.getElementById('field-form-container');
  const formLoading = document.getElementById('field-form-loading');
  const successState = document.getElementById('field-success-state');
  
  const inputName = document.getElementById('field-name');
  const inputVariety = document.getElementById('field-variety');
  const inputDate = document.getElementById('field-date');
  const inputSize = document.getElementById('field-size');
  const errorName = document.getElementById('field-name-error');
  
  const mapContainer = document.getElementById('field-map');
  const btnUseLocation = document.getElementById('btn-use-location');
  const locationStatus = document.getElementById('location-status');
  const errorLocation = document.getElementById('field-location-error');
  
  const btnSaveField = document.getElementById('btn-save-field');
  const btnCancelField = document.getElementById('btn-cancel-field');
  
  const deleteContainer = document.getElementById('delete-field-container');
  const btnDeleteField = document.getElementById('btn-delete-field');
  const deleteOverlay = document.getElementById('delete-confirm-overlay');
  const btnConfirmDelete = document.getElementById('btn-confirm-delete');
  const btnCancelDelete = document.getElementById('btn-cancel-delete');
  
  // State
  let currentEditingFieldId = null;
  let leafletMap = null;
  let locationMarker = null;
  let selectedLatLng = null;

  // Render Field List
  const renderFieldList = async () => {
    fieldListContainer.classList.add('hidden');
    fieldEmpty.classList.add('hidden');
    fieldLoading.classList.remove('hidden');

    const fields = await window.DataAccess.getFields();

    fieldLoading.classList.add('hidden');

    if (fields.length === 0) {
      fieldEmpty.classList.remove('hidden');
      return;
    }

    fieldListContainer.innerHTML = '';
    
    fields.forEach(field => {
      const card = document.createElement('div');
      card.className = 'info-card flex items-center justify-between cursor-pointer hover:bg-white/90 transition-colors border-l-4 ' + getStatusBorderClass(field.status);
      card.innerHTML = `
        <div>
          <h4 class="font-bold text-lg text-[#0d5c38]">${field.name}</h4>
          <p class="text-sm text-gray-600">${field.crop} • ${field.location || 'No location set'}</p>
        </div>
        <div class="flex items-center space-x-3">
          ${getStatusBadge(field.status)}
          <button class="text-[#0d5c38]/50 hover:text-[#0d5c38] p-2 edit-field-btn" data-id="${field.id}">
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z"></path></svg>
          </button>
        </div>
      `;
      fieldListContainer.appendChild(card);
    });

    fieldListContainer.classList.remove('hidden');
    
    // Bind Edit buttons
    document.querySelectorAll('.edit-field-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation(); // Prevent card click
        openEditForm(btn.dataset.id);
      });
    });
  };

  // Helper for Status UI
  const getStatusBorderClass = (status) => {
    if (status === 'Healthy') return 'border-[var(--status-green)]';
    if (status === 'Needs Attention') return 'border-[var(--status-amber)]';
    if (status === 'High Risk') return 'border-[var(--status-red)]';
    return 'border-gray-400';
  };
  
  const getStatusBadge = (status) => {
    if (status === 'Healthy') return `<span class="status-badge status-healthy py-1 px-2 text-xs">Healthy</span>`;
    if (status === 'Needs Attention') return `<span class="status-badge status-attention py-1 px-2 text-xs">Needs Attention</span>`;
    if (status === 'High Risk') return `<span class="status-badge status-risk py-1 px-2 text-xs">High Risk</span>`;
    return `<span class="status-badge py-1 px-2 text-xs text-gray-600 bg-gray-100">Unknown</span>`;
  };

  // Open Form (Add new)
  const openAddForm = () => {
    currentEditingFieldId = null;
    formTitle.textContent = "Add My Field";
    btnSaveField.textContent = "Save Field";
    deleteContainer.classList.add('hidden');
    
    // Reset Form
    inputName.value = '';
    inputVariety.value = 'BPT 5204 – Sona Masuri';
    inputDate.value = '';
    inputSize.value = '';
    selectedLatLng = null;
    
    clearErrors();
    showForm();
    initMap();
    if(locationMarker) leafletMap.removeLayer(locationMarker);
    locationStatus.textContent = '';
    
    if (window.goToPage) window.goToPage('page-field-form', true);
  };

  // Open Form (Edit)
  const openEditForm = async (id) => {
    currentEditingFieldId = id;
    formTitle.textContent = "Edit Field";
    btnSaveField.textContent = "Save Changes";
    deleteContainer.classList.remove('hidden');
    
    clearErrors();
    showForm();
    
    if (window.goToPage) window.goToPage('page-field-form', true);
    
    // Load Data
    formLoading.classList.remove('hidden');
    formLoading.style.display = 'flex';
    const field = await window.DataAccess.getField(id);
    formLoading.classList.add('hidden');
    formLoading.style.display = 'none';
    
    if (field) {
      inputName.value = field.name || '';
      inputVariety.value = field.crop || 'BPT 5204 – Sona Masuri';
      inputDate.value = field.sowingDate || '';
      inputSize.value = field.size || '';
      
      initMap();
      if (field.lat && field.lng) {
        setMapLocation(field.lat, field.lng, true);
      } else {
        if(locationMarker) leafletMap.removeLayer(locationMarker);
        selectedLatLng = null;
      }
    }
  };

  // Leaflet Map Initialization
  const initMap = () => {
    if (leafletMap) {
      leafletMap.remove();
      leafletMap = null;
    }

    // Default to center of India broadly
    leafletMap = L.map(mapContainer).setView([20.5937, 78.9629], 5);
    const satelliteMap = L.tileLayer('https://{s}.google.com/vt/lyrs=s&x={x}&y={y}&z={z}', {
      maxZoom: 20,
      subdomains:['mt0','mt1','mt2','mt3'],
      attribution: '&copy; Google Maps'
    });

    const normalMap = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '© OpenStreetMap'
    });

    satelliteMap.addTo(leafletMap);

    const baseMaps = {
      "Satellite Map": satelliteMap,
      "Normal Map": normalMap
    };

    L.control.layers(baseMaps).addTo(leafletMap);
    
    leafletMap.on('click', (e) => {
      setMapLocation(e.latlng.lat, e.latlng.lng, false);
    });
    setTimeout(() => leafletMap.invalidateSize(), 300);
  };

  const setMapLocation = (lat, lng, zoomIn) => {
    selectedLatLng = { lat, lng };
    if (!locationMarker) {
      locationMarker = L.marker([lat, lng]).addTo(leafletMap);
    } else {
      locationMarker.setLatLng([lat, lng]);
    }
    if (zoomIn) {
      leafletMap.setView([lat, lng], 13);
    }
    locationStatus.textContent = "Location selected.";
    locationStatus.classList.remove('text-red-500');
    locationStatus.classList.add('text-green-600');
    errorLocation.classList.add('hidden');
  };

  // Geolocation
  btnUseLocation.addEventListener('click', () => {
    locationStatus.textContent = "Getting location...";
    locationStatus.classList.remove('text-red-500', 'text-green-600');
    
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          setMapLocation(position.coords.latitude, position.coords.longitude, true);
        },
        (_error) => {
          locationStatus.textContent = "Location access is unavailable. You can select your field location directly on the map.";
          locationStatus.classList.add('text-red-500');
          // Fallback to manual tap
        }
      );
    } else {
      locationStatus.textContent = "Geolocation is not supported. Please tap on the map.";
      locationStatus.classList.add('text-red-500');
    }
  });

  // Save/Validation
  const clearErrors = () => {
    errorName.classList.add('hidden');
    inputName.classList.remove('border-red-500');
    errorLocation.classList.add('hidden');
    mapContainer.classList.remove('border-red-500');
  };

  btnSaveField.addEventListener('click', async () => {
    clearErrors();
    let isValid = true;
    
    if (!inputName.value.trim()) {
      errorName.classList.remove('hidden');
      inputName.classList.add('border-red-500');
      isValid = false;
    }
    
    if (!selectedLatLng) {
      errorLocation.classList.remove('hidden');
      mapContainer.classList.add('border-red-500');
      isValid = false;
    }
    
    if (!isValid) return;
    
    formLoading.classList.remove('hidden');
    formLoading.style.display = 'flex';
    
    const fieldData = {
      name: inputName.value.trim(),
      crop: inputVariety.value,
      sowingDate: inputDate.value,
      size: inputSize.value.trim(),
      location: "Map Location", 
      lat: selectedLatLng.lat,
      lng: selectedLatLng.lng
    };
    
    if (currentEditingFieldId) {
      await window.DataAccess.updateField(currentEditingFieldId, fieldData);
      document.getElementById('field-success-title').textContent = "Your field details have been updated successfully.";
    } else {
      await window.DataAccess.saveField(fieldData);
      document.getElementById('field-success-title').textContent = "Your field has been added successfully!";
    }
    
    formLoading.classList.add('hidden');
    formLoading.style.display = 'none';
    
    formContainer.classList.add('hidden');
    successState.classList.remove('hidden');
    
    // Refresh list in background
    renderFieldList();
  });

  // Cancel form
  btnCancelField.addEventListener('click', () => {
    if (window.goToPage) window.goToPage('page-home', true);
  });

  // Delete flow
  btnDeleteField.addEventListener('click', () => {
    deleteOverlay.classList.remove('hidden');
    deleteOverlay.style.display = 'flex';
  });
  
  btnCancelDelete.addEventListener('click', () => {
    deleteOverlay.classList.add('hidden');
    deleteOverlay.style.display = 'none';
  });
  
  btnConfirmDelete.addEventListener('click', async () => {
    if (!currentEditingFieldId) return;
    
    deleteOverlay.classList.add('hidden');
    deleteOverlay.style.display = 'none';
    
    formLoading.classList.remove('hidden');
    formLoading.style.display = 'flex';
    
    await window.DataAccess.deleteField(currentEditingFieldId);
    
    formLoading.classList.add('hidden');
    formLoading.style.display = 'none';
    
    await renderFieldList();
    if (window.goToPage) window.goToPage('page-home', true);
  });

  // State mgmt helpers
  const showForm = () => {
    formContainer.classList.remove('hidden');
    successState.classList.add('hidden');
    deleteOverlay.classList.add('hidden');
    deleteOverlay.style.display = 'none';
  };

  // Setup Triggers
  btnAddNewField.addEventListener('click', openAddForm);
  
  // Re-bind global nav links for success state buttons since they might be missed by original script
  document.querySelectorAll('#field-success-state .nav-link').forEach(link => {
    link.addEventListener('click', (e) => {
      e.preventDefault();
      if (window.goToPage) window.goToPage(link.dataset.target, true);
    });
  });

  // Check if we start on Home
  renderFieldList();
});
